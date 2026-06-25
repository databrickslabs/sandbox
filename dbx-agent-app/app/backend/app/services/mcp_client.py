"""
MCP Client for discovering and listing tools from MCP servers.

This module provides a client wrapper for the Model Context Protocol (MCP),
enabling communication with MCP servers to discover available tools.

The MCP protocol uses JSON-RPC 2.0 over HTTP/SSE for communication.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
from app.config import settings


class MCPConnectionError(Exception):
    """Raised when connection to MCP server fails."""

    pass


class MCPTimeoutError(Exception):
    """Raised when MCP server request times out."""

    pass


@dataclass
class MCPTool:
    """
    Represents a tool discovered from an MCP server.

    Attributes:
        name: Tool identifier (e.g., "search_transcripts")
        description: Human-readable description
        input_schema: JSON Schema for tool parameters
    """

    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]


class MCPClient:
    """
    Client for interacting with MCP servers.

    Handles connection pooling, timeouts, and error recovery when
    communicating with MCP servers to list available tools.

    Usage:
        async with MCPClient() as client:
            tools = await client.list_tools("https://mcp.example.com")
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
    ):
        """
        Initialize MCP client with connection pool settings.

        Args:
            timeout: Request timeout in seconds (default: 30.0)
            max_connections: Maximum total connections (default: 10)
            max_keepalive_connections: Maximum keep-alive connections (default: 5)
        """
        self.timeout = timeout
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _next_request_id(self) -> int:
        """Generate next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def _send_jsonrpc_request(
        self,
        server_url: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request to an MCP server.

        Args:
            server_url: MCP server endpoint URL
            method: JSON-RPC method name
            params: Optional method parameters

        Returns:
            JSON-RPC response result

        Raises:
            MCPConnectionError: If connection fails
            MCPTimeoutError: If request times out
        """
        if not self._client:
            raise MCPConnectionError("Client not initialized. Use async context manager.")

        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }

        if params:
            request_payload["params"] = params

        try:
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            response = await self._client.post(
                server_url,
                json=request_payload,
                headers=headers,
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error = result["error"]
                raise MCPConnectionError(
                    f"MCP server error: {error.get('message', 'Unknown error')} "
                    f"(code: {error.get('code', 'unknown')})"
                )

            return result.get("result", {})

        except httpx.TimeoutException as e:
            raise MCPTimeoutError(f"Request to {server_url} timed out: {str(e)}")
        except httpx.HTTPError as e:
            raise MCPConnectionError(f"HTTP error connecting to {server_url}: {str(e)}")
        except json.JSONDecodeError as e:
            raise MCPConnectionError(f"Invalid JSON response from {server_url}: {str(e)}")

    async def list_tools(self, server_url: str, auth_token: Optional[str] = None) -> List[MCPTool]:
        """
        List all tools available from an MCP server.

        Sends a 'tools/list' JSON-RPC request to the MCP server and
        parses the response into MCPTool objects.

        Args:
            server_url: MCP server endpoint URL

        Returns:
            List of MCPTool objects

        Raises:
            MCPConnectionError: If connection or parsing fails
            MCPTimeoutError: If request times out

        Example:
            >>> async with MCPClient() as client:
            ...     tools = await client.list_tools("https://mcp.example.com")
            ...     for tool in tools:
            ...         print(f"{tool.name}: {tool.description}")
        """
        try:
            result = await self._send_jsonrpc_request(
                server_url=server_url,
                method="tools/list",
                params={},
                auth_token=auth_token,
            )

            tools_data = result.get("tools", [])
            tools = []

            for tool_data in tools_data:
                try:
                    tool = MCPTool(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description"),
                        input_schema=tool_data.get("inputSchema", {}),
                    )

                    if not tool.name:
                        continue

                    tools.append(tool)

                except (KeyError, TypeError) as e:
                    # Log but don't fail entire operation for one bad tool
                    continue

            return tools

        except (MCPConnectionError, MCPTimeoutError):
            raise
        except Exception as e:
            raise MCPConnectionError(f"Unexpected error listing tools: {str(e)}")

    async def get_server_info(self, server_url: str) -> Dict[str, Any]:
        """
        Get server information from an MCP server.

        Sends an 'initialize' JSON-RPC request to get server capabilities
        and metadata.

        Args:
            server_url: MCP server endpoint URL

        Returns:
            Server information dictionary

        Raises:
            MCPConnectionError: If connection fails
            MCPTimeoutError: If request times out
        """
        try:
            result = await self._send_jsonrpc_request(
                server_url=server_url,
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": settings.api_title,
                        "version": settings.api_version,
                    },
                },
            )

            return result

        except (MCPConnectionError, MCPTimeoutError):
            raise
        except Exception as e:
            raise MCPConnectionError(f"Unexpected error getting server info: {str(e)}")

    async def ping(self, server_url: str) -> bool:
        """
        Ping an MCP server to check if it's alive.

        Sends a 'ping' JSON-RPC request (or attempts connection).

        Args:
            server_url: MCP server endpoint URL

        Returns:
            True if server is reachable, False otherwise
        """
        try:
            await self._send_jsonrpc_request(
                server_url=server_url,
                method="ping",
                params={},
            )
            return True
        except (MCPConnectionError, MCPTimeoutError):
            return False
        except Exception:
            return False


async def create_mcp_client() -> MCPClient:
    """
    Factory function to create an MCP client instance.

    Returns:
        Configured MCPClient instance
    """
    return MCPClient(
        timeout=30.0,
        max_connections=10,
        max_keepalive_connections=5,
    )
