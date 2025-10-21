"""
Planner module for AgentFlow using Amazon Bedrock

Rewritten to use BedrockClient instead of create_llm_engine.
Implements planning and reasoning capabilities for agent workflows.
"""

import json
import os
import re
import asyncio
from typing import Any, Dict, List, Tuple, Optional
from PIL import Image

from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)


class Memory:
    """Simple memory implementation for tracking actions"""
    
    def __init__(self):
        self.actions: List[Dict[str, Any]] = []
    
    def add_action(self, action: Dict[str, Any]) -> None:
        """Add an action to memory"""
        self.actions.append(action)
    
    def get_actions(self) -> str:
        """Get formatted actions string"""
        if not self.actions:
            return "No previous actions"
        
        formatted = []
        for i, action in enumerate(self.actions, 1):
            formatted.append(f"Step {i}: {action}")
        return "\n".join(formatted)
    
    def clear(self) -> None:
        """Clear all actions"""
        self.actions.clear()


class Planner:
    """
    Planner for agent workflows using Amazon Bedrock
    
    Replaces the original create_llm_engine approach with BedrockClient
    for better integration with AWS services and fault tolerance.
    """
    
    def __init__(
        self,
        bedrock_client: BedrockClient,
        model_type: ModelType = ModelType.SONNET_4_5,
        toolbox_metadata: Optional[Dict] = None,
        available_tools: Optional[List[str]] = None,
        verbose: bool = False,
        is_multimodal: bool = False,
        temperature: float = 0.0
    ):
        """
        Initialize planner with BedrockClient
        
        Args:
            bedrock_client: BedrockClient instance for model invocations
            model_type: Bedrock model to use (default: Sonnet 4)
            toolbox_metadata: Metadata about available tools
            available_tools: List of available tool names
            verbose: Enable verbose logging
            is_multimodal: Enable multimodal support
            temperature: Sampling temperature
        """
        self.bedrock_client = bedrock_client
        self.model_type = model_type
        self.is_multimodal = is_multimodal
        self.temperature = temperature
        self.toolbox_metadata = toolbox_metadata if toolbox_metadata is not None else {}
        self.available_tools = available_tools if available_tools is not None else []
        self.verbose = verbose
        
        # CloudWatch logging
        logger.info(
            "Planner initialized",
            model_type=model_type.value,
            is_multimodal=is_multimodal,
            tools_count=len(self.available_tools),
            temperature=temperature
        )
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        Get image information from file path
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with image metadata
        """
        image_info = {}
        if image_path and os.path.isfile(image_path):
            image_info["image_path"] = image_path
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                image_info.update({
                    "width": width,
                    "height": height
                })
                logger.debug(f"Image info extracted: {width}x{height}")
            except Exception as e:
                logger.error(f"Error processing image file: {str(e)}")
        return image_info
    
    async def generate_base_response(
        self,
        question: str,
        image: Optional[str] = None,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate base response using Bedrock
        
        Args:
            question: User question
            image: Optional image path
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        image_info = self.get_image_info(image) if image else {}
        
        # Prepare prompt
        prompt = question
        if image_info:
            prompt = f"Question: {question}\n\nImage info: {image_info}"
        
        if self.verbose:
            logger.info(f"Generating base response for: {question[:100]}...")
        
        try:
            # Use BedrockClient instead of llm_engine
            response = await self.bedrock_client.invoke(
                model_type=self.model_type,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            # Extract text from response
            self.base_response = response.get("content", [{}])[0].get("text", "")
            
            logger.info("Base response generated successfully")
            return self.base_response
            
        except Exception as e:
            logger.error(f"Error generating base response: {str(e)}", exc_info=True)
            raise
    
    async def analyze_query(
        self,
        question: str,
        image: Optional[str] = None
    ) -> str:
        """
        Analyze query to determine required skills and tools
        
        Args:
            question: User query
            image: Optional image path
            
        Returns:
            Query analysis text
        """
        image_info = self.get_image_info(image) if image else {}
        
        if self.is_multimodal and image_info:
            query_prompt = f"""
Task: Analyze the given query with accompanying inputs and determine the skills and tools needed to address it effectively.

Available tools: {self.available_tools}

Metadata for the tools: {self.toolbox_metadata}

Image: {image_info}

Query: {question}

Instructions:
1. Carefully read and understand the query and any accompanying inputs.
2. Identify the main objectives or tasks within the query.
3. List the specific skills that would be necessary to address the query comprehensively.
4. Examine the available tools in the toolbox and determine which ones might be relevant and useful for addressing the query.
5. Provide a brief explanation for each skill and tool you've identified, describing how it would contribute to answering the query.

Your response should include:
1. A concise summary of the query's main points and objectives.
2. A list of required skills, with a brief explanation for each.
3. A list of relevant tools from the toolbox, with a brief explanation of how each tool would be utilized.
4. Any additional considerations that might be important for addressing the query effectively.

Please present your analysis in a clear, structured format.
"""
        else:
            query_prompt = f"""
Task: Analyze the given query to determine necessary skills and tools.

Inputs:
- Query: {question}
- Available tools: {self.available_tools}
- Metadata for tools: {self.toolbox_metadata}

Instructions:
1. Identify the main objectives in the query.
2. List the necessary skills and tools.
3. For each skill and tool, explain how it helps address the query.
4. Note any additional considerations.

Format your response with a summary of the query, lists of skills and tools with explanations, and a section for additional considerations.

Be brief and precise with insight.
"""
        
        if self.verbose:
            logger.info(f"Analyzing query: {question[:100]}...")
        
        try:
            # Use BedrockClient instead of llm_engine
            response = await self.bedrock_client.invoke(
                model_type=self.model_type,
                prompt=query_prompt,
                temperature=self.temperature,
                max_tokens=2048
            )
            
            # Extract text from response
            self.query_analysis = response.get("content", [{}])[0].get("text", "")
            
            logger.info("Query analysis completed successfully")
            return str(self.query_analysis).strip()
            
        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}", exc_info=True)
            raise
    
    def extract_context_subgoal_and_tool(
        self,
        response: Any
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract context, sub-goal, and tool name from response
        
        Args:
            response: Response text or structured object
            
        Returns:
            Tuple of (context, sub_goal, tool_name)
        """
        def normalize_tool_name(tool_name: str) -> str:
            """Normalize tool name to match available tools"""
            def to_canonical(name: str) -> str:
                parts = re.split('[ _]+', name)
                return "_".join(part.lower() for part in parts)
            
            normalized_input = to_canonical(tool_name)
            
            for tool in self.available_tools:
                if to_canonical(tool) == normalized_input:
                    return tool
            
            logger.warning(f"No matched tool for: {tool_name}")
            return f"No matched tool given: {tool_name}"
        
        try:
            if isinstance(response, str):
                # Parse text response
                text = response.replace("**", "")
                
                # Pattern to match the format
                pattern = r"Context:\s*(.*?)Sub-Goal:\s*(.*?)Tool Name:\s*(.*?)\s*(?:```)?\\s*(?=\n\n|\Z)"
                matches = re.findall(pattern, text, re.DOTALL)
                
                if matches:
                    context, sub_goal, tool_name = matches[-1]
                    context = context.strip()
                    sub_goal = sub_goal.strip()
                    tool_name = normalize_tool_name(tool_name.strip())
                    
                    logger.debug(
                        "Extracted planning components",
                        context_length=len(context),
                        sub_goal_length=len(sub_goal),
                        tool_name=tool_name
                    )
                    
                    return context, sub_goal, tool_name
                else:
                    logger.warning("No matches found in response")
                    return None, None, None
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                return None, None, None
                
        except Exception as e:
            logger.error(
                f"Error extracting context, sub-goal, and tool name: {str(e)}",
                exc_info=True
            )
            return None, None, None
    
    async def generate_next_step(
        self,
        question: str,
        image: Optional[str],
        query_analysis: str,
        memory: Memory,
        step_count: int,
        max_step_count: int,
        json_data: Optional[Any] = None
    ) -> Any:
        """
        Generate the next step in the workflow
        
        Args:
            question: User question
            image: Optional image path
            query_analysis: Analysis of the query
            memory: Memory of previous actions
            step_count: Current step count
            max_step_count: Maximum allowed steps
            json_data: Optional JSON data
            
        Returns:
            Next step information
        """
        image_info = self.get_image_info(image) if image else "No image provided"
        
        if self.is_multimodal:
            prompt_generate_next_step = f"""
Task: Determine the optimal next step to address the given query based on the provided analysis, available tools, and previous steps taken.

Context:
Query: {question}
Image: {image_info}
Query Analysis: {query_analysis}

Available Tools:
{self.available_tools}

Tool Metadata:
{self.toolbox_metadata}

Previous Steps and Their Results:
{memory.get_actions()}

Current Progress:
- Step Count: {step_count}/{max_step_count}

Instructions:
1. Review the query, analysis, and previous steps.
2. Determine if the query has been fully addressed or if additional steps are needed.
3. If more steps are needed, identify the most appropriate next action and tool to use.
4. Provide your response in the following format:

Context: [Brief summary of the current situation and what has been accomplished]
Sub-Goal: [The specific objective for the next step]
Tool Name: [The exact name of the tool to be used, or "FINISH" if the task is complete]

Important:
- Use "FINISH" as the Tool Name only when the query has been fully addressed.
- Ensure the Tool Name exactly matches one from the available tools list.
- Be concise but informative in your Context and Sub-Goal descriptions.
"""
        else:
            prompt_generate_next_step = f"""
Task: Determine the next step to address the query.

Context:
Query: {question}
Query Analysis: {query_analysis}

Available Tools: {self.available_tools}
Tool Metadata: {self.toolbox_metadata}

Previous Steps:
{memory.get_actions()}

Progress: Step {step_count}/{max_step_count}

Instructions:
1. Review the query, analysis, and previous steps.
2. Determine if more steps are needed.
3. Provide response in this format:

Context: [Current situation summary]
Sub-Goal: [Next step objective]
Tool Name: [Tool to use, or "FINISH" if complete]

Use "FINISH" only when the query is fully addressed.
Ensure Tool Name matches available tools exactly.
"""
        
        if self.verbose:
            logger.info(f"Generating next step (step {step_count}/{max_step_count})")
        
        try:
            # Use BedrockClient instead of llm_engine
            response = await self.bedrock_client.invoke(
                model_type=self.model_type,
                prompt=prompt_generate_next_step,
                temperature=self.temperature,
                max_tokens=1024
            )
            
            # Extract text from response
            next_step_text = response.get("content", [{}])[0].get("text", "")
            
            logger.info("Next step generated successfully")
            return next_step_text
            
        except Exception as e:
            logger.error(f"Error generating next step: {str(e)}", exc_info=True)
            raise
    
    async def verify_memory(
        self,
        question: str,
        memory: Memory,
        final_answer: str
    ) -> bool:
        """
        Verify if the memory and final answer address the question
        
        Args:
            question: Original question
            memory: Memory of actions taken
            final_answer: Final answer generated
            
        Returns:
            True if verification passes, False otherwise
        """
        verification_prompt = f"""
Task: Verify if the actions taken and final answer adequately address the original question.

Original Question: {question}

Actions Taken:
{memory.get_actions()}

Final Answer: {final_answer}

Instructions:
1. Review the original question carefully.
2. Examine the actions taken and their results.
3. Evaluate the final answer.
4. Determine if the question has been fully and accurately addressed.

Respond with:
- "VERIFIED" if the answer adequately addresses the question
- "NOT_VERIFIED" if the answer is incomplete or incorrect

Provide a brief explanation for your decision.
"""
        
        if self.verbose:
            logger.info("Verifying memory and final answer")
        
        try:
            # Use BedrockClient for verification
            response = await self.bedrock_client.invoke(
                model_type=self.model_type,
                prompt=verification_prompt,
                temperature=0.0,  # Use 0 for verification
                max_tokens=512
            )
            
            # Extract text from response
            verification_text = response.get("content", [{}])[0].get("text", "")
            
            # Check if verified
            is_verified = "VERIFIED" in verification_text.upper() and "NOT_VERIFIED" not in verification_text.upper()
            
            logger.info(
                "Memory verification completed",
                is_verified=is_verified,
                verification_text=verification_text[:100]
            )
            
            return is_verified
            
        except Exception as e:
            logger.error(f"Error verifying memory: {str(e)}", exc_info=True)
            return False


# Synchronous wrapper for backward compatibility
class SyncPlanner(Planner):
    """Synchronous wrapper for Planner"""
    
    def generate_base_response_sync(
        self,
        question: str,
        image: Optional[str] = None,
        max_tokens: int = 2048
    ) -> str:
        """Synchronous version of generate_base_response"""
        return asyncio.run(self.generate_base_response(question, image, max_tokens))
    
    def analyze_query_sync(
        self,
        question: str,
        image: Optional[str] = None
    ) -> str:
        """Synchronous version of analyze_query"""
        return asyncio.run(self.analyze_query(question, image))
    
    def generate_next_step_sync(
        self,
        question: str,
        image: Optional[str],
        query_analysis: str,
        memory: Memory,
        step_count: int,
        max_step_count: int,
        json_data: Optional[Any] = None
    ) -> Any:
        """Synchronous version of generate_next_step"""
        return asyncio.run(
            self.generate_next_step(
                question, image, query_analysis, memory,
                step_count, max_step_count, json_data
            )
        )
    
    def verify_memory_sync(
        self,
        question: str,
        memory: Memory,
        final_answer: str
    ) -> bool:
        """Synchronous version of verify_memory"""
        return asyncio.run(self.verify_memory(question, memory, final_answer))
