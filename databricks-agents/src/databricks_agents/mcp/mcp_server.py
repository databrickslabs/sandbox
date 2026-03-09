"""
MCP server implementation for agents.

Provides an MCP server that exposes agent tools via the Model Context Protocol.
Works with any FastAPI app.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from fastapi import Request

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
    MCP server that exposes tools via JSON-RPC.

    Accepts tools as dicts with name, description, parameters, function keys.
    """

    def __init__(self, tools, config: MCPServerConfig):
        """
        Initialize MCP server.

        Args:
            tools: List of ToolDefinition objects or dicts with name/description/parameters/function
            config: MCP server configuration
        """
        self._tools = tools
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
                logger.error("MCP request failed: %s", e)
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id") if isinstance(body, dict) else None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }

        @app.get("/api/mcp/tools")
        async def list_mcp_tools():
            """List available MCP tools."""
            return await self._list_tools()

    def _get_tool_name(self, tool) -> str:
        return tool.name if hasattr(tool, "name") else tool["name"]

    def _get_tool_description(self, tool) -> str:
        return tool.description if hasattr(tool, "description") else tool["description"]

    def _get_tool_parameters(self, tool) -> Dict[str, Any]:
        return tool.parameters if hasattr(tool, "parameters") else tool.get("parameters", {})

    def _get_tool_function(self, tool):
        return tool.function if hasattr(tool, "function") else tool["function"]

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

        for tool in self._tools:
            mcp_tool = {
                "name": self._get_tool_name(tool),
                "description": self._get_tool_description(tool),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }

            for param_name, param_spec in self._get_tool_parameters(tool).items():
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
        """Call a tool via MCP."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        tool_def = None
        for tool in self._tools:
            if self._get_tool_name(tool) == tool_name:
                tool_def = tool
                break

        if not tool_def:
            raise ValueError(f"Tool not found: {tool_name}")

        try:
            result = await self._get_tool_function(tool_def)(**arguments)
            return {"result": result}
        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            raise


def setup_mcp_server(tools, config: Optional[MCPServerConfig] = None, fastapi_app=None):
    """
    Set up MCP server for an agent.

    Args:
        tools: List of tool dicts with name/description/parameters/function keys
        config: Optional MCP server configuration
        fastapi_app: FastAPI app to add routes to (required)

    Returns:
        MCPServer instance
    """
    if config is None:
        config = MCPServerConfig(name="mcp-server")

    server = MCPServer(tools, config)
    server.setup_routes(fastapi_app)

    return server
