#!/usr/bin/env python3
"""
Setup script for MCP configuration in AgentFlow

Creates default MCP configuration files and validates setup.
"""

import os
import json
import sys
from pathlib import Path


def create_default_config(config_path: str, force: bool = False) -> bool:
    """
    Create default MCP configuration
    
    Args:
        config_path: Path to create config file
        force: Overwrite existing file
        
    Returns:
        True if created, False if skipped
    """
    config_file = Path(config_path)
    
    if config_file.exists() and not force:
        print(f"⚠️  Config already exists: {config_path}")
        print("   Use --force to overwrite")
        return False
    
    default_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", str(Path.home())],
                "disabled": False,
                "autoApprove": ["read_file", "list_directory"]
            },
            "brave-search": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {
                    "BRAVE_API_KEY": "<your-api-key-here>"
                },
                "disabled": True,
                "autoApprove": []
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token-here>"
                },
                "disabled": True,
                "autoApprove": ["search_repositories"]
            },
            "aws-kb-retrieval": {
                "command": "uvx",
                "args": ["mcp-server-aws-kb-retrieval"],
                "env": {
                    "AWS_REGION": "us-east-1",
                    "KB_ID": "<your-knowledge-base-id>"
                },
                "disabled": True,
                "autoApprove": []
            }
        }
    }
    
    # Create directory if needed
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write config
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"✓ Created MCP config: {config_path}")
    return True


def validate_config(config_path: str) -> bool:
    """
    Validate MCP configuration
    
    Args:
        config_path: Path to config file
        
    Returns:
        True if valid, False otherwise
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"❌ Config not found: {config_path}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if "mcpServers" not in config:
            print(f"❌ Invalid config: missing 'mcpServers' key")
            return False
        
        servers = config["mcpServers"]
        print(f"✓ Valid config with {len(servers)} servers:")
        
        for server_name, server_config in servers.items():
            status = "disabled" if server_config.get("disabled", False) else "enabled"
            auto_approve = server_config.get("autoApprove", [])
            print(f"  - {server_name}: {status}")
            if auto_approve:
                print(f"    Auto-approve: {', '.join(auto_approve)}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating config: {e}")
        return False


def check_dependencies() -> None:
    """Check if required dependencies are installed"""
    print("\nChecking dependencies...")
    
    # Check npx
    npx_available = os.system("which npx > /dev/null 2>&1") == 0
    if npx_available:
        print("✓ npx is installed (Node.js MCP servers)")
    else:
        print("⚠️  npx not found - install Node.js for NPM-based MCP servers")
        print("   https://nodejs.org/")
    
    # Check uvx
    uvx_available = os.system("which uvx > /dev/null 2>&1") == 0
    if uvx_available:
        print("✓ uvx is installed (Python MCP servers)")
    else:
        print("⚠️  uvx not found - install uv for Python-based MCP servers")
        print("   https://docs.astral.sh/uv/getting-started/installation/")


def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Setup MCP configuration for AgentFlow"
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Create user-level config (~/.kiro/settings/mcp.json)"
    )
    parser.add_argument(
        "--workspace",
        action="store_true",
        help="Create workspace-level config (.kiro/settings/mcp.json)"
    )
    parser.add_argument(
        "--custom",
        type=str,
        help="Create config at custom path"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config"
    )
    parser.add_argument(
        "--validate",
        type=str,
        help="Validate existing config file"
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if MCP dependencies are installed"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AgentFlow MCP Setup")
    print("=" * 60)
    
    # Check dependencies
    if args.check_deps:
        check_dependencies()
        return
    
    # Validate config
    if args.validate:
        print(f"\nValidating config: {args.validate}")
        validate_config(args.validate)
        return
    
    # Create configs
    created = False
    
    if args.user:
        user_config = Path.home() / ".kiro" / "settings" / "mcp.json"
        print(f"\nCreating user-level config...")
        created |= create_default_config(str(user_config), args.force)
    
    if args.workspace:
        workspace_config = Path.cwd() / ".kiro" / "settings" / "mcp.json"
        print(f"\nCreating workspace-level config...")
        created |= create_default_config(str(workspace_config), args.force)
    
    if args.custom:
        print(f"\nCreating custom config...")
        created |= create_default_config(args.custom, args.force)
    
    if not any([args.user, args.workspace, args.custom, args.validate]):
        print("\nNo action specified. Use --help for options.")
        print("\nQuick start:")
        print("  python scripts/setup_mcp.py --user        # User-level config")
        print("  python scripts/setup_mcp.py --workspace   # Workspace config")
        print("  python scripts/setup_mcp.py --check-deps  # Check dependencies")
        return
    
    if created:
        print("\n" + "=" * 60)
        print("✓ Setup complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Edit the config file to add your API keys")
        print("2. Enable servers by setting 'disabled: false'")
        print("3. Run: python examples/mcp_solver_example.py")
        print("\nDocumentation: docs/MCP_INTEGRATION_GUIDE.md")
    
    # Check dependencies
    check_dependencies()


if __name__ == "__main__":
    main()
