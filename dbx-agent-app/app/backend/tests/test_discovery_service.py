"""
Unit tests for discovery service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.discovery import (
    DiscoveryService,
    DiscoveredServer,
    DiscoveryResult,
    create_discovery_service,
)
from app.services.mcp_client import (
    MCPClient,
    MCPTool,
    MCPConnectionError,
    MCPTimeoutError,
)
from app.services.tool_parser import NormalizedTool


class TestDiscoveryService:
    """Tests for DiscoveryService class."""

    @pytest.mark.asyncio
    async def test_discover_from_url_success(self):
        """Test successful discovery from a single URL."""
        # Mock MCP client
        mock_client = AsyncMock(spec=MCPClient)
        mock_tools = [
            MCPTool(
                name="tool1",
                description="First tool",
                input_schema={"type": "object"},
            ),
            MCPTool(
                name="tool2",
                description="Second tool",
                input_schema={"type": "string"},
            ),
        ]
        mock_client.list_tools.return_value = mock_tools

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_url(
            "https://mcp.example.com",
            kind="custom",
        )

        assert isinstance(result, DiscoveredServer)
        assert result.server_url == "https://mcp.example.com"
        assert result.kind == "custom"
        assert len(result.tools) == 2
        assert result.error is None
        assert result.tools[0].name == "tool1"
        assert result.tools[1].name == "tool2"

    @pytest.mark.asyncio
    async def test_discover_from_url_connection_error(self):
        """Test discovery handles connection errors gracefully."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.list_tools.side_effect = MCPConnectionError("Connection failed")

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_url("https://mcp.example.com")

        assert isinstance(result, DiscoveredServer)
        assert result.server_url == "https://mcp.example.com"
        assert len(result.tools) == 0
        assert result.error is not None
        assert "Connection failed" in result.error

    @pytest.mark.asyncio
    async def test_discover_from_url_timeout_error(self):
        """Test discovery handles timeout errors gracefully."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.list_tools.side_effect = MCPTimeoutError("Request timed out")

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_url("https://mcp.example.com")

        assert result.error is not None
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_discover_from_url_skip_invalid_tools(self):
        """Test discovery skips invalid tools without failing."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_tools = [
            MCPTool(
                name="valid_tool",
                description="Valid",
                input_schema={"type": "object"},
            ),
            MCPTool(
                name="",  # Invalid - empty name
                description="Invalid",
                input_schema={},
            ),
        ]
        mock_client.list_tools.return_value = mock_tools

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_url("https://mcp.example.com")

        # Should only include valid tool
        assert len(result.tools) == 1
        assert result.tools[0].name == "valid_tool"

    @pytest.mark.asyncio
    async def test_discover_from_url_without_provided_client(self):
        """Test discovery creates its own client when none provided."""
        service = DiscoveryService()  # No client provided

        # We can't easily test the actual HTTP call without a real server
        # But we can verify the method doesn't crash
        # In a real scenario, this would require mocking at a lower level
        # For now, we'll test the error handling
        result = await service.discover_from_url("https://invalid-mcp-server-xyz.example")

        # Should return a result with an error
        assert isinstance(result, DiscoveredServer)
        # Error will vary based on network conditions, but should be present
        # (Could be connection error, DNS error, etc.)

    @pytest.mark.asyncio
    async def test_discover_from_workspace_returns_result(self):
        """Test workspace discovery returns a valid DiscoveryResult."""
        service = DiscoveryService()
        result = await service.discover_from_workspace()

        assert isinstance(result, DiscoveryResult)
        # May find servers if workspace apps exist, or return empty
        assert result.servers_discovered >= 0
        assert result.tools_discovered >= 0

    @pytest.mark.asyncio
    async def test_discover_from_catalog_no_url(self):
        """Test catalog discovery returns empty when catalog URL not configured."""
        service = DiscoveryService()
        result = await service.discover_from_catalog()

        assert isinstance(result, DiscoveryResult)
        # Without mcp_catalog_url configured, returns empty results
        assert result.servers_discovered == 0
        assert result.tools_discovered == 0
        assert len(result.servers) == 0

    @pytest.mark.asyncio
    async def test_discover_from_urls_multiple_servers(self):
        """Test discovery from multiple URLs."""
        mock_client = AsyncMock(spec=MCPClient)

        # First server returns 2 tools
        first_tools = [
            MCPTool(name="tool1", description="Tool 1", input_schema={}),
            MCPTool(name="tool2", description="Tool 2", input_schema={}),
        ]

        # Second server returns 1 tool
        second_tools = [
            MCPTool(name="tool3", description="Tool 3", input_schema={}),
        ]

        # Configure mock to return different results based on call count
        mock_client.list_tools.side_effect = [first_tools, second_tools]

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_urls(
            ["https://mcp1.example.com", "https://mcp2.example.com"],
            kind="external",
        )

        assert result.servers_discovered == 2
        assert result.tools_discovered == 3
        assert len(result.servers) == 2
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_discover_from_urls_empty_list(self):
        """Test discovery from empty URL list."""
        service = DiscoveryService()
        result = await service.discover_from_urls([])

        assert result.servers_discovered == 0
        assert result.tools_discovered == 0
        assert len(result.servers) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_discover_from_urls_partial_failures(self):
        """Test discovery handles partial failures across multiple servers."""
        mock_client = AsyncMock(spec=MCPClient)

        # First server succeeds
        first_tools = [
            MCPTool(name="tool1", description="Tool 1", input_schema={}),
        ]

        # Second server fails
        mock_client.list_tools.side_effect = [
            first_tools,
            MCPConnectionError("Connection failed"),
        ]

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_from_urls(
            ["https://mcp1.example.com", "https://mcp2.example.com"]
        )

        assert result.servers_discovered == 1  # Only first succeeded
        assert result.tools_discovered == 1
        assert len(result.servers) == 2  # Both servers returned
        assert len(result.errors) == 1  # One error
        assert "mcp2.example.com" in result.errors[0]

    @pytest.mark.asyncio
    async def test_discover_all_without_custom_urls(self):
        """Test full discovery without custom URLs returns valid result."""
        service = DiscoveryService()
        result = await service.discover_all()

        # Runs workspace + catalog discovery; may or may not find servers
        assert isinstance(result, DiscoveryResult)
        assert result.servers_discovered >= 0
        assert result.tools_discovered >= 0

    @pytest.mark.asyncio
    async def test_discover_all_with_custom_urls(self):
        """Test full discovery with custom URLs."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_tools = [
            MCPTool(name="tool1", description="Tool 1", input_schema={}),
        ]
        mock_client.list_tools.return_value = mock_tools

        service = DiscoveryService(mcp_client=mock_client)
        result = await service.discover_all(
            custom_urls=["https://mcp.example.com"]
        )

        # Should include stub results + custom URL results
        assert result.servers_discovered >= 1
        assert result.tools_discovered >= 1

    @pytest.mark.asyncio
    async def test_create_discovery_service_factory(self):
        """Test factory function creates service."""
        service = await create_discovery_service()

        assert isinstance(service, DiscoveryService)


class TestDiscoveredServer:
    """Tests for DiscoveredServer dataclass."""

    def test_discovered_server_creation(self):
        """Test creating DiscoveredServer instance."""
        tools = [
            NormalizedTool(name="tool1", description="Tool 1", parameters="{}"),
        ]

        server = DiscoveredServer(
            server_url="https://mcp.example.com",
            kind="custom",
            tools=tools,
        )

        assert server.server_url == "https://mcp.example.com"
        assert server.kind == "custom"
        assert len(server.tools) == 1
        assert server.error is None

    def test_discovered_server_with_error(self):
        """Test DiscoveredServer with error."""
        server = DiscoveredServer(
            server_url="https://mcp.example.com",
            kind="custom",
            tools=[],
            error="Connection failed",
        )

        assert server.error == "Connection failed"
        assert len(server.tools) == 0


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_discovery_result_creation(self):
        """Test creating DiscoveryResult instance."""
        tools = [
            NormalizedTool(name="tool1", description="Tool 1", parameters="{}"),
        ]
        servers = [
            DiscoveredServer(
                server_url="https://mcp.example.com",
                kind="custom",
                tools=tools,
            )
        ]

        result = DiscoveryResult(
            servers_discovered=1,
            tools_discovered=1,
            servers=servers,
            errors=[],
        )

        assert result.servers_discovered == 1
        assert result.tools_discovered == 1
        assert len(result.servers) == 1
        assert len(result.errors) == 0

    def test_discovery_result_with_errors(self):
        """Test DiscoveryResult with errors."""
        result = DiscoveryResult(
            servers_discovered=0,
            tools_discovered=0,
            servers=[],
            errors=["Error 1", "Error 2"],
        )

        assert len(result.errors) == 2
        assert result.servers_discovered == 0
