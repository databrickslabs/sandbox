"""
Unit tests for MCP client.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.mcp_client import (
    MCPClient,
    MCPTool,
    MCPConnectionError,
    MCPTimeoutError,
    create_mcp_client,
)


class TestMCPClient:
    """Tests for MCPClient class."""

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """Test successful tool listing from MCP server."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "search_experts",
                        "description": "Search for experts by keyword",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "get_transcript",
                        "description": "Get transcript by ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "transcript_id": {"type": "string"},
                            },
                        },
                    },
                ]
            },
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                tools = await client.list_tools("https://mcp.example.com")

                assert len(tools) == 2
                assert tools[0].name == "search_experts"
                assert tools[0].description == "Search for experts by keyword"
                assert tools[0].input_schema["type"] == "object"
                assert tools[1].name == "get_transcript"

    @pytest.mark.asyncio
    async def test_list_tools_empty_response(self):
        """Test handling of empty tool list response."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []},
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                tools = await client.list_tools("https://mcp.example.com")

                assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_list_tools_missing_tools_key(self):
        """Test handling of response without tools key."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {},
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                tools = await client.list_tools("https://mcp.example.com")

                assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_list_tools_skip_invalid_tool(self):
        """Test that invalid tools are skipped without failing entire operation."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "valid_tool",
                        "description": "A valid tool",
                        "inputSchema": {"type": "object"},
                    },
                    {
                        # Missing name - should be skipped
                        "description": "Invalid tool",
                        "inputSchema": {"type": "object"},
                    },
                    {
                        "name": "",  # Empty name - should be skipped
                        "description": "Another invalid tool",
                        "inputSchema": {"type": "object"},
                    },
                ]
            },
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                tools = await client.list_tools("https://mcp.example.com")

                # Only the valid tool should be returned
                assert len(tools) == 1
                assert tools[0].name == "valid_tool"

    @pytest.mark.asyncio
    async def test_list_tools_connection_error(self):
        """Test handling of connection errors."""
        async with MCPClient() as client:
            with patch.object(
                client._client, "post", side_effect=httpx.ConnectError("Connection failed")
            ):
                with pytest.raises(MCPConnectionError) as exc_info:
                    await client.list_tools("https://mcp.example.com")

                assert "HTTP error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tools_timeout_error(self):
        """Test handling of timeout errors."""
        async with MCPClient() as client:
            with patch.object(
                client._client, "post", side_effect=httpx.TimeoutException("Request timed out")
            ):
                with pytest.raises(MCPTimeoutError) as exc_info:
                    await client.list_tools("https://mcp.example.com")

                assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tools_json_rpc_error(self):
        """Test handling of JSON-RPC error response."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32600,
                "message": "Invalid Request",
            },
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                with pytest.raises(MCPConnectionError) as exc_info:
                    await client.list_tools("https://mcp.example.com")

                assert "Invalid Request" in str(exc_info.value)
                assert "-32600" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tools_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.side_effect = ValueError("Invalid JSON")
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                with pytest.raises(MCPConnectionError) as exc_info:
                    await client.list_tools("https://mcp.example.com")

                assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_server_info_success(self):
        """Test successful server info retrieval."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "Example MCP Server",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "tools": {},
                },
            },
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                info = await client.get_server_info("https://mcp.example.com")

                assert info["protocolVersion"] == "2024-11-05"
                assert info["serverInfo"]["name"] == "Example MCP Server"

    @pytest.mark.asyncio
    async def test_ping_success(self):
        """Test successful ping."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {},
        }

        async with MCPClient() as client:
            with patch.object(client._client, "post") as mock_post:
                mock_response_obj = MagicMock()
                mock_response_obj.json.return_value = mock_response
                mock_response_obj.raise_for_status = MagicMock()
                mock_post.return_value = mock_response_obj

                result = await client.ping("https://mcp.example.com")

                assert result is True

    @pytest.mark.asyncio
    async def test_ping_connection_failure(self):
        """Test ping returns False on connection failure."""
        async with MCPClient() as client:
            with patch.object(
                client._client, "post", side_effect=httpx.ConnectError("Connection failed")
            ):
                result = await client.ping("https://mcp.example.com")

                assert result is False

    @pytest.mark.asyncio
    async def test_ping_timeout(self):
        """Test ping returns False on timeout."""
        async with MCPClient() as client:
            with patch.object(
                client._client, "post", side_effect=httpx.TimeoutException("Timeout")
            ):
                result = await client.ping("https://mcp.example.com")

                assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client works as async context manager."""
        async with MCPClient() as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

        # Client should be closed after context exit
        # (We can't directly test this without accessing internals)

    @pytest.mark.asyncio
    async def test_request_id_increments(self):
        """Test that JSON-RPC request IDs increment."""
        async with MCPClient() as client:
            id1 = client._next_request_id()
            id2 = client._next_request_id()
            id3 = client._next_request_id()

            assert id2 == id1 + 1
            assert id3 == id2 + 1

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self):
        """Test that using client without context manager raises error."""
        client = MCPClient()

        with pytest.raises(MCPConnectionError) as exc_info:
            await client.list_tools("https://mcp.example.com")

        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_mcp_client_factory(self):
        """Test factory function creates client."""
        client = await create_mcp_client()

        assert isinstance(client, MCPClient)
        assert client.timeout == 30.0


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_mcp_tool_creation(self):
        """Test creating MCPTool instance."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object"}

    def test_mcp_tool_optional_description(self):
        """Test MCPTool with None description."""
        tool = MCPTool(
            name="test_tool",
            description=None,
            input_schema={},
        )

        assert tool.name == "test_tool"
        assert tool.description is None
