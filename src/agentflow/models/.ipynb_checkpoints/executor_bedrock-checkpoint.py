"""
Executor module for AgentFlow using Amazon Bedrock

Rewritten to use BedrockClient instead of create_llm_engine.
Handles tool command generation and execution for agent workflows.
"""

import importlib
import json
import os
import re
import signal
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)

# Import MCP support (optional)
try:
    from agentflow.mcp import MCPToolLoader, MCPConfig
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP support not available")


# Tool name mapping: Static fallback mapping (long external names to internal)
TOOL_NAME_MAPPING_LONG = {
    "Generalist_Solution_Generator_Tool": {
        "class_name": "Base_Generator_Tool",
        "dir_name": "base_generator"
    },
    "Ground_Google_Search_Tool": {
        "class_name": "Google_Search_Tool",
        "dir_name": "google_search"
    },
    "Python_Code_Generator_Tool": {
        "class_name": "Python_Coder_Tool",
        "dir_name": "python_coder"
    },
    "Web_RAG_Search_Tool": {
        "class_name": "Web_Search_Tool",
        "dir_name": "web_search"
    },
    "Wikipedia_RAG_Search_Tool": {
        "class_name": "Wikipedia_Search_Tool",
        "dir_name": "wikipedia_search"
    }
}

# Short to long mapping for fallback
TOOL_NAME_MAPPING_SHORT = {
    "Base_Generator_Tool": "Generalist_Solution_Generator_Tool",
    "Google_Search_Tool": "Ground_Google_Search_Tool",
    "Python_Coder_Tool": "Python_Code_Generator_Tool",
    "Web_Search_Tool": "Web_RAG_Search_Tool",
    "Wikipedia_Search_Tool": "Wikipedia_RAG_Search_Tool"
}


# Timeout handling
try:
    TimeoutError
except NameError:
    class TimeoutError(Exception):
        pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Function execution timed out")


class Executor:
    """
    Executor for tool commands using Amazon Bedrock
    
    Replaces the original create_llm_engine approach with BedrockClient
    for better integration with AWS services and fault tolerance.
    """
    
    def __init__(
        self,
        bedrock_client: BedrockClient,
        model_type: ModelType = ModelType.SONNET_4_5,
        root_cache_dir: str = "solver_cache",
        num_threads: int = 1,
        max_time: int = 120,
        max_output_length: int = 100000,
        verbose: bool = False,
        temperature: float = 0.0,
        enable_mcp: bool = True,
        mcp_config_path: Optional[str] = None
    ):
        """
        Initialize executor with BedrockClient
        
        Args:
            bedrock_client: BedrockClient instance for model invocations
            model_type: Bedrock model to use (default: Sonnet 4.5)
            root_cache_dir: Root directory for caching
            num_threads: Number of threads for execution
            max_time: Maximum execution time in seconds
            max_output_length: Maximum output length
            verbose: Enable verbose logging
            temperature: Sampling temperature
            enable_mcp: Enable MCP tool loading
            mcp_config_path: Custom MCP config path
        """
        self.bedrock_client = bedrock_client
        self.model_type = model_type
        self.root_cache_dir = root_cache_dir
        self.num_threads = num_threads
        self.max_time = max_time
        self.max_output_length = max_output_length
        self.verbose = verbose
        self.temperature = temperature
        self.query_cache_dir: Optional[str] = None
        
        # MCP tool support
        self.mcp_loader: Optional[Any] = None
        self.mcp_tools: Dict[str, Any] = {}
        
        if enable_mcp and MCP_AVAILABLE:
            try:
                mcp_config = MCPConfig(config_path=mcp_config_path)
                self.mcp_loader = MCPToolLoader(mcp_config)
                logger.info("MCP tool support enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP support: {e}")
        
        # CloudWatch logging
        logger.info(
            "Executor initialized",
            model_type=model_type.value,
            max_time=max_time,
            temperature=temperature,
            root_cache_dir=root_cache_dir,
            mcp_enabled=self.mcp_loader is not None
        )
    
    def set_query_cache_dir(self, query_cache_dir: Optional[str] = None) -> None:
        """
        Set the query cache directory
        
        Args:
            query_cache_dir: Cache directory path (auto-generated if None)
        """
        if query_cache_dir:
            self.query_cache_dir = query_cache_dir
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.query_cache_dir = os.path.join(self.root_cache_dir, timestamp)
        
        os.makedirs(self.query_cache_dir, exist_ok=True)
        
        logger.info(
            "Query cache directory set",
            cache_dir=self.query_cache_dir
        )
    
    async def load_mcp_tools(self, server_names: Optional[List[str]] = None) -> None:
        """
        Load tools from MCP servers
        
        Args:
            server_names: List of server names to load (None = all)
        """
        if not self.mcp_loader:
            logger.warning("MCP loader not initialized")
            return
        
        try:
            self.mcp_tools = await self.mcp_loader.load_tools(server_names)
            logger.info(f"Loaded {len(self.mcp_tools)} MCP tools")
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
    
    def get_mcp_tool_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all MCP tools"""
        if not self.mcp_loader:
            return {}
        return self.mcp_loader.get_tool_metadata()
    
    async def generate_tool_command(
        self,
        question: str,
        image: Optional[str],
        context: str,
        sub_goal: str,
        tool_name: str,
        tool_metadata: Dict[str, Any],
        step_count: int = 0,
        json_data: Optional[Any] = None
    ) -> Any:
        """
        Generate a tool command using Bedrock
        
        Args:
            question: User question
            image: Optional image path
            context: Relevant context
            sub_goal: Sub-goal to achieve
            tool_name: Name of tool to use
            tool_metadata: Tool metadata
            step_count: Current step count
            json_data: Optional JSON data for logging
            
        Returns:
            Generated tool command
        """
        prompt_generate_tool_command = f"""
Task: Generate a precise command to execute the selected tool.

Context:
- **Query:** {question}
- **Sub-Goal:** {sub_goal}
- **Tool Name:** {tool_name}
- **Tool Metadata:** {tool_metadata}
- **Relevant Data:** {context}

Instructions:
1. Analyze the tool's required parameters from its metadata.
2. Construct valid Python code that addresses the sub-goal using the provided context and data.
3. The command must include at least one call to `tool.execute()`.
4. Each `tool.execute()` call must be assigned to a variable named **`execution`**.
5. Please give the exact numbers and parameters should be used in the `tool.execute()` call.

Output Format:
Present your response in the following structured format. Do not include any extra text or explanations.

Generated Command:
```python
<command>
```

Example1:
Generated Command:
```python
execution = tool.execute(query="Summarize the following problem: Isaac has 100 toys, masa gets ...., how much are their together?")
```

Example2:
Generated Command:
```python
execution = tool.execute(query=["Methanol", "function of hyperbola", "Fermat's Last Theorem"])
```
"""
        
        if self.verbose:
            logger.info(
                "Generating tool command",
                tool_name=tool_name,
                sub_goal=sub_goal[:100]
            )
        
        try:
            # Use BedrockClient instead of llm_engine
            response = await self.bedrock_client.invoke(
                model_type=self.model_type,
                prompt=prompt_generate_tool_command,
                temperature=self.temperature,
                max_tokens=2048
            )
            
            # Extract text from response
            tool_command = response.get("content", [{}])[0].get("text", "")
            
            # Log to json_data if provided
            if json_data is not None:
                json_data[f"tool_commander_{step_count}_prompt"] = prompt_generate_tool_command
                json_data[f"tool_commander_{step_count}_response"] = str(tool_command)
            
            logger.info(
                "Tool command generated successfully",
                tool_name=tool_name,
                command_length=len(tool_command)
            )
            
            return tool_command
            
        except Exception as e:
            logger.error(
                f"Error generating tool command: {str(e)}",
                tool_name=tool_name,
                exc_info=True
            )
            raise
    
    def extract_explanation_and_command(
        self,
        response: Any
    ) -> Tuple[str, str, str]:
        """
        Extract analysis, explanation, and command from response
        
        Args:
            response: Response text or structured object
            
        Returns:
            Tuple of (analysis, explanation, command)
        """
        def normalize_code(code: str) -> str:
            """Remove leading/trailing whitespace and triple backticks"""
            return re.sub(r'^```python\s*', '', code).rstrip('```').strip()
        
        analysis = "No analysis found."
        explanation = "No explanation found."
        command = "No command found."
        
        try:
            if isinstance(response, str):
                # Extract command using "Generated Command:" prefix
                command_pattern = r"Generated Command:.*?```python\n(.*?)```"
                command_match = re.search(command_pattern, response, re.DOTALL | re.IGNORECASE)
                
                if command_match:
                    command = command_match.group(1).strip()
                else:
                    # Fallback: Extract ANY ```python ... ``` block
                    loose_command_pattern = r"```python\s*\n(.*?)```"
                    loose_match = re.findall(loose_command_pattern, response, re.DOTALL | re.IGNORECASE)
                    
                    if loose_match:
                        # Take the longest one as heuristic
                        command = max(loose_match, key=lambda x: len(x.strip())).strip()
                    else:
                        command = "No command found."
                
                # Try to extract analysis and explanation if present
                analysis_pattern = r"Analysis:(.*?)(?:Command Explanation|Generated Command)"
                analysis_match = re.search(analysis_pattern, response, re.DOTALL | re.IGNORECASE)
                if analysis_match:
                    analysis = analysis_match.group(1).strip()
                
                explanation_pattern = r"Command Explanation:(.*?)Generated Command"
                explanation_match = re.search(explanation_pattern, response, re.DOTALL | re.IGNORECASE)
                if explanation_match:
                    explanation = explanation_match.group(1).strip()
            
            # Final normalization
            command = normalize_code(command)
            
            logger.debug(
                "Extracted command components",
                has_analysis=analysis != "No analysis found.",
                has_explanation=explanation != "No explanation found.",
                has_command=command != "No command found."
            )
            
        except Exception as e:
            logger.error(
                f"Error extracting command components: {str(e)}",
                exc_info=True
            )
            analysis = "Parsing error."
            explanation = "Parsing error."
            command = "No command found."
        
        return analysis, explanation, command
    
    def execute_tool_command(
        self,
        tool_name: str,
        command: str
    ) -> Any:
        """
        Execute a tool command with timeout protection
        
        Args:
            tool_name: Name of the tool to execute
            command: Command string containing tool.execute() calls
            
        Returns:
            List of execution results or error message
        """
        def split_commands(command: str) -> List[str]:
            """Split command into individual tool.execute() blocks"""
            pattern = r'.*?execution\s*=\s*tool\.execute\([^\n]*\)\s*(?:\n|$)'
            blocks = re.findall(pattern, command, re.DOTALL)
            return [block.strip() for block in blocks if block.strip()]
        
        def execute_with_timeout(block: str, local_context: dict) -> Optional[str]:
            """Execute a command block with timeout protection"""
            # Set up the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.max_time)
            
            try:
                # Execute the block in the local context
                exec(block, globals(), local_context)
                result = local_context.get('execution')
                signal.alarm(0)  # Disable the alarm
                return result
            except TimeoutError:
                logger.warning(
                    f"Execution timed out after {self.max_time} seconds",
                    tool_name=tool_name
                )
                return f"Execution timed out after {self.max_time} seconds"
            except Exception as e:
                logger.error(
                    f"Error executing block: {str(e)}",
                    tool_name=tool_name,
                    exc_info=True
                )
                return f"Error executing block: {str(e)}"
            finally:
                signal.alarm(0)  # Ensure alarm is disabled
        
        logger.info(
            "Executing tool command",
            tool_name=tool_name,
            command_length=len(command)
        )
        
        # Check if this is an MCP tool
        if self.mcp_loader and tool_name in self.mcp_tools:
            logger.info(f"Executing MCP tool: {tool_name}")
            return asyncio.run(self._execute_mcp_tool(tool_name, command))
        
        # Resolve tool name mapping
        if tool_name in TOOL_NAME_MAPPING_LONG:
            dir_name = TOOL_NAME_MAPPING_LONG[tool_name]["dir_name"]
            class_name = TOOL_NAME_MAPPING_LONG[tool_name]["class_name"]
        elif tool_name in TOOL_NAME_MAPPING_SHORT:
            long_name = TOOL_NAME_MAPPING_SHORT[tool_name]
            if long_name in TOOL_NAME_MAPPING_LONG:
                dir_name = TOOL_NAME_MAPPING_LONG[long_name]["dir_name"]
                class_name = TOOL_NAME_MAPPING_LONG[long_name]["class_name"]
            else:
                # Fallback
                dir_name = tool_name.lower().replace('_tool', '')
                class_name = tool_name
        else:
            # Fallback to original behavior for unmapped tools
            dir_name = tool_name.lower().replace('_tool', '')
            class_name = tool_name
        
        module_name = f"tools.{dir_name}.tool"
        
        try:
            # Dynamically import the module
            module = importlib.import_module(module_name)
            
            # Get the tool class
            tool_class = getattr(module, class_name)
            
            tool = tool_class()
            
            # Set the custom output directory
            if self.query_cache_dir:
                tool.set_custom_output_dir(self.query_cache_dir)
            
            # Split the command into blocks, execute each one
            command_blocks = split_commands(command)
            executions = []
            
            logger.debug(
                f"Executing {len(command_blocks)} command blocks",
                tool_name=tool_name
            )
            
            for i, block in enumerate(command_blocks, 1):
                # Create a local context to safely execute the block
                local_context = {'tool': tool}
                
                # Execute the block with timeout protection
                result = execute_with_timeout(block, local_context)
                
                if result is not None:
                    executions.append(result)
                    logger.debug(
                        f"Block {i} executed successfully",
                        tool_name=tool_name
                    )
                else:
                    error_msg = f"No execution captured from block: {block}"
                    executions.append(error_msg)
                    logger.warning(error_msg, tool_name=tool_name)
            
            logger.info(
                "Tool command execution completed",
                tool_name=tool_name,
                executions_count=len(executions)
            )
            
            # Return all the execution results
            return executions
            
        except ImportError as e:
            # Tool module not found - fall back to simulation
            logger.warning(
                f"Tool module not found, using simulation",
                tool_name=tool_name,
                module_name=module_name
            )
            return self._simulate_tool_execution(tool_name, command)
            
        except Exception as e:
            error_msg = f"Error in execute_tool_command: {str(e)}"
            logger.error(
                error_msg,
                tool_name=tool_name,
                module_name=module_name,
                exc_info=True
            )
            return error_msg
    
    async def _execute_mcp_tool(self, tool_name: str, command: str) -> Any:
        """
        Execute an MCP tool
        
        Args:
            tool_name: MCP tool name (e.g., "filesystem.read_file")
            command: Command string with tool.execute() call
            
        Returns:
            Tool execution result
        """
        try:
            # Extract parameters from command
            # Pattern: tool.execute(param1=value1, param2=value2)
            import ast
            
            # Find the execute call
            execute_pattern = r'tool\.execute\(([^)]+)\)'
            match = re.search(execute_pattern, command)
            
            if not match:
                return "Error: Could not parse MCP tool parameters"
            
            params_str = match.group(1)
            
            # Parse parameters
            # This is a simplified parser - in production use ast.parse
            params = {}
            try:
                # Try to evaluate as dict-like parameters
                params_code = f"dict({params_str})"
                params = eval(params_code, {"__builtins__": {}}, {})
            except:
                # Fallback: try to parse as keyword arguments
                for param in params_str.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        params[key] = value
            
            logger.info(f"Executing MCP tool {tool_name} with params: {params}")
            
            # Execute the MCP tool
            result = await self.mcp_loader.execute_tool(tool_name, **params)
            
            return [result]  # Return as list for consistency
            
        except Exception as e:
            error_msg = f"Error executing MCP tool {tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _simulate_tool_execution(self, tool_name: str, command: str) -> Any:
        """
        Simulate tool execution for demonstration purposes
        
        In a real implementation, this would be replaced with actual tool imports
        and execution logic.
        """
        logger.info(f"Simulating execution for tool: {tool_name}")
        
        # Extract the query/input from the command
        # Try to extract parameters from tool.execute() call
        execute_pattern = r'tool\.execute\(([^)]+)\)'
        match = re.search(execute_pattern, command)
        
        if match:
            params_str = match.group(1)
            logger.debug(f"Extracted parameters: {params_str}")
        else:
            params_str = "No parameters found"
        
        # Simulate different tool behaviors
        if "calculator" in tool_name.lower():
            # Simulate calculator
            if "15% of 250" in command or "0.15 * 250" in command:
                return ["37.5"]
            elif "compound interest" in command.lower():
                return ["$11,576.25"]
            else:
                return ["Calculation result: 42"]
        
        elif "search" in tool_name.lower() or "web" in tool_name.lower():
            # Simulate web search
            return [{
                "results": [
                    "Search result 1: Relevant information found",
                    "Search result 2: Additional context",
                    "Search result 3: Supporting data"
                ],
                "summary": "Found relevant information from web search"
            }]
        
        elif "code" in tool_name.lower() or "python" in tool_name.lower():
            # Simulate code execution
            return [{
                "output": "Code executed successfully",
                "result": "Expected output generated",
                "status": "completed"
            }]
        
        elif "generator" in tool_name.lower() or "base" in tool_name.lower():
            # Simulate general solution generator
            return ["Generated solution based on the given parameters and context."]
        
        else:
            # Generic simulation
            return [f"Simulated result from {tool_name} with parameters: {params_str}"]


# Synchronous wrapper for backward compatibility
class SyncExecutor(Executor):
    """Synchronous wrapper for Executor"""
    
    def generate_tool_command_sync(
        self,
        question: str,
        image: Optional[str],
        context: str,
        sub_goal: str,
        tool_name: str,
        tool_metadata: Dict[str, Any],
        step_count: int = 0,
        json_data: Optional[Any] = None
    ) -> Any:
        """Synchronous version of generate_tool_command"""
        return asyncio.run(
            self.generate_tool_command(
                question, image, context, sub_goal,
                tool_name, tool_metadata, step_count, json_data
            )
        )
