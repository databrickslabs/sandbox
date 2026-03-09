"""
Lightweight helpers to make any FastAPI app discoverable in the agent platform.

These are opt-in functions that agent developers call on their own FastAPI app.
They do NOT impose a framework — they just add discoverability endpoints.

Usage:
    from fastapi import FastAPI
    from dbx_agent_app import add_agent_card, add_mcp_endpoints

    app = FastAPI()

    @app.post("/invocations")
    async def invocations(request): ...

    add_agent_card(app, name="my_agent", description="Does stuff", capabilities=["search"])
    add_mcp_endpoints(app, tools=[...])  # optional
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


def add_agent_card(
    app: FastAPI,
    *,
    name: str,
    description: str,
    capabilities: List[str],
    version: str = "1.0.0",
    tools: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Add a GET /.well-known/agent.json endpoint to a FastAPI app.

    This makes the app discoverable by the agent platform scanner.
    Any Databricks App serving this endpoint will be auto-discovered.

    Args:
        app: FastAPI application to add the endpoint to
        name: Agent name (used for discovery and UC registration)
        description: Human-readable description of what the agent does
        capabilities: List of capability tags (e.g. ["search", "analysis"])
        version: Agent version string
        tools: Optional list of tool metadata dicts with name, description, parameters
    """
    card = {
        "schema_version": "a2a/1.0",
        "name": name,
        "description": description,
        "capabilities": capabilities,
        "version": version,
        "endpoints": {
            "invocations": "/invocations",
        },
        "tools": tools or [],
    }

    @app.get("/.well-known/agent.json")
    async def agent_card():
        return card

    @app.get("/health")
    async def health():
        return {"status": "healthy", "agent": name, "version": version}

    logger.info("Agent card registered: %s (capabilities=%s)", name, capabilities)


def add_mcp_endpoints(
    app: FastAPI,
    *,
    tools: List[Dict[str, Any]],
    server_name: Optional[str] = None,
    server_version: str = "1.0.0",
) -> None:
    """
    Add MCP JSON-RPC endpoints to a FastAPI app.

    Adds:
      POST /api/mcp      — MCP JSON-RPC 2.0 (tools/list, tools/call, server/info)
      GET  /api/mcp/tools — convenience tool listing

    Each tool dict must have:
      - name: str
      - description: str
      - function: async callable
      - parameters: dict of param_name -> {"type": str, "required": bool}

    Args:
        app: FastAPI application
        tools: List of tool definition dicts
        server_name: MCP server name (defaults to app title)
        server_version: MCP server version
    """
    _server_name = server_name or getattr(app, "title", "mcp-server")

    def _to_mcp_format(tool_list):
        """Convert tool dicts to MCP tool format."""
        mcp_tools = []
        for t in tool_list:
            props = {}
            required = []
            for pname, pspec in t.get("parameters", {}).items():
                props[pname] = {
                    "type": pspec.get("type", "string"),
                    "description": pspec.get("description", ""),
                }
                if pspec.get("required", False):
                    required.append(pname)

            mcp_tools.append({
                "name": t["name"],
                "description": t["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            })
        return mcp_tools

    tool_lookup = {t["name"]: t for t in tools}
    mcp_formatted = _to_mcp_format(tools)

    @app.post("/api/mcp")
    async def mcp_jsonrpc(request: Request):
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        try:
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": mcp_formatted},
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                tool = tool_lookup.get(tool_name)
                if not tool:
                    raise ValueError(f"Tool not found: {tool_name}")

                result = await tool["function"](**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"result": result},
                }

            elif method == "server/info":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "name": _server_name,
                        "version": server_version,
                        "protocol_version": "1.0",
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

        except Exception as e:
            logger.error("MCP request failed: %s", e)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},
            }

    @app.get("/api/mcp/tools")
    async def list_mcp_tools():
        return {"tools": mcp_formatted}

    logger.info("MCP endpoints registered: %d tools", len(tools))
