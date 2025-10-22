# MCP Integration Summary

## Overview

Successfully integrated **Model Context Protocol (MCP)** support into AgentFlow, enabling dynamic tool loading from external MCP servers.

## What Was Added

### Core MCP Module (`src/agentflow/mcp/`)

1. **`mcp_config.py`** - Configuration management
   - Loads configs from multiple sources (user, workspace, custom, env)
   - Merges configurations with precedence rules
   - Handles server enable/disable and auto-approval settings

2. **`mcp_tool_loader.py`** - Dynamic tool loading
   - Discovers tools from MCP servers
   - Creates executable tool wrappers
   - Manages tool metadata and namespacing
   - Provides simulation fallback

3. **`__init__.py`** - Module exports

### Executor Integration

Modified `src/agentflow/models/executor.py`:

- Added MCP support initialization
- Added `load_mcp_tools()` method
- Added `get_mcp_tool_metadata()` method
- Added `_execute_mcp_tool()` method for MCP tool execution
- Integrated MCP tool routing in `execute_tool_command()`

### Solver Integration

Modified `src/agentflow/solver.py`:

- Added MCP configuration parameters to `construct_solver()`
- Automatic MCP tool loading on solver construction
- Merges MCP tools with built-in tools
- Passes MCP metadata to planner

## Configuration System

### Configuration Hierarchy (Precedence Order)

1. Environment variable: `AGENTFLOW_MCP_CONFIG`
2. Custom config file: via `mcp_config_path` parameter
3. Workspace config: `.kiro/settings/mcp.json`
4. User config: `~/.kiro/settings/mcp.json`

### Configuration Format

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {"KEY": "value"},
      "disabled": false,
      "autoApprove": ["tool1", "tool2"]
    }
  }
}
```

## Features

✓ **Dynamic tool discovery** - Tools loaded at runtime from MCP servers  
✓ **Multiple config sources** - User, workspace, custom, environment  
✓ **Selective loading** - Load only specific servers  
✓ **Auto-approval** - Configure which tools run without confirmation  
✓ **Tool namespacing** - Format: `server.tool` (e.g., `filesystem.read_file`)  
✓ **Graceful fallback** - Simulation mode when servers unavailable  
✓ **Fault tolerance** - MCP failures don't crash the solver  
✓ **Metadata integration** - MCP tools appear in planner's toolbox  

## Usage Examples

### Basic Usage

```python
from agentflow.solver import construct_solver

solver = construct_solver(
    enable_mcp=True,  # Enable MCP
    mcp_servers=["filesystem", "github"]  # Load specific servers
)

result = await solver.solve("List files in /tmp")
```

### Custom Configuration

```python
solver = construct_solver(
    enable_mcp=True,
    mcp_config_path="./my-config.json"  # Custom config
)
```

### Environment Configuration

```python
import os
import json

os.environ["AGENTFLOW_MCP_CONFIG"] = json.dumps({
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "disabled": False,
            "autoApprove": ["*"]
        }
    }
})

solver = construct_solver(enable_mcp=True)
```

## Supported MCP Servers

### Pre-configured Servers

1. **Filesystem** - File operations
   - `read_file`, `write_file`, `list_directory`

2. **Brave Search** - Web search
   - `search`

3. **GitHub** - GitHub integration
   - `search_repositories`, `get_file_contents`

4. **AWS Knowledge Base** - Retrieval
   - `retrieve`

### Adding Custom Servers

Simply add to configuration:

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["my_server.py"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Files Created

### Core Implementation
- `src/agentflow/mcp/__init__.py`
- `src/agentflow/mcp/mcp_config.py`
- `src/agentflow/mcp/mcp_tool_loader.py`

### Documentation
- `docs/MCP_INTEGRATION_GUIDE.md` - Comprehensive guide
- `MCP_INTEGRATION_SUMMARY.md` - This file

### Examples
- `examples/mcp_config_example.json` - Example configuration
- `examples/mcp_solver_example.py` - Usage examples

### Tools
- `scripts/setup_mcp.py` - Setup and validation script

## Setup Instructions

### 1. Create Configuration

```bash
# User-level config
python scripts/setup_mcp.py --user

# Workspace-level config
python scripts/setup_mcp.py --workspace

# Custom location
python scripts/setup_mcp.py --custom ./my-config.json
```

### 2. Edit Configuration

Edit the created config file to:
- Add API keys for services (Brave, GitHub, etc.)
- Enable/disable servers
- Configure auto-approval

### 3. Check Dependencies

```bash
python scripts/setup_mcp.py --check-deps
```

Ensure you have:
- `npx` (Node.js) for NPM-based servers
- `uvx` (uv) for Python-based servers

### 4. Run Examples

```bash
python examples/mcp_solver_example.py
```

## Architecture

```
AgentFlow Solver
├── Planner (generates plans)
├── Executor (executes tools)
│   ├── Built-in Tools (calculator, web_search, etc.)
│   └── MCP Tools (via MCPToolLoader)
│       ├── MCPConfig (configuration management)
│       └── MCPTool instances (executable tools)
└── Memory (tracks execution)
```

## Tool Execution Flow

1. **Solver** receives question
2. **Planner** generates plan with tool selection
3. **Executor** checks if tool is MCP tool
4. If MCP:
   - Routes to `_execute_mcp_tool()`
   - Extracts parameters from command
   - Calls `MCPToolLoader.execute_tool()`
   - Returns result
5. If built-in:
   - Routes to standard execution
   - Falls back to simulation if not found

## Security Features

### Auto-Approval

Control which tools can run automatically:

```json
{
  "autoApprove": ["read_file"]  // Only these tools
}
```

```json
{
  "autoApprove": ["*"]  // All tools (use carefully)
}
```

### Environment Variables

Sensitive data via environment:

```json
{
  "env": {
    "API_KEY": "${MY_API_KEY}"  // Reference env var
  }
}
```

### Server Disable

Quickly disable servers:

```json
{
  "disabled": true  // Server won't load
}
```

## Benefits

1. **Extensibility** - Add tools without code changes
2. **Flexibility** - Use community MCP servers
3. **Security** - Fine-grained control
4. **Maintainability** - Separate tool logic from core
5. **Compatibility** - Standard MCP protocol
6. **Developer-friendly** - Works with or without MCP

## Testing

### Validate Configuration

```bash
python scripts/setup_mcp.py --validate ~/.kiro/settings/mcp.json
```

### Run Examples

```bash
# Basic example
python examples/mcp_solver_example.py

# Test executor
python test_executor_fix.py
```

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Tools Not Loading

1. Check config exists and is valid
2. Verify server is not disabled
3. Check command is installed (`npx`, `uvx`)
4. Enable debug logging

### Execution Fails

1. Check environment variables are set
2. Verify auto-approval settings
3. Check tool parameters are correct
4. Review logs for errors

### Simulation Mode

If you see "using simulation" warnings:
- MCP servers aren't available
- This is expected for development
- Install servers for production use

## Next Steps

### For Development

1. Use simulation mode (no setup needed)
2. Test workflows with simulated tools
3. Add real MCP servers when ready

### For Production

1. Install required MCP servers
2. Configure with real API keys
3. Set appropriate auto-approval
4. Enable CloudWatch logging
5. Monitor tool execution

### Custom Tools

1. Build custom MCP server
2. Add to configuration
3. Tools automatically available

## References

- **MCP Specification**: https://modelcontextprotocol.io
- **Official Servers**: https://github.com/modelcontextprotocol/servers
- **AgentFlow Docs**: `docs/MCP_INTEGRATION_GUIDE.md`
- **Setup Script**: `scripts/setup_mcp.py`
- **Examples**: `examples/mcp_solver_example.py`

## Summary

MCP integration makes AgentFlow highly extensible and configurable. You can now:

- ✓ Add external tools dynamically
- ✓ Use community MCP servers
- ✓ Build custom tools
- ✓ Control tool permissions
- ✓ Mix built-in and MCP tools
- ✓ Configure per-user or per-workspace
- ✓ Work with or without MCP servers

The system is production-ready, fault-tolerant, and developer-friendly!
