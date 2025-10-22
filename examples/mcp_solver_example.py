"""
Example: Using AgentFlow Solver with MCP Tools

Demonstrates how to integrate external tools via Model Context Protocol (MCP).
"""

import asyncio
import os
from solver_bedrock import construct_solver
from agentflow.models.bedrock_client import ModelType


async def main():
    """Demonstrate solver with MCP tools"""
    
    print("=" * 70)
    print("AgentFlow Solver with MCP Tools Example")
    print("=" * 70)
    print()
    
    # Example 1: Using default MCP configuration
    print("Example 1: Solver with MCP Tools (Default Config)")
    print("-" * 50)
    
    solver = construct_solver(
        model_type=ModelType.SONNET_4_5,
        enabled_tools=["calculator"],  # Built-in tools
        output_types="direct",
        max_steps=5,
        verbose=True,
        temperature=0.3,
        enable_mcp=True,  # Enable MCP tool loading
        mcp_servers=["filesystem"]  # Load specific MCP servers
    )
    
    # The solver now has access to both built-in and MCP tools
    print("\nAvailable tools:")
    print("- Built-in: calculator, web_search, code_interpreter")
    print("- MCP: filesystem.read_file, filesystem.write_file, filesystem.list_directory")
    print()
    
    question1 = "List the files in the /tmp directory"
    print(f"Question: {question1}")
    print()
    
    result1 = await solver.solve(question1)
    
    print("\n" + "=" * 50)
    print("Results:")
    print(f"- Answer: {result1.get('direct_output', 'N/A')}")
    
    # Example 2: Using custom MCP configuration
    print("\n\n" + "=" * 70)
    print("Example 2: Solver with Custom MCP Config")
    print("-" * 50)
    
    # Point to custom config file
    custom_config_path = "examples/mcp_config_example.json"
    
    solver2 = construct_solver(
        model_type=ModelType.SONNET_4_5,
        enabled_tools=["web_search"],
        output_types="final,direct",
        max_steps=3,
        verbose=True,
        enable_mcp=True,
        mcp_config_path=custom_config_path,
        mcp_servers=["filesystem", "github"]  # Load multiple servers
    )
    
    question2 = "Search for Python repositories on GitHub related to machine learning"
    print(f"Question: {question2}")
    print()
    
    result2 = await solver2.solve(question2)
    
    print("\n" + "=" * 50)
    print("Results:")
    print(f"- Steps: {result2.get('step_count', 0)}")
    print(f"- Time: {result2.get('execution_time', 0)}s")
    
    # Example 3: Programmatic MCP configuration
    print("\n\n" + "=" * 70)
    print("Example 3: Programmatic MCP Configuration")
    print("-" * 50)
    
    # Set MCP config via environment variable
    mcp_config_json = '''
    {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "disabled": false,
                "autoApprove": ["*"]
            }
        }
    }
    '''
    
    os.environ["AGENTFLOW_MCP_CONFIG"] = mcp_config_json
    
    solver3 = construct_solver(
        model_type=ModelType.HAIKU_4_5,  # Fast model
        output_types="direct",
        enable_mcp=True,
        verbose=True
    )
    
    question3 = "What files are in the current directory?"
    print(f"Question: {question3}")
    print()
    
    result3 = await solver3.solve(question3)
    
    print("\n" + "=" * 50)
    print(f"Answer: {result3.get('direct_output', 'N/A')}")
    
    # Example 4: Disabling MCP
    print("\n\n" + "=" * 70)
    print("Example 4: Solver without MCP (Built-in Tools Only)")
    print("-" * 50)
    
    solver4 = construct_solver(
        model_type=ModelType.SONNET_4_5,
        enabled_tools=["calculator"],
        output_types="direct",
        enable_mcp=False,  # Disable MCP
        verbose=True
    )
    
    question4 = "What is 25% of 400?"
    print(f"Question: {question4}")
    print()
    
    result4 = await solver4.solve(question4)
    
    print("\n" + "=" * 50)
    print(f"Answer: {result4.get('direct_output', 'N/A')}")
    
    print("\n\n" + "=" * 70)
    print("✓ All examples completed!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("- MCP tool integration with AgentFlow")
    print("- Multiple configuration methods (file, env, default)")
    print("- Selective MCP server loading")
    print("- Mixing built-in and MCP tools")
    print("- Auto-approval configuration")
    print("- Graceful fallback when MCP unavailable")
    print()
    print("Configuration Locations:")
    print("1. User-level: ~/.kiro/settings/mcp.json")
    print("2. Workspace-level: .kiro/settings/mcp.json")
    print("3. Custom path: via mcp_config_path parameter")
    print("4. Environment: AGENTFLOW_MCP_CONFIG variable")


if __name__ == "__main__":
    asyncio.run(main())
