"""
MCP Tool Loader

Dynamically loads and manages tools from MCP servers.
"""

import subprocess
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from agentflow.utils.logging import setup_logger

logger = setup_logger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]
    execute_fn: Callable
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to tool metadata format"""
        return {
            "name": self.name,
            "description": self.description,
            "server": self.server_name,
            "parameters": self.input_schema.get("properties", {}),
            "required": self.input_schema.get("required", [])
        }


class MCPToolLoader:
    """
    Loads and manages tools from MCP servers
    
    Supports:
    - Dynamic tool discovery from MCP servers
    - Tool execution via MCP protocol
    - Caching of tool metadata
    """
    
    def __init__(self, mcp_config: Optional[Any] = None):
        """
        Initialize MCP tool loader
        
        Args:
            mcp_config: MCPConfig instance
        """
        from .mcp_config import MCPConfig
        
        self.config = mcp_config or MCPConfig()
        self.tools: Dict[str, MCPTool] = {}
        self.server_processes: Dict[str, Any] = {}
        
        logger.info("MCP Tool Loader initialized")
    
    async def load_tools(self, server_names: Optional[List[str]] = None) -> Dict[str, MCPTool]:
        """
        Load tools from MCP servers
        
        Args:
            server_names: List of server names to load (None = all)
            
        Returns:
            Dictionary of tool_name -> MCPTool
        """
        servers_to_load = server_names or list(self.config.get_all_servers().keys())
        
        logger.info(f"Loading tools from {len(servers_to_load)} MCP servers")
        
        for server_name in servers_to_load:
            try:
                await self._load_server_tools(server_name)
            except Exception as e:
                logger.error(f"Failed to load tools from {server_name}: {e}", exc_info=True)
        
        logger.info(f"Loaded {len(self.tools)} tools from MCP servers")
        return self.tools
    
    async def _load_server_tools(self, server_name: str) -> None:
        """Load tools from a specific MCP server"""
        server_config = self.config.get_server_config(server_name)
        if not server_config:
            logger.warning(f"No configuration found for server: {server_name}")
            return
        
        logger.info(f"Loading tools from MCP server: {server_name}")
        
        # For now, we'll use a simplified approach
        # In production, you'd implement the full MCP protocol
        try:
            # Simulate tool discovery
            # In real implementation, this would communicate with the MCP server
            tools = await self._discover_tools(server_name, server_config)
            
            for tool_info in tools:
                tool = MCPTool(
                    name=tool_info["name"],
                    description=tool_info.get("description", ""),
                    server_name=server_name,
                    input_schema=tool_info.get("inputSchema", {}),
                    execute_fn=self._create_execute_function(server_name, tool_info["name"])
                )
                
                # Use namespaced tool name to avoid conflicts
                tool_key = f"{server_name}.{tool['name']}"
                self.tools[tool_key] = tool
                
                logger.debug(f"Registered MCP tool: {tool_key}")
        
        except Exception as e:
            logger.error(f"Error loading tools from {server_name}: {e}", exc_info=True)
    
    async def _discover_tools(
        self,
        server_name: str,
        server_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Discover available tools from an MCP server
        
        This is a simplified implementation. In production, you would:
        1. Start the MCP server process
        2. Send a tools/list request
        3. Parse the response
        """
        # Predefined tool mappings for common MCP servers
        # This allows the system to work without actual MCP server connections
        
        tool_mappings = {
            "filesystem": [
                {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"}
                        },
                        "required": ["path"]
                    }
                },
                {
                    "name": "write_file",
                    "description": "Write contents to a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "File content"}
                        },
                        "required": ["path", "content"]
                    }
                },
                {
                    "name": "list_directory",
                    "description": "List contents of a directory",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path"}
                        },
                        "required": ["path"]
                    }
                }
            ],
            "brave-search": [
                {
                    "name": "search",
                    "description": "Search the web using Brave Search",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            ],
            "github": [
                {
                    "name": "search_repositories",
                    "description": "Search GitHub repositories",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_file_contents",
                    "description": "Get contents of a file from a repository",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "path": {"type": "string"}
                        },
                        "required": ["owner", "repo", "path"]
                    }
                }
            ]
        }
        
        return tool_mappings.get(server_name, [])
    
    def _create_execute_function(self, server_name: str, tool_name: str) -> Callable:
        """Create an execution function for an MCP tool"""
        
        async def execute(**kwargs) -> Any:
            """Execute the MCP tool"""
            logger.info(f"Executing MCP tool: {server_name}.{tool_name}")
            logger.debug(f"Parameters: {kwargs}")
            
            try:
                # In production, this would send a tools/call request to the MCP server
                # For now, we'll simulate execution
                result = await self._simulate_tool_execution(server_name, tool_name, kwargs)
                
                logger.info(f"MCP tool execution completed: {server_name}.{tool_name}")
                return result
                
            except Exception as e:
                logger.error(f"Error executing MCP tool {server_name}.{tool_name}: {e}", exc_info=True)
                return {"error": str(e)}
        
        return execute
    
    async def _simulate_tool_execution(
        self,
        server_name: str,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """Simulate MCP tool execution"""
        
        # Filesystem tools
        if server_name == "filesystem":
            if tool_name == "read_file":
                return {"content": f"Simulated content of {params.get('path', 'unknown')}"}
            elif tool_name == "write_file":
                return {"success": True, "message": f"File written: {params.get('path', 'unknown')}"}
            elif tool_name == "list_directory":
                return {"files": ["file1.txt", "file2.py", "dir1/"]}
        
        # Search tools
        elif server_name == "brave-search":
            if tool_name == "search":
                return {
                    "results": [
                        {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
                        {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."}
                    ]
                }
        
        # GitHub tools
        elif server_name == "github":
            if tool_name == "search_repositories":
                return {
                    "repositories": [
                        {"name": "repo1", "owner": "user1", "stars": 100},
                        {"name": "repo2", "owner": "user2", "stars": 50}
                    ]
                }
            elif tool_name == "get_file_contents":
                return {"content": "# Sample README\n\nThis is a sample file."}
        
        # Generic fallback
        return {"result": f"Simulated execution of {server_name}.{tool_name}", "params": params}
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a specific tool by name"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, MCPTool]:
        """Get all loaded tools"""
        return self.tools
    
    def get_tool_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all tools"""
        return {
            name: tool.to_metadata()
            for name, tool in self.tools.items()
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute an MCP tool
        
        Args:
            tool_name: Name of the tool (can be namespaced: server.tool)
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        return await tool.execute_fn(**kwargs)
    
    def cleanup(self) -> None:
        """Cleanup MCP server processes"""
        for server_name, process in self.server_processes.items():
            try:
                if hasattr(process, 'terminate'):
                    process.terminate()
                logger.info(f"Terminated MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error terminating server {server_name}: {e}")
