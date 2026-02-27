"""
MCP server implementation for agents.

Provides an MCP server that exposes agent tools via the Model Context Protocol.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """
    Configuration for MCP server.
    
    Attributes:
        name: Server name
        version: Server version
        description: Server description
    """
    name: str
    version: str = "1.0.0"
    description: str = "MCP server for agent tools"


class MCPServer:
    """
    MCP server that exposes agent tools.
    
    Integrates with AgentApp to automatically expose registered tools
    via the Model Context Protocol.
    
    Usage:
        app = AgentApp(...)
        mcp_server = MCPServer(app, config=MCPServerConfig(...))
        mcp_server.setup_routes(app)
    """
    
    def __init__(self, agent_app, config: MCPServerConfig):
        """
        Initialize MCP server.
        
        Args:
            agent_app: AgentApp instance
            config: MCP server configuration
        """
        self.agent_app = agent_app
        self.config = config
    
    def setup_routes(self, app):
        """
        Set up MCP protocol routes on the FastAPI app.
        
        Adds:
        - POST /api/mcp - MCP JSON-RPC endpoint
        - GET /api/mcp/tools - List available tools
        """
        
        @app.post("/api/mcp")
        async def mcp_jsonrpc(request: Request):
            """MCP JSON-RPC endpoint."""
            try:
                body = await request.json()
                method = body.get("method")
                params = body.get("params", {})
                request_id = body.get("id")
                
                if method == "tools/list":
                    result = await self._list_tools()
                elif method == "tools/call":
                    result = await self._call_tool(params)
                elif method == "server/info":
                    result = self._server_info()
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"MCP request failed: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id") if hasattr(body, 'get') else None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
        
        @app.get("/api/mcp/tools")
        async def list_mcp_tools():
            """List available MCP tools."""
            return await self._list_tools()
    
    def _server_info(self) -> Dict[str, Any]:
        """Get MCP server information."""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
            "protocol_version": "1.0",
        }
    
    async def _list_tools(self) -> Dict[str, Any]:
        """List all available tools in MCP format."""
        tools = []
        
        for tool in self.agent_app.agent_metadata.tools:
            # Convert tool definition to MCP format
            mcp_tool = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Convert parameters to JSON Schema format
            for param_name, param_spec in tool.parameters.items():
                param_type = param_spec.get("type", "string")
                mcp_tool["inputSchema"]["properties"][param_name] = {
                    "type": param_type,
                    "description": param_spec.get("description", "")
                }
                if param_spec.get("required", False):
                    mcp_tool["inputSchema"]["required"].append(param_name)
            
            tools.append(mcp_tool)
        
        return {"tools": tools}
    
    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool via MCP.
        
        Args:
            params: MCP call parameters with 'name' and 'arguments'
            
        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Find the tool
        tool_def = None
        for tool in self.agent_app.agent_metadata.tools:
            if tool.name == tool_name:
                tool_def = tool
                break
        
        if not tool_def:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Execute the tool
        try:
            result = await tool_def.function(**arguments)
            return {"result": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise


def setup_mcp_server(agent_app, config: Optional[MCPServerConfig] = None):
    """
    Set up MCP server for an AgentApp.
    
    Args:
        agent_app: AgentApp instance
        config: Optional MCP server configuration
        
    Returns:
        MCPServer instance
        
    Example:
        >>> app = AgentApp(name="my_agent", ...)
        >>> mcp_server = setup_mcp_server(app)
    """
    if config is None:
        config = MCPServerConfig(
            name=agent_app.agent_metadata.name,
            description=agent_app.agent_metadata.description,
        )
    
    server = MCPServer(agent_app, config)
    server.setup_routes(agent_app)
    
    return server
