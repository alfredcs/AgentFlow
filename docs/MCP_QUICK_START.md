# MCP Quick Start Guide

## 🚀 Quick Setup (30 seconds)

### 1. Create Configuration

```bash
python scripts/setup_mcp.py --user
```

### 2. Use in Code

```python
from agentflow.solver import construct_solver

solver = construct_solver(enable_mcp=True)
result = await solver.solve("Your question here")
```

That's it! 🎉

---

## 📋 Configuration Locations

| Location | Path | Use Case |
|----------|------|----------|
| User | `~/.kiro/settings/mcp.json` | Personal settings |
| Workspace | `.kiro/settings/mcp.json` | Project-specific |
| Custom | Any path | Special configs |
| Environment | `AGENTFLOW_MCP_CONFIG` | Dynamic configs |

---

## 🛠️ Common Commands

```bash
# Setup
python scripts/setup_mcp.py --user              # Create user config
python scripts/setup_mcp.py --workspace         # Create workspace config
python scripts/setup_mcp.py --check-deps        # Check dependencies

# Validate
python scripts/setup_mcp.py --validate ~/.kiro/settings/mcp.json

# Run examples
python examples/mcp_solver_example.py
```

---

## 📝 Configuration Template

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "disabled": false,
      "autoApprove": ["read_file", "list_directory"]
    }
  }
}
```

---

## 💻 Code Examples

### Basic Usage

```python
solver = construct_solver(enable_mcp=True)
```

### Selective Servers

```python
solver = construct_solver(
    enable_mcp=True,
    mcp_servers=["filesystem", "github"]
)
```

### Custom Config

```python
solver = construct_solver(
    enable_mcp=True,
    mcp_config_path="./my-config.json"
)
```

### Disable MCP

```python
solver = construct_solver(enable_mcp=False)
```

---

## 🔧 Available Servers

| Server | Tools | Setup |
|--------|-------|-------|
| **filesystem** | read_file, write_file, list_directory | `npx -y @modelcontextprotocol/server-filesystem` |
| **brave-search** | search | Requires API key |
| **github** | search_repositories, get_file_contents | Requires token |
| **aws-kb** | retrieve | Requires AWS credentials |

---

## 🎯 Tool Naming

MCP tools use namespaced names:

- Format: `{server}.{tool}`
- Examples:
  - `filesystem.read_file`
  - `github.search_repositories`
  - `brave-search.search`

---

## ⚙️ Configuration Options

| Field | Description | Example |
|-------|-------------|---------|
| `command` | Command to run | `"npx"`, `"uvx"`, `"python"` |
| `args` | Command arguments | `["-y", "package-name"]` |
| `env` | Environment variables | `{"API_KEY": "value"}` |
| `disabled` | Enable/disable server | `true` or `false` |
| `autoApprove` | Auto-approve tools | `["tool1"]` or `["*"]` |

---

## 🔒 Security Tips

✓ **DO**: Use auto-approve for read-only tools  
✓ **DO**: Store API keys in environment variables  
✓ **DO**: Disable unused servers  

❌ **DON'T**: Commit API keys to git  
❌ **DON'T**: Auto-approve all tools (`["*"]`) in production  
❌ **DON'T**: Enable untrusted servers  

---

## 🐛 Troubleshooting

### Tools not loading?

```bash
# Check config
cat ~/.kiro/settings/mcp.json

# Validate config
python scripts/setup_mcp.py --validate ~/.kiro/settings/mcp.json

# Check dependencies
python scripts/setup_mcp.py --check-deps
```

### Execution fails?

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Simulation mode?

This is normal for development. Install MCP servers for production:

```bash
# Check if npx is installed
which npx

# Check if uvx is installed
which uvx
```

---

## 📚 Documentation

- **Full Guide**: `docs/MCP_INTEGRATION_GUIDE.md`
- **Summary**: `MCP_INTEGRATION_SUMMARY.md`
- **Examples**: `examples/mcp_solver_example.py`
- **Setup Script**: `scripts/setup_mcp.py`

---

## 🎓 Learning Path

1. **Start**: Run `python scripts/setup_mcp.py --user`
2. **Learn**: Read `docs/MCP_INTEGRATION_GUIDE.md`
3. **Practice**: Run `python examples/mcp_solver_example.py`
4. **Build**: Create your own MCP tools
5. **Deploy**: Configure for production

---

## 💡 Pro Tips

1. Start with simulation mode (no setup needed)
2. Use workspace configs for project-specific tools
3. Keep user config for personal tools
4. Use environment variables for secrets
5. Enable verbose mode for debugging
6. Check logs when things go wrong

---

## 🚦 Status Indicators

| Message | Meaning | Action |
|---------|---------|--------|
| `MCP tool support enabled` | ✅ Working | None |
| `using simulation` | ⚠️ Fallback mode | Install servers |
| `Tool module not found` | ⚠️ Missing tool | Check config |
| `Failed to load MCP tools` | ❌ Error | Check logs |

---

## 📞 Getting Help

1. Check documentation: `docs/MCP_INTEGRATION_GUIDE.md`
2. Run validation: `python scripts/setup_mcp.py --validate`
3. Enable debug logging
4. Check examples: `examples/mcp_solver_example.py`

---

## ✨ Quick Wins

### 5-Minute Setup

```bash
# 1. Create config
python scripts/setup_mcp.py --user

# 2. Run example
python examples/mcp_solver_example.py
```

### 10-Minute Custom Tool

```python
# 1. Add to config
{
  "mcpServers": {
    "my-tool": {
      "command": "python",
      "args": ["my_server.py"],
      "disabled": false
    }
  }
}

# 2. Use in code
solver = construct_solver(enable_mcp=True)
result = await solver.solve("Use my-tool to...")
```

---

**Ready to go!** 🚀

For more details, see `docs/MCP_INTEGRATION_GUIDE.md`
