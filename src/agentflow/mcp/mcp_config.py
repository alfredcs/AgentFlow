"""
MCP Configuration Management

Handles loading and parsing MCP server configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)


class MCPConfig:
    """
    Manages MCP server configurations
    
    Loads configurations from:
    1. Workspace level: .kiro/settings/mcp.json
    2. User level: ~/.kiro/settings/mcp.json
    3. Environment variables
    """
    
    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize MCP configuration
        
        Args:
            workspace_dir: Workspace directory path
            config_path: Custom config file path (overrides defaults)
        """
        self.workspace_dir = workspace_dir or os.getcwd()
        self.config_path = config_path
        self.servers: Dict[str, Dict[str, Any]] = {}
        
        self._load_configurations()
    
    def _load_configurations(self) -> None:
        """Load MCP configurations from multiple sources"""
        configs = []
        
        # 1. Load user-level config
        user_config_path = Path.home() / ".kiro" / "settings" / "mcp.json"
        if user_config_path.exists():
            configs.append(self._load_config_file(user_config_path))
            logger.info(f"Loaded user-level MCP config: {user_config_path}")
        
        # 2. Load workspace-level config
        workspace_config_path = Path(self.workspace_dir) / ".kiro" / "settings" / "mcp.json"
        if workspace_config_path.exists():
            configs.append(self._load_config_file(workspace_config_path))
            logger.info(f"Loaded workspace-level MCP config: {workspace_config_path}")
        
        # 3. Load custom config if specified
        if self.config_path:
            custom_path = Path(self.config_path)
            if custom_path.exists():
                configs.append(self._load_config_file(custom_path))
                logger.info(f"Loaded custom MCP config: {custom_path}")
        
        # 4. Load from environment variable
        env_config = os.environ.get("AGENTFLOW_MCP_CONFIG")
        if env_config:
            try:
                configs.append(json.loads(env_config))
                logger.info("Loaded MCP config from environment variable")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP config from environment: {e}")
        
        # Merge configurations (workspace takes precedence)
        self._merge_configs(configs)
    
    def _load_config_file(self, path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            return {}
    
    def _merge_configs(self, configs: List[Dict[str, Any]]) -> None:
        """
        Merge multiple configurations
        
        Later configs override earlier ones for same server names.
        """
        for config in configs:
            mcp_servers = config.get("mcpServers", {})
            for server_name, server_config in mcp_servers.items():
                # Skip disabled servers
                if server_config.get("disabled", False):
                    logger.info(f"Skipping disabled MCP server: {server_name}")
                    continue
                
                self.servers[server_name] = server_config
                logger.debug(f"Registered MCP server: {server_name}")
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server"""
        return self.servers.get(server_name)
    
    def get_all_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all server configurations"""
        return self.servers
    
    def is_tool_auto_approved(self, server_name: str, tool_name: str) -> bool:
        """Check if a tool is auto-approved"""
        server_config = self.get_server_config(server_name)
        if not server_config:
            return False
        
        auto_approve = server_config.get("autoApprove", [])
        return tool_name in auto_approve or "*" in auto_approve
    
    def get_enabled_tools(self) -> List[str]:
        """Get list of all enabled tool names across all servers"""
        tools = []
        for server_name, server_config in self.servers.items():
            # Extract tool names from server config if available
            # This is a placeholder - actual implementation depends on MCP protocol
            tools.append(f"{server_name}.*")
        return tools
    
    @classmethod
    def create_default_config(cls, output_path: str) -> None:
        """
        Create a default MCP configuration file
        
        Args:
            output_path: Path to save the configuration
        """
        default_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "disabled": False,
                    "autoApprove": ["read_file", "list_directory"]
                },
                "brave-search": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "env": {
                        "BRAVE_API_KEY": "<your-api-key>"
                    },
                    "disabled": True,
                    "autoApprove": []
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
                    },
                    "disabled": True,
                    "autoApprove": []
                }
            }
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default MCP config at: {output_path}")
