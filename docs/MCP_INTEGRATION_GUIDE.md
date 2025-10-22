# MCP Integration Guide for AgentFlow

## Overview

AgentFlow now supports **Model Context Protocol (MCP)** for dynamic tool loading. This allows you to extend AgentFlow with external tools from MCP servers without modifying the core codebase.

## What is MCP?

Model Context Protocol (MCP) is a standard protocol for connecting AI assistants to external tools and data sources. It enables:

- **Dynamic tool discovery** - Tools are discovered at runtime
- **Standardized interface** - Consistent API across different tools
- **Extensibility** - Add new capabilities without code changes
- **Security** - Fine-grained control over tool permissions

## Features

✓ **Automatic tool discovery** from MCP servers  
✓ **Multiple configuration sources** (user, workspace, custom, env)  
✓ **Selective server loading** - Load only the tools you need  
✓ **Auto-approval** - Configure which tools can run without confirmation  
✓ **Graceful fallback** - Works with or without MCP  
✓ **Tool namespacing** - Avoid conflicts between tools  

## Configuration

### Configuration Hierarchy

AgentFlow loads MCP configurations from multiple sources (in order of precedence):

1. **Environment variable** - `AGENTFLOW_MCP_CONFIG`
2. **Custom config file** - Specified via `mcp_config_path`
3. **Workspace config** - `.kiro/settings/mcp.json`
4. **User config** - `~/.kiro/settings/mcp.json`

Later configurations override earlier ones for the same server name.

### Configuration Format

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      },
      "disabled": false,
      "autoApprove": ["tool1", "tool2"]
    }
  }
}
```

### Configuration Fields

- **command**: Command to start the MCP server (e.g., `npx`, `uvx`, `python`)
- **args**: Arguments to pass to the command
- **env**: Environment variables for the server process
- **disabled**: Set to `true` to disable the server
- **autoApprove**: List of tool names that don't require confirmation
  - Use `["*"]` to auto-approve all tools from this server

### Example Configuration

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "disabled": false,
      "autoApprove": ["read_file", "list_directory"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key-here"
      },
      "disabled": false,
      "autoApprove": []
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
      },
      "disabled": false,
      "autoApprove": ["search_repositories"]
    }
  }
}
```

## Usage

### Basic Usage

```python
from agentflow.solver import construct_solver
from agentflow.models.bedrock_client import ModelType

# Create solver with MCP enabled
solver = construct_solver(
    model_type=ModelType.SONNET_4,
    enable_mcp=True,  # Enable MCP tool loading
    verbose=True
)

# Solve a problem using MCP tools
result = await solver.solve("List files in /tmp directory")
```

### Selective Server Loading

```python
# Load only specific MCP servers
solver = construct_solver(
    model_type=ModelType.SONNET_4,
    enable_mcp=True,
    mcp_servers=["filesystem", "github"]  # Only load these servers
)
```

### Custom Configuration Path

```python
# Use a custom config file
solver = construct_solver(
    model_type=ModelType.SONNET_4,
    enable_mcp=True,
    mcp_config_path="./my-mcp-config.json"
)
```

### Environment Variable Configuration

```python
import os
import json

# Set config via environment
config = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "disabled": false,
            "autoApprove": ["*"]
        }
    }
}

os.environ["AGENTFLOW_MCP_CONFIG"] = json.dumps(config)

# Create solver (will use env config)
solver = construct_solver(
    model_type=ModelType.SONNET_4,
    enable_mcp=True
)
```

### Disabling MCP

```python
# Use only built-in tools
solver = construct_solver(
    model_type=ModelType.SONNET_4,
    enable_mcp=False  # Disable MCP
)
```

## Available MCP Servers

### Official MCP Servers

1. **Filesystem** - File operations
   - `read_file` - Read file contents
   - `write_file` - Write to files
   - `list_directory` - List directory contents

2. **Brave Search** - Web search
   - `search` - Search the web

3. **GitHub** - GitHub integration
   - `search_repositories` - Search repos
   - `get_file_contents` - Get file from repo
   - `create_issue` - Create issues
   - `create_pull_request` - Create PRs

4. **AWS Knowledge Base** - Retrieval from AWS KB
   - `retrieve` - Query knowledge base

### Installing MCP Servers

Most MCP servers can be run without installation using `npx` or `uvx`:

```bash
# NPX (Node.js)
npx -y @modelcontextprotocol/server-filesystem /tmp

# UVX (Python)
uvx mcp-server-aws-kb-retrieval
```

## Tool Naming

MCP tools are namespaced to avoid conflicts:

- Format: `{server-name}.{tool-name}`
- Example: `filesystem.read_file`, `github.search_repositories`

The solver automatically handles tool resolution and routing.

## Security Considerations

### Auto-Approval

Use auto-approval carefully:

```json
{
  "autoApprove": ["read_file"]  // ✓ Safe - read-only
}
```

```json
{
  "autoApprove": ["*"]  // ⚠️ Caution - all tools
}
```

### Environment Variables

Never commit sensitive data:

```json
{
  "env": {
    "API_KEY": "your-key-here"  // ❌ Don't commit
  }
}
```

Use environment variables instead:

```json
{
  "env": {
    "API_KEY": "${BRAVE_API_KEY}"  // ✓ Reference env var
  }
}
```

## Troubleshooting

### MCP Tools Not Loading

1. **Check configuration**:
   ```bash
   cat ~/.kiro/settings/mcp.json
   cat .kiro/settings/mcp.json
   ```

2. **Check logs**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Verify server is not disabled**:
   ```json
   {
     "disabled": false  // Must be false
   }
   ```

### Tool Execution Fails

1. **Check server command is installed**:
   ```bash
   which npx
   which uvx
   ```

2. **Check environment variables are set**:
   ```bash
   echo $BRAVE_API_KEY
   ```

3. **Check auto-approval settings**:
   ```json
   {
     "autoApprove": ["tool-name"]
   }
   ```

### Simulation Mode

If MCP servers aren't available, AgentFlow falls back to simulation:

```
WARNING: Tool module not found, using simulation
```

This allows development and testing without real MCP servers.

## Advanced Usage

### Programmatic Configuration

```python
from agentflow.mcp import MCPConfig, MCPToolLoader

# Create config programmatically
config = MCPConfig()
config.servers["custom-server"] = {
    "command": "python",
    "args": ["my_mcp_server.py"],
    "disabled": False,
    "autoApprove": []
}

# Load tools
loader = MCPToolLoader(config)
tools = await loader.load_tools()
```

### Custom Tool Execution

```python
from agentflow.mcp import MCPToolLoader

# Load tools
loader = MCPToolLoader()
await loader.load_tools()

# Execute tool directly
result = await loader.execute_tool(
    "filesystem.read_file",
    path="/tmp/test.txt"
)
```

### Tool Metadata

```python
# Get metadata for all MCP tools
metadata = executor.get_mcp_tool_metadata()

for tool_name, tool_info in metadata.items():
    print(f"Tool: {tool_name}")
    print(f"Description: {tool_info['description']}")
    print(f"Parameters: {tool_info['parameters']}")
```

## Best Practices

1. **Start with simulation** - Test workflows before connecting real servers
2. **Use workspace configs** - Keep project-specific configs in `.kiro/settings/`
3. **Selective loading** - Only load servers you need
4. **Auto-approve carefully** - Only auto-approve safe, read-only tools
5. **Environment variables** - Use for sensitive data
6. **Error handling** - MCP failures won't crash the solver
7. **Logging** - Enable verbose mode for debugging

## Examples

See `examples/mcp_solver_example.py` for complete examples.

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Kiro MCP Documentation](https://docs.kiro.ai/mcp)

## Summary

MCP integration makes AgentFlow highly extensible. You can:

- Add new tools without code changes
- Use community-built MCP servers
- Build custom MCP servers for your needs
- Control tool access and permissions
- Mix built-in and MCP tools seamlessly

The system is designed to be fault-tolerant and developer-friendly, working with or without MCP servers available.
