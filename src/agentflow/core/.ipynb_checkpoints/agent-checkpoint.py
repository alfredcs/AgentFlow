"""
Agent implementation for AgentFlow
"""

import uuid
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import structlog

from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.patterns.reasoning import ReasoningPattern
from agentflow.utils.logging import setup_logger

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


class Agent(ABC):
    """
    Base agent class for AgentFlow
    
    Agents are the core execution units that interact with Bedrock models
    to perform specific tasks within a workflow.
    """
    
    def __init__(self, config: AgentConfig, bedrock_client: BedrockClient):
        self.config = config
        self.bedrock_client = bedrock_client
        self.agent_id = str(uuid.uuid4())
        self.logger = logger.bind(agent_id=self.agent_id, agent_name=config.name)
        self.execution_count = 0
        
    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Execute the agent with given inputs"""
        self.execution_count += 1
        execution_id = str(uuid.uuid4())
        
        self.logger.info(
            "Agent execution started",
            execution_id=execution_id,
            execution_count=self.execution_count
        )
        
        try:
            # Prepare the prompt
            prompt = self._prepare_prompt(inputs)
            
            # Apply reasoning pattern if configured
            if self.config.reasoning_pattern:
                prompt = self.config.reasoning_pattern.apply(prompt, inputs)
            
            # Execute with Bedrock
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
            
            self.logger.info(
                "Agent execution completed",
                execution_id=execution_id,
                model=self.config.model_type.value
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Agent execution failed",
                execution_id=execution_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    @abstractmethod
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare the prompt for the model"""
        pass
    
    @abstractmethod
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process the model response"""
        pass


class SimpleAgent(Agent):
    """
    Simple agent for straightforward tasks
    
    Uses a template-based approach for prompt generation.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        prompt_template: str
    ):
        super().__init__(config, bedrock_client)
        self.prompt_template = prompt_template
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt using template"""
        try:
            return self.prompt_template.format(**inputs)
        except KeyError as e:
            raise ValueError(f"Missing required input: {e}")
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Extract text from response"""
        return response.get("content", [{}])[0].get("text", "")


class ToolAgent(Agent):
    """
    Agent with tool-calling capabilities
    
    Can use tools to perform actions and gather information.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        prompt_template: str,
        tool_handlers: Dict[str, Any]
    ):
        super().__init__(config, bedrock_client)
        self.prompt_template = prompt_template
        self.tool_handlers = tool_handlers
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt with tool context"""
        return self.prompt_template.format(**inputs)
    
    def _process_response(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Any:
        """Process response and handle tool calls"""
        content = response.get("content", [])
        
        results = []
        for item in content:
            if item.get("type") == "text":
                results.append(item.get("text", ""))
            elif item.get("type") == "tool_use":
                tool_name = item.get("name")
                tool_input = item.get("input", {})
                
                if tool_name in self.tool_handlers:
                    tool_result = self.tool_handlers[tool_name](tool_input)
                    results.append({
                        "tool": tool_name,
                        "result": tool_result
                    })
        
        return results if len(results) > 1 else results[0] if results else ""


class ReasoningAgent(Agent):
    """
    Agent with structured reasoning capabilities
    
    Uses reasoning patterns like Chain-of-Thought, ReAct, etc.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        bedrock_client: BedrockClient,
        reasoning_pattern: ReasoningPattern
    ):
        config.reasoning_pattern = reasoning_pattern
        super().__init__(config, bedrock_client)
    
    def _prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt for reasoning"""
        task = inputs.get("task", "")
        context = inputs.get("context", "")
        
        return f"Task: {task}\n\nContext: {context}"
    
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
        
        return {
            "reasoning": reasoning_steps,
            "answer": final_answer or text
        }
