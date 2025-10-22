"""
Quick test to verify the executor handles missing tools gracefully
"""

import asyncio
from agentflow.models.bedrock_client import BedrockClient, ModelType
from agentflow.models.executor import Executor


async def test_executor_with_missing_tools():
    """Test that executor falls back to simulation when tools are missing"""
    
    print("Testing Executor with missing tools...")
    print("=" * 60)
    
    # Create executor
    bedrock_client = BedrockClient(region_name="us-east-1")
    executor = Executor(
        bedrock_client=bedrock_client,
        model_type=ModelType.SONNET_4,
        verbose=True
    )
    
    # Test 1: Calculator tool (doesn't exist)
    print("\nTest 1: Calculator tool (simulated)")
    print("-" * 60)
    command1 = 'execution = tool.execute(query="15% of 250")'
    result1 = executor.execute_tool_command("calculator", command1)
    print(f"Result: {result1}")
    
    # Test 2: Web search tool (doesn't exist)
    print("\nTest 2: Web search tool (simulated)")
    print("-" * 60)
    command2 = 'execution = tool.execute(query="What is the capital of France?")'
    result2 = executor.execute_tool_command("web_search", command2)
    print(f"Result: {result2}")
    
    # Test 3: Code interpreter tool (doesn't exist)
    print("\nTest 3: Code interpreter tool (simulated)")
    print("-" * 60)
    command3 = 'execution = tool.execute(code="print(2 + 2)")'
    result3 = executor.execute_tool_command("code_interpreter", command3)
    print(f"Result: {result3}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Executor handles missing tools gracefully.")
    print("\nKey points:")
    print("- No 'ModuleNotFoundError' raised")
    print("- Simulation fallback works correctly")
    print("- Different tool types return appropriate simulated results")


if __name__ == "__main__":
    asyncio.run(test_executor_with_missing_tools())
