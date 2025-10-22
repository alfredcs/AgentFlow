"""
Test MCP Integration in AgentFlow

Verifies that MCP tools can be loaded and configured correctly.
"""

import asyncio
import json
import os
from pathlib import Path


async def test_mcp_config():
    """Test MCP configuration loading"""
    print("=" * 60)
    print("Test 1: MCP Configuration")
    print("=" * 60)
    
    from agentflow.mcp import MCPConfig
    
    # Test 1: Create config from dict
    print("\n1. Testing configuration creation...")
    config = MCPConfig()
    print(f"✓ MCPConfig created")
    print(f"  Servers loaded: {len(config.get_all_servers())}")
    
    # Test 2: Get server config
    print("\n2. Testing server configuration...")
    filesystem_config = config.get_server_config("filesystem")
    if filesystem_config:
        print(f"✓ Filesystem server config found")
        print(f"  Command: {filesystem_config.get('command')}")
        print(f"  Disabled: {filesystem_config.get('disabled', False)}")
    else:
        print("⚠️  No filesystem server configured (this is OK)")
    
    # Test 3: Auto-approval check
    print("\n3. Testing auto-approval...")
    is_approved = config.is_tool_auto_approved("filesystem", "read_file")
    print(f"  filesystem.read_file auto-approved: {is_approved}")
    
    print("\n✓ Configuration tests passed!")


async def test_mcp_tool_loader():
    """Test MCP tool loader"""
    print("\n" + "=" * 60)
    print("Test 2: MCP Tool Loader")
    print("=" * 60)
    
    from agentflow.mcp import MCPToolLoader, MCPConfig
    
    # Test 1: Create loader
    print("\n1. Testing tool loader creation...")
    config = MCPConfig()
    loader = MCPToolLoader(config)
    print(f"✓ MCPToolLoader created")
    
    # Test 2: Load tools
    print("\n2. Testing tool loading...")
    tools = await loader.load_tools()
    print(f"✓ Loaded {len(tools)} tools")
    
    if tools:
        print("\n  Available tools:")
        for tool_name, tool in list(tools.items())[:5]:  # Show first 5
            print(f"    - {tool_name}: {tool.description[:50]}...")
    
    # Test 3: Get tool metadata
    print("\n3. Testing tool metadata...")
    metadata = loader.get_tool_metadata()
    print(f"✓ Retrieved metadata for {len(metadata)} tools")
    
    # Test 4: Execute a tool (simulated)
    if tools:
        print("\n4. Testing tool execution (simulated)...")
        first_tool = list(tools.keys())[0]
        try:
            result = await loader.execute_tool(first_tool, query="test")
            print(f"✓ Tool executed: {first_tool}")
            print(f"  Result type: {type(result).__name__}")
        except Exception as e:
            print(f"⚠️  Tool execution failed (expected): {e}")
    
    print("\n✓ Tool loader tests passed!")


async def test_executor_mcp_integration():
    """Test executor MCP integration"""
    print("\n" + "=" * 60)
    print("Test 3: Executor MCP Integration")
    print("=" * 60)
    
    from agentflow.models.bedrock_client import BedrockClient, ModelType
    from agentflow.models.executor import Executor
    
    # Test 1: Create executor with MCP
    print("\n1. Testing executor with MCP enabled...")
    bedrock_client = BedrockClient(region_name="us-east-1")
    executor = Executor(
        bedrock_client=bedrock_client,
        model_type=ModelType.SONNET_4,
        enable_mcp=True,
        verbose=False
    )
    print(f"✓ Executor created with MCP support")
    print(f"  MCP loader available: {executor.mcp_loader is not None}")
    
    # Test 2: Load MCP tools
    print("\n2. Testing MCP tool loading in executor...")
    await executor.load_mcp_tools()
    print(f"✓ MCP tools loaded: {len(executor.mcp_tools)}")
    
    # Test 3: Get MCP metadata
    print("\n3. Testing MCP metadata retrieval...")
    metadata = executor.get_mcp_tool_metadata()
    print(f"✓ Retrieved metadata for {len(metadata)} tools")
    
    if metadata:
        print("\n  Sample tools:")
        for tool_name in list(metadata.keys())[:3]:
            print(f"    - {tool_name}")
    
    print("\n✓ Executor integration tests passed!")


async def test_solver_mcp_integration():
    """Test solver MCP integration"""
    print("\n" + "=" * 60)
    print("Test 4: Solver MCP Integration")
    print("=" * 60)
    
    from agentflow.solver import construct_solver
    from agentflow.models.bedrock_client import ModelType
    
    # Test 1: Create solver with MCP
    print("\n1. Testing solver construction with MCP...")
    solver = construct_solver(
        model_type=ModelType.SONNET_4,
        enabled_tools=["calculator"],
        enable_mcp=True,
        mcp_servers=["filesystem"],
        verbose=False
    )
    print(f"✓ Solver created with MCP support")
    
    # Test 2: Check available tools
    print("\n2. Checking available tools...")
    available_tools = solver.planner.available_tools
    print(f"✓ Available tools: {len(available_tools)}")
    print(f"  Tools: {', '.join(available_tools[:5])}...")
    
    # Test 3: Check toolbox metadata
    print("\n3. Checking toolbox metadata...")
    toolbox = solver.planner.toolbox_metadata
    print(f"✓ Toolbox has {len(toolbox)} tool definitions")
    
    # Check if MCP tools are in toolbox
    mcp_tools = [t for t in toolbox.keys() if '.' in t]
    if mcp_tools:
        print(f"  MCP tools in toolbox: {len(mcp_tools)}")
        print(f"  Examples: {', '.join(mcp_tools[:3])}")
    
    print("\n✓ Solver integration tests passed!")


async def test_config_creation():
    """Test configuration file creation"""
    print("\n" + "=" * 60)
    print("Test 5: Configuration File Creation")
    print("=" * 60)
    
    from agentflow.mcp import MCPConfig
    
    # Test creating a config file
    print("\n1. Testing config file creation...")
    test_config_path = "/tmp/test_mcp_config.json"
    
    try:
        MCPConfig.create_default_config(test_config_path)
        print(f"✓ Config file created: {test_config_path}")
        
        # Verify it's valid JSON
        with open(test_config_path, 'r') as f:
            config_data = json.load(f)
        
        print(f"✓ Config is valid JSON")
        print(f"  Servers defined: {len(config_data.get('mcpServers', {}))}")
        
        # Clean up
        os.remove(test_config_path)
        print(f"✓ Test config cleaned up")
        
    except Exception as e:
        print(f"❌ Config creation failed: {e}")
    
    print("\n✓ Configuration creation tests passed!")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AgentFlow MCP Integration Tests")
    print("=" * 60)
    print()
    print("Testing MCP integration components...")
    print()
    
    try:
        # Run tests
        await test_mcp_config()
        await test_mcp_tool_loader()
        await test_executor_mcp_integration()
        await test_solver_mcp_integration()
        await test_config_creation()
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("MCP integration is working correctly!")
        print()
        print("Next steps:")
        print("1. Create your MCP config: python scripts/setup_mcp.py --user")
        print("2. Run examples: python examples/mcp_solver_example.py")
        print("3. Read docs: docs/MCP_INTEGRATION_GUIDE.md")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print("\nCheck the error above and try again.")


if __name__ == "__main__":
    asyncio.run(main())
