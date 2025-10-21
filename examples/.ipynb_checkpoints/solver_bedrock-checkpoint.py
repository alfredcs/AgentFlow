"""
Solver module for AgentFlow using Amazon Bedrock

Rewritten to use BedrockClient instead of llm_engine_name.
Orchestrates the complete AgentFlow system: planning, execution, and memory management.
"""

import argparse
import time
import json
import asyncio
from typing import Optional, Dict, Any, List

from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.models.planner_bedrock import Planner, Memory
from agentflow.models.executor_bedrock import Executor
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)


def make_json_serializable_truncated(obj: Any, max_length: int = 10000) -> Any:
    """
    Convert object to JSON serializable format with truncation
    
    Args:
        obj: Object to convert
        max_length: Maximum string length
        
    Returns:
        JSON serializable object
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        if isinstance(obj, str) and len(obj) > max_length:
            return obj[:max_length] + "... [truncated]"
        return obj
    elif isinstance(obj, dict):
        return {k: make_json_serializable_truncated(v, max_length) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable_truncated(item, max_length) for item in obj]
    else:
        str_repr = str(obj)
        if len(str_repr) > max_length:
            return str_repr[:max_length] + "... [truncated]"
        return str_repr


class Solver:
    """
    Main solver class for AgentFlow using Amazon Bedrock
    
    Orchestrates the complete workflow:
    1. Query analysis
    2. Multi-step planning and execution
    3. Memory management
    4. Result generation
    """
    
    def __init__(
        self,
        planner: Planner,
        memory: Memory,
        executor: Executor,
        output_types: str = "base,final,direct",
        max_steps: int = 10,
        max_time: int = 300,
        max_tokens: int = 4000,
        root_cache_dir: str = "cache",
        verbose: bool = True,
        temperature: float = 0.0
    ):
        """
        Initialize solver
        
        Args:
            planner: Planner instance
            memory: Memory instance
            executor: Executor instance
            output_types: Comma-separated output types (base,final,direct)
            max_steps: Maximum execution steps
            max_time: Maximum execution time in seconds
            max_tokens: Maximum tokens for generation
            root_cache_dir: Root cache directory
            verbose: Enable verbose output
            temperature: Sampling temperature
        """
        self.planner = planner
        self.memory = memory
        self.executor = executor
        self.max_steps = max_steps
        self.max_time = max_time
        self.max_tokens = max_tokens
        self.root_cache_dir = root_cache_dir
        self.temperature = temperature
        
        self.output_types = output_types.lower().split(',')
        assert all(
            output_type in ["base", "final", "direct"] 
            for output_type in self.output_types
        ), "Invalid output type. Supported types are 'base', 'final', 'direct'."
        
        self.verbose = verbose
        
        logger.info(
            "Solver initialized",
            output_types=self.output_types,
            max_steps=max_steps,
            max_time=max_time,
            temperature=temperature
        )
    
    async def solve(
        self,
        question: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solve a problem using AgentFlow
        
        Args:
            question: Question to solve
            image_path: Optional image path
            
        Returns:
            Dictionary with results
        """
        # Update cache directory for the executor
        self.executor.set_query_cache_dir(self.root_cache_dir)
        
        # Initialize json_data with basic problem information
        json_data = {
            "query": question,
            "image": image_path
        }
        
        if self.verbose:
            print(f"\n==> 🔍 Received Query: {question}")
            if image_path:
                print(f"\n==> 🖼️ Received Image: {image_path}")
        
        logger.info(
            "Starting solve",
            question=question[:100],
            has_image=image_path is not None
        )
        
        # Generate base response if requested
        if 'base' in self.output_types:
            base_response = await self.planner.generate_base_response(
                question,
                image_path,
                self.max_tokens
            )
            json_data["base_response"] = base_response
            
            if self.verbose:
                print(f"\n==> 📝 Base Response from LLM:\n\n{base_response}")
            
            logger.info("Base response generated")
        
        # If only base response is needed, save and return
        if set(self.output_types) == {'base'}:
            return json_data
        
        # Continue with query analysis and tool execution
        if {'final', 'direct'} & set(self.output_types):
            if self.verbose:
                print(f"\n==> 🐙 Reasoning Steps from AgentFlow (Deep Thinking...)")
            
            # [1] Analyze query
            query_start_time = time.time()
            query_analysis = await self.planner.analyze_query(question, image_path)
            json_data["query_analysis"] = query_analysis
            
            if self.verbose:
                print(f"\n==> 🔍 Step 0: Query Analysis\n")
                print(f"{query_analysis}")
                print(f"[Time]: {round(time.time() - query_start_time, 2)}s")
            
            logger.info("Query analysis completed")
            
            # Main execution loop
            step_count = 0
            action_times = []
            
            while step_count < self.max_steps and (time.time() - query_start_time) < self.max_time:
                step_count += 1
                step_start_time = time.time()
                
                logger.info(f"Starting step {step_count}")
                
                # [2] Generate next step
                local_start_time = time.time()
                next_step = await self.planner.generate_next_step(
                    question,
                    image_path,
                    query_analysis,
                    self.memory,
                    step_count,
                    self.max_steps,
                    json_data
                )
                
                context, sub_goal, tool_name = self.planner.extract_context_subgoal_and_tool(next_step)
                
                # Log extraction results for debugging
                logger.debug(
                    "Extracted step components",
                    context_found=context is not None,
                    sub_goal_found=sub_goal is not None,
                    tool_name_found=tool_name is not None,
                    tool_name=tool_name
                )
                
                if self.verbose:
                    print(f"\n==> 🎯 Step {step_count}: Action Prediction ({tool_name})\n")
                    print(f"[Context]: {context}\n[Sub Goal]: {sub_goal}\n[Tool]: {tool_name}")
                    print(f"[Time]: {round(time.time() - local_start_time, 2)}s")
                
                # Check if extraction failed
                if context is None or sub_goal is None or tool_name is None:
                    logger.warning(
                        "Failed to extract step components from response",
                        next_step_preview=next_step[:200] if isinstance(next_step, str) else str(next_step)[:200]
                    )
                    print(f"\n==> ⚠️ Warning: Could not parse next step response")
                    print(f"Response preview: {next_step[:200] if isinstance(next_step, str) else str(next_step)[:200]}")
                    
                    # Try to continue with a default action or break
                    if step_count >= 2:  # If we've made some progress, stop gracefully
                        logger.info("Stopping execution due to parsing failure after progress")
                        break
                    else:
                        # For first step, try to generate a direct answer
                        logger.info("Attempting direct answer generation")
                        tool_name = "FINISH"
                        context = "Unable to parse planning response"
                        sub_goal = "Generate direct answer"
                
                # Check if we should finish
                if tool_name and "FINISH" in tool_name.upper():
                    logger.info("Received FINISH signal, stopping execution")
                    break
                
                if tool_name not in self.planner.available_tools:
                    logger.warning(f"Tool '{tool_name}' not available")
                    print(f"\n==> 🚫 Error: Tool '{tool_name}' is not available or not found.")
                    command = "No command was generated because the tool was not found."
                    result = "No result was generated because the tool was not found."
                else:
                    # [3] Generate the tool command
                    local_start_time = time.time()
                    tool_command = await self.executor.generate_tool_command(
                        question,
                        image_path,
                        context,
                        sub_goal,
                        tool_name,
                        self.planner.toolbox_metadata.get(tool_name, {}),
                        step_count,
                        json_data
                    )
                    
                    analysis, explanation, command = self.executor.extract_explanation_and_command(tool_command)
                    
                    if self.verbose:
                        print(f"\n==> 📝 Step {step_count}: Command Generation ({tool_name})\n")
                        print(f"[Analysis]: {analysis}\n[Explanation]: {explanation}\n[Command]: {command}")
                        print(f"[Time]: {round(time.time() - local_start_time, 2)}s")
                    
                    # [4] Execute the tool command
                    local_start_time = time.time()
                    result = self.executor.execute_tool_command(tool_name, command)
                    result = make_json_serializable_truncated(result)
                    json_data[f"tool_result_{step_count}"] = result
                    
                    if self.verbose:
                        print(f"\n==> 🛠️ Step {step_count}: Command Execution ({tool_name})\n")
                        print(f"[Result]:\n{json.dumps(result, indent=4)}")
                        print(f"[Time]: {round(time.time() - local_start_time, 2)}s")
                
                # Track execution time for the current step
                execution_time_step = round(time.time() - step_start_time, 2)
                action_times.append(execution_time_step)
                
                # Update memory
                self.memory.add_action({
                    "step": step_count,
                    "tool": tool_name,
                    "sub_goal": sub_goal,
                    "command": command,
                    "result": result
                })
                
                logger.info(
                    f"Step {step_count} completed",
                    tool=tool_name,
                    execution_time=execution_time_step
                )
            
            # Add memory and statistics to json_data
            json_data.update({
                "memory": self.memory.get_actions(),
                "step_count": step_count,
                "execution_time": round(time.time() - query_start_time, 2),
            })
            
            # Generate final output if requested
            if 'final' in self.output_types:
                final_output = await self._generate_final_output(question, image_path)
                json_data["final_output"] = final_output
                print(f"\n==> 🐙 Detailed Solution:\n\n{final_output}")
            
            # Generate direct output if requested
            if 'direct' in self.output_types:
                direct_output = await self._generate_direct_output(question, image_path)
                json_data["direct_output"] = direct_output
                print(f"\n==> 🐙 Final Answer:\n\n{direct_output}")
            
            print(f"\n[Total Time]: {round(time.time() - query_start_time, 2)}s")
            print(f"\n==> ✅ Query Solved!")
            
            logger.info(
                "Solve completed",
                step_count=step_count,
                total_time=round(time.time() - query_start_time, 2)
            )
        
        return json_data
    
    async def _generate_final_output(
        self,
        question: str,
        image_path: Optional[str]
    ) -> str:
        """Generate detailed final output"""
        prompt = f"""
Based on the following question and execution history, provide a detailed solution.

Question: {question}

Execution History:
{self.memory.get_actions()}

Provide a comprehensive, step-by-step explanation of how the problem was solved.
"""
        
        response = await self.planner.bedrock_client.invoke(
            model_type=self.planner.model_type,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.get("content", [{}])[0].get("text", "")
    
    async def _generate_direct_output(
        self,
        question: str,
        image_path: Optional[str]
    ) -> str:
        """Generate concise direct answer"""
        prompt = f"""
Based on the following question and execution history, provide a concise final answer.

Question: {question}

Execution History:
{self.memory.get_actions()}

Provide only the final answer, without explanation.
"""
        
        response = await self.planner.bedrock_client.invoke(
            model_type=self.planner.model_type,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=500
        )
        
        return response.get("content", [{}])[0].get("text", "")


def construct_solver(
    bedrock_client: Optional[BedrockClient] = None,
    model_type: ModelType = ModelType.SONNET_4_5,
    enabled_tools: Optional[List[str]] = None,
    toolbox_metadata: Optional[Dict[str, Any]] = None,
    output_types: str = "final,direct",
    max_steps: int = 10,
    max_time: int = 300,
    max_tokens: int = 4000,
    root_cache_dir: str = "solver_cache",
    verbose: bool = True,
    temperature: float = 0.0,
    region_name: str = "us-east-1"
) -> Solver:
    """
    Construct a Solver instance with BedrockClient
    
    Args:
        bedrock_client: BedrockClient instance (created if None)
        model_type: Bedrock model to use
        enabled_tools: List of enabled tool names
        toolbox_metadata: Tool metadata dictionary
        output_types: Comma-separated output types
        max_steps: Maximum execution steps
        max_time: Maximum execution time
        max_tokens: Maximum tokens for generation
        root_cache_dir: Root cache directory
        verbose: Enable verbose output
        temperature: Sampling temperature
        region_name: AWS region name
        
    Returns:
        Configured Solver instance
    """
    # Create BedrockClient if not provided
    if bedrock_client is None:
        bedrock_client = BedrockClient(region_name=region_name)
    
    # Default tools and metadata
    if enabled_tools is None:
        enabled_tools = ["calculator", "web_search", "code_interpreter"]
    
    if toolbox_metadata is None:
        toolbox_metadata = {
            "calculator": {
                "description": "Performs mathematical calculations",
                "parameters": {"expression": "Mathematical expression"}
            },
            "web_search": {
                "description": "Searches the web for information",
                "parameters": {"query": "Search query"}
            },
            "code_interpreter": {
                "description": "Executes Python code",
                "parameters": {"code": "Python code to execute"}
            }
        }
    
    # Instantiate Planner
    planner = Planner(
        bedrock_client=bedrock_client,
        model_type=model_type,
        toolbox_metadata=toolbox_metadata,
        available_tools=enabled_tools,
        verbose=verbose,
        temperature=temperature
    )
    
    # Instantiate Memory
    memory = Memory()
    
    # Instantiate Executor
    executor = Executor(
        bedrock_client=bedrock_client,
        model_type=model_type,
        root_cache_dir=root_cache_dir,
        verbose=verbose,
        temperature=temperature
    )
    
    # Instantiate Solver
    solver = Solver(
        planner=planner,
        memory=memory,
        executor=executor,
        output_types=output_types,
        max_steps=max_steps,
        max_time=max_time,
        max_tokens=max_tokens,
        root_cache_dir=root_cache_dir,
        verbose=verbose,
        temperature=temperature
    )
    
    logger.info("Solver constructed successfully")
    
    return solver


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run AgentFlow solver with Amazon Bedrock"
    )
    parser.add_argument(
        "--model_type",
        default="sonnet",
        choices=["sonnet", "haiku"],
        help="Model type: sonnet (Sonnet 4.5) or haiku (Haiku 4.5)"
    )
    parser.add_argument(
        "--output_types",
        default="base,final,direct",
        help="Comma-separated list of required outputs (base,final,direct)"
    )
    parser.add_argument(
        "--enabled_tools",
        default="calculator,web_search",
        help="Comma-separated list of enabled tools"
    )
    parser.add_argument(
        "--root_cache_dir",
        default="solver_cache",
        help="Path to solver cache directory"
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=4000,
        help="Maximum tokens for LLM generation"
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=10,
        help="Maximum number of steps to execute"
    )
    parser.add_argument(
        "--max_time",
        type=int,
        default=300,
        help="Maximum time allowed in seconds"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region name"
    )
    parser.add_argument(
        "--prompt",
        default="What were the cpatials of China since the Qin dynasty?",
        help="Your question"
    )
    
    return parser.parse_args()


async def main_async(args):
    """Async main function"""
    # Map model type
    model_type = ModelType.SONNET_4_5 if args.model_type == "sonnet" else ModelType.HAIKU_4_5
    
    # Parse enabled tools
    enabled_tools = args.enabled_tools.split(',')
    
    # Construct solver
    solver = construct_solver(
        model_type=model_type,
        enabled_tools=enabled_tools,
        output_types=args.output_types,
        max_steps=args.max_steps,
        max_time=args.max_time,
        max_tokens=args.max_tokens,
        root_cache_dir=args.root_cache_dir,
        verbose=args.verbose,
        temperature=args.temperature,
        region_name=args.region
    )
    
    # Solve the task
    result = await solver.solve(args.prompt)
    
    # Save result
    output_file = f"{args.root_cache_dir}/result.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n==> 💾 Result saved to: {output_file}")


def main(args):
    """Main entry point"""
    asyncio.run(main_async(args))


if __name__ == "__main__":
    args = parse_arguments()
    main(args)

