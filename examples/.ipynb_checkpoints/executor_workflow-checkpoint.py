"""
Example usage of the Executor with BedrockClient

Demonstrates how to use the rewritten Executor that uses BedrockClient
instead of create_llm_engine.
"""

import asyncio
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.models.executor_bedrock import Executor


async def main():
    """Demonstrate executor usage"""
    
    print("=" * 60)
    print("AgentFlow Executor Example with BedrockClient")
    print("=" * 60)
    print()
    
    # Initialize Bedrock client
    bedrock = BedrockClient(region_name="us-east-1")
    print("✓ Bedrock client initialized")
    
    # Create executor
    executor = Executor(
        bedrock_client=bedrock,
        model_type=ModelType.SONNET_4,
        root_cache_dir="./executor_cache",
        max_time=120,
        verbose=True,
        temperature=0.0
    )
    print("✓ Executor initialized")
    print(f"  - Model: {ModelType.SONNET_4.value}")
    print(f"  - Max execution time: 120s")
    print(f"  - Temperature: 0.0")
    print()
    
    # Set cache directory
    executor.set_query_cache_dir()
    print(f"✓ Cache directory: {executor.query_cache_dir}")
    print()
    
    # Example 1: Generate tool command for calculator
    print("-" * 60)
    print("Example 1: Generate Calculator Tool Command")
    print("-" * 60)
    
    question = "What is 15% of 250?"
    context = "Need to calculate percentage"
    sub_goal = "Calculate 15% of 250"
    tool_name = "calculator"
    tool_metadata = {
        "description": "Performs mathematical calculations",
        "parameters": {
            "expression": "Mathematical expression to evaluate"
        }
    }
    
    print(f"Question: {question}")
    print(f"Sub-Goal: {sub_goal}")
    print(f"Tool: {tool_name}")
    print()
    
    tool_command = await executor.generate_tool_command(
        question=question,
        image=None,
        context=context,
        sub_goal=sub_goal,
        tool_name=tool_name,
        tool_metadata=tool_metadata,
        step_count=1
    )
    
    print("Generated Tool Command:")
    print(tool_command)
    print()
    
    # Extract components
    analysis, explanation, command = executor.extract_explanation_and_command(tool_command)
    
    print("Extracted Components:")
    if analysis != "No analysis found.":
        print(f"  Analysis: {analysis[:100]}...")
    if explanation != "No explanation found.":
        print(f"  Explanation: {explanation[:100]}...")
    print(f"  Command: {command}")
    print()
    
    # Example 2: Generate tool command for web search
    print("-" * 60)
    print("Example 2: Generate Web Search Tool Command")
    print("-" * 60)
    
    question2 = "What is the current inflation rate in the US?"
    context2 = "Need to search for current economic data"
    sub_goal2 = "Search for current US inflation rate"
    tool_name2 = "web_search"
    tool_metadata2 = {
        "description": "Searches the web for information",
        "parameters": {
            "query": "Search query string"
        }
    }
    
    print(f"Question: {question2}")
    print(f"Sub-Goal: {sub_goal2}")
    print(f"Tool: {tool_name2}")
    print()
    
    tool_command2 = await executor.generate_tool_command(
        question=question2,
        image=None,
        context=context2,
        sub_goal=sub_goal2,
        tool_name=tool_name2,
        tool_metadata=tool_metadata2,
        step_count=2
    )
    
    print("Generated Tool Command:")
    print(tool_command2)
    print()
    
    # Extract components
    analysis2, explanation2, command2 = executor.extract_explanation_and_command(tool_command2)
    
    print("Extracted Components:")
    if analysis2 != "No analysis found.":
        print(f"  Analysis: {analysis2[:100]}...")
    if explanation2 != "No explanation found.":
        print(f"  Explanation: {explanation2[:100]}...")
    print(f"  Command: {command2}")
    print()
    
    # Example 3: Tool name mapping
    print("-" * 60)
    print("Example 3: Tool Name Mapping")
    print("-" * 60)
    
    from agentflow.models.executor import TOOL_NAME_MAPPING_LONG, TOOL_NAME_MAPPING_SHORT
    
    print("Long to Short Mapping:")
    for long_name, mapping in TOOL_NAME_MAPPING_LONG.items():
        print(f"  {long_name}")
        print(f"    -> Class: {mapping['class_name']}")
        print(f"    -> Directory: {mapping['dir_name']}")
    print()
    
    print("Short to Long Mapping:")
    for short_name, long_name in TOOL_NAME_MAPPING_SHORT.items():
        print(f"  {short_name} -> {long_name}")
    print()
    
    # Example 4: Multi-step workflow
    print("-" * 60)
    print("Example 4: Multi-Step Workflow")
    print("-" * 60)
    
    workflow_question = "Calculate the compound interest on $10,000 at 5% for 3 years"
    
    # Step 1: Generate command for calculation
    print("Step 1: Generate calculation command")
    step1_command = await executor.generate_tool_command(
        question=workflow_question,
        image=None,
        context="Need to calculate compound interest using formula A = P(1 + r)^t",
        sub_goal="Calculate compound interest",
        tool_name="calculator",
        tool_metadata={
            "description": "Performs mathematical calculations",
            "parameters": {"expression": "Mathematical expression"}
        },
        step_count=1
    )
    
    _, _, cmd1 = executor.extract_explanation_and_command(step1_command)
    print(f"Command: {cmd1}")
    print()
    
    # Step 2: Generate command for formatting result
    print("Step 2: Generate formatting command")
    step2_command = await executor.generate_tool_command(
        question=workflow_question,
        image=None,
        context="Result from calculation: $11,576.25",
        sub_goal="Format the result as a clear answer",
        tool_name="text_formatter",
        tool_metadata={
            "description": "Formats text output",
            "parameters": {"text": "Text to format"}
        },
        step_count=2
    )
    
    _, _, cmd2 = executor.extract_explanation_and_command(step2_command)
    print(f"Command: {cmd2}")
    print()
    
    # Example 5: Error handling
    print("-" * 60)
    print("Example 5: Error Handling")
    print("-" * 60)
    
    print("Testing with invalid tool metadata...")
    try:
        invalid_command = await executor.generate_tool_command(
            question="Test question",
            image=None,
            context="Test context",
            sub_goal="Test sub-goal",
            tool_name="invalid_tool",
            tool_metadata={},  # Empty metadata
            step_count=99
        )
        print("Command generated (may be generic)")
        print(invalid_command[:200] + "...")
    except Exception as e:
        print(f"Error handled: {str(e)}")
    print()
    
    print("=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)
    print()
    print("Note: Tool execution examples require actual tool implementations")
    print("in the 'tools/' directory. The executor can generate commands")
    print("but needs the tool classes to execute them.")


if __name__ == "__main__":
    asyncio.run(main())
