"""
Agent implementation for AgentFlow using Amazon Strands SDK
"""

import uuid
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.patterns.reasoning import ReasoningPattern
from agentflow.utils.logging import setup_logger
from agentflow.utils.exceptions import AgentExecutionError

logger = setup_logger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    description: str = ""
    model_type: ModelType = ModelType.SONNET_4_5
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    reasoning_pattern: Optional[ReasoningPattern] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    retry_delay: float = 1.0


class StrandsAgent(ABC):
    """
    Base agent class for AgentFlow using Strands SDK patterns
    
    Integrates with Amazon Strands SDK for agent orchestration while
    maintaining compatibility with Bedrock models.
    """
    
    def __init__(self, config: AgentConfig, bedrock_client: BedrockClient):
        self.config = config
        self.bedrock_client = bedrock_client
        self.agent_id = str(uuid.uuid4())
        self.logger = logger.bind(
            agent_id=self.agent_id,
            agent_name=config.name,
            agent_type=self.__class__.__name__
        )
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        
        # CloudWatch logging
        self.logger.info(
            "Agent initialized",
            model_type=config.model_type.value,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, "WARNING"),
        after=after_log(logger, "INFO"),
        reraise=True
    )
    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """
        Execute the agent with given inputs
        
        Implements Strands SDK execution pattern with:
        - Automatic retry with exponential backoff
        - CloudWatch logging
        - Fault tolerance
        - Execution tracking
        """
        self.execution_count += 1
        execution_id = str(uuid.uuid4())
        
        # CloudWatch structured logging
        self.logger.info(
            "Agent execution started",
            execution_id=execution_id,
            execution_count=self.execution_count,
            inputs_keys=list(inputs.keys())
        )
        
        try:
            # Validate inputs
            self._validate_inputs(inputs)
            
            # Prepare the prompt
            prompt = self._prepare_prompt(inputs)
            
            # Apply reasoning pattern if configured
            if self.config.reasoning_pattern:
                self.logger.debug(
                    "Applying reasoning pattern",
                    pattern=self.config.reasoning_pattern.__class__.__name__
                )
                prompt = self.config.reasoning_pattern.apply(prompt, inputs)
            
            # Execute with Bedrock (with built-in retry)
            self.logger.debug(
                "Invoking Bedrock model",
                model=self.config.model_type.value,
                prompt_length=len(prompt)
            )
            
            response = await self.bedrock_client.invoke(
                model_type=self.config.model_type,
                prompt=prompt,
                system_prompt=self.config.system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=self.config.tools if self.config.tools else None
            )
            
            # Process the response
            result = self._process_response(response, inputs)
            
            # Track success
            self.success_count += 1
            
            # CloudWatch logging
            self.logger.info(
                "Agent execution completed successfully",
                execution_id=execution_id,
                model=self.config.model_type.value,
                success_count=self.success_count,
                input_tokens=response.get("usage", {}).get("input_tokens", 0),
                output_tokens=response.get("usage", {}).get("output_tokens", 0)
            )
            
            return result
            
        except Exception as e:
            # Track failure
            self.failure_count += 1
            
            # CloudWatch error logging
            self.logger.error(
                "Agent execution failed",
                execution_id=execution_id,
                error=str(e),
                error_type=type(e).__name__,
                failure_count=self.failure_count,
                exc_info=True
            )
            
            raise AgentExecutionError(
                f"Agent {self.config.name} execution failed: {str(e)}"
            ) from e
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate input data"""
        if not isinstance(inputs, dict):
            raise ValueError("Inputs must be a dictionary")
        
        # Log validation
        self.logger.debug(
            "Input validation passed",
            input_count=len(inputs)
        )
    
    @abstractmethod
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare the prompt for the model"""
        pass
    
    @abstractmethod
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process the model response"""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent execution metrics"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.config.name,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / self.execution_count if self.execution_count > 0 else 0
        }


# Maintain backward compatibility
Agent = StrandsAgent


class SimpleAgent(StrandsAgent):
    """
    Simple agent for straightforward tasks
    
    Uses a template-based approach for prompt generation.
    Integrates with Strands SDK patterns.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        prompt_template: str
    ):
        super().__init__(config, bedrock_client)
        self.prompt_template = prompt_template
        
        self.logger.debug(
            "SimpleAgent initialized",
            template_length=len(prompt_template)
        )
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt using template"""
        try:
            prompt = self.prompt_template.format(**inputs)
            self.logger.debug(
                "Prompt prepared",
                prompt_length=len(prompt)
            )
            return prompt
        except KeyError as e:
            self.logger.error(
                "Missing required input for prompt template",
                missing_key=str(e),
                available_keys=list(inputs.keys())
            )
            raise ValueError(f"Missing required input: {e}")
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Extract text from response"""
        content = response.get("content", [{}])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            self.logger.debug(
                "Response processed",
                response_length=len(text)
            )
            return text
        return ""


class ToolAgent(StrandsAgent):
    """
    Agent with tool-calling capabilities
    
    Can use tools to perform actions and gather information.
    Implements Strands SDK tool integration patterns.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        prompt_template: str,
        tool_handlers: Dict[str, Callable]
    ):
        super().__init__(config, bedrock_client)
        self.prompt_template = prompt_template
        self.tool_handlers = tool_handlers
        
        self.logger.info(
            "ToolAgent initialized",
            tool_count=len(tool_handlers),
            tools=list(tool_handlers.keys())
        )
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt with tool context"""
        try:
            return self.prompt_template.format(**inputs)
        except KeyError as e:
            raise ValueError(f"Missing required input: {e}")
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process response and handle tool calls"""
        content = response.get("content", [])
        
        results = []
        tool_calls = 0
        
        for item in content:
            if item.get("type") == "text":
                results.append(item.get("text", ""))
            elif item.get("type") == "tool_use":
                tool_name = item.get("name")
                tool_input = item.get("input", {})
                
                self.logger.info(
                    "Tool invocation",
                    tool_name=tool_name,
                    tool_input_keys=list(tool_input.keys())
                )
                
                if tool_name in self.tool_handlers:
                    try:
                        tool_result = self.tool_handlers[tool_name](tool_input)
                        tool_calls += 1
                        
                        self.logger.info(
                            "Tool execution successful",
                            tool_name=tool_name
                        )
                        
                        results.append({
                            "tool": tool_name,
                            "result": tool_result
                        })
                    except Exception as e:
                        self.logger.error(
                            "Tool execution failed",
                            tool_name=tool_name,
                            error=str(e),
                            exc_info=True
                        )
                        results.append({
                            "tool": tool_name,
                            "error": str(e)
                        })
                else:
                    self.logger.warning(
                        "Tool handler not found",
                        tool_name=tool_name,
                        available_tools=list(self.tool_handlers.keys())
                    )
        
        self.logger.debug(
            "Response processing complete",
            result_count=len(results),
            tool_calls=tool_calls
        )
        
        return results if len(results) > 1 else results[0] if results else ""


class ReasoningAgent(StrandsAgent):
    """
    Agent with structured reasoning capabilities
    
    Uses reasoning patterns like Chain-of-Thought, ReAct, etc.
    Implements Strands SDK reasoning patterns.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        reasoning_pattern: ReasoningPattern
    ):
        config.reasoning_pattern = reasoning_pattern
        super().__init__(config, bedrock_client)
        
        self.logger.info(
            "ReasoningAgent initialized",
            reasoning_pattern=reasoning_pattern.__class__.__name__
        )
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt for reasoning"""
        task = inputs.get("task", "")
        context = inputs.get("context", "")
        
        prompt = f"Task: {task}\n\nContext: {context}"
        
        self.logger.debug(
            "Reasoning prompt prepared",
            task_length=len(task),
            context_length=len(context)
        )
        
        return prompt
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Extract reasoning and final answer"""
        text = response.get("content", [{}])[0].get("text", "")
        
        # Parse reasoning steps and final answer
        lines = text.split("\n")
        reasoning_steps = []
        final_answer = ""
        
        for line in lines:
            if line.startswith("Step") or line.startswith("Thought"):
                reasoning_steps.append(line)
            elif line.startswith("Answer:") or line.startswith("Final Answer:"):
                final_answer = line.split(":", 1)[1].strip()
        
        self.logger.debug(
            "Reasoning extracted",
            reasoning_steps_count=len(reasoning_steps),
            has_final_answer=bool(final_answer)
        )
        
        return {
            "reasoning": reasoning_steps,
            "answer": final_answer or text
        }
