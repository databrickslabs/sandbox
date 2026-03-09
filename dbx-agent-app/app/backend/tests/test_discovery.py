"""
Tests for Discovery endpoint.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.discovery import DiscoveryResult, DiscoveredServer
from app.services.tool_parser import NormalizedTool
from app.models import MCPServer, Tool
from app.models.mcp_server import MCPServerKind


@pytest.fixture(autouse=True)
def reset_discovery_state():
    """Reset discovery state before each test."""
    from app.routes import discovery
    discovery._discovery_state = {
        "is_running": False,
        "last_run_timestamp": None,
        "last_run_status": None,
        "last_run_message": None,
    }
    yield


@pytest.fixture
def mock_discovery_result():
    """Create a mock discovery result with sample data."""
    return DiscoveryResult(
        servers_discovered=2,
        tools_discovered=5,
        servers=[
            DiscoveredServer(
                server_url="https://mcp1.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(
                        name="tool1",
                        description="Tool 1 description",
                        parameters='{"type": "object"}',
                    ),
                    NormalizedTool(
                        name="tool2",
                        description="Tool 2 description",
                        parameters='{"type": "object"}',
                    ),
                ],
            ),
            DiscoveredServer(
                server_url="https://mcp2.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(
                        name="tool3",
                        description="Tool 3 description",
                        parameters='{"type": "object"}',
                    ),
                    NormalizedTool(
                        name="tool4",
                        description="Tool 4 description",
                        parameters='{"type": "object"}',
                    ),
                    NormalizedTool(
                        name="tool5",
                        description="Tool 5 description",
                        parameters='{"type": "object"}',
                    ),
                ],
            ),
        ],
        errors=[],
    )


@pytest.mark.asyncio
async def test_discovery_refresh_success(client, db, mock_discovery_result):
    """Test discovery refresh endpoint with successful discovery."""
    with patch("app.routes.discovery.DiscoveryService") as mock_service_class:
        # Setup mock
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.discover_all = AsyncMock(return_value=mock_discovery_result)
        mock_service.upsert_discovery_results = MagicMock()

        # Mock upsert result
        from app.services.discovery import UpsertResult
        mock_service.upsert_discovery_results.return_value = UpsertResult(
            new_servers=2,
            updated_servers=0,
            new_tools=5,
            updated_tools=0,
        )

        # Make request
        response = client.post(
            "/api/discovery/refresh",
            json={
                "server_urls": ["https://mcp1.example.com", "https://mcp2.example.com"],
            },
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["servers_discovered"] == 2
        assert data["tools_discovered"] == 5
        assert data["new_servers"] == 2
        assert data["new_tools"] == 5
        assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_discovery_refresh_with_errors(client, db):
    """Test discovery refresh endpoint with partial failures."""
    result_with_errors = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=2,
        servers=[
            DiscoveredServer(
                server_url="https://mcp1.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(
                        name="tool1",
                        description="Tool 1",
                        parameters="{}",
                    ),
                    NormalizedTool(
                        name="tool2",
                        description="Tool 2",
                        parameters="{}",
                    ),
                ],
            ),
            DiscoveredServer(
                server_url="https://mcp2.example.com",
                kind="custom",
                tools=[],
                error="Connection timeout",
            ),
        ],
        errors=["https://mcp2.example.com: Connection timeout"],
    )

    with patch("app.routes.discovery.DiscoveryService") as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.discover_all = AsyncMock(return_value=result_with_errors)

        from app.services.discovery import UpsertResult
        mock_service.upsert_discovery_results.return_value = UpsertResult(
            new_servers=1,
            updated_servers=0,
            new_tools=2,
            updated_tools=0,
        )

        response = client.post(
            "/api/discovery/refresh",
            json={
                "server_urls": ["https://mcp1.example.com", "https://mcp2.example.com"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        assert data["servers_discovered"] == 1
        assert data["tools_discovered"] == 2
        assert len(data["errors"]) == 1
        assert "Connection timeout" in data["errors"][0]


@pytest.mark.asyncio
async def test_discovery_refresh_no_sources(client, db):
    """Test discovery refresh endpoint with no sources specified."""
    response = client.post(
        "/api/discovery/refresh",
        json={
            "server_urls": [],
            "discover_workspace": False,
            "discover_catalog": False,
        },
    )

    assert response.status_code == 400
    assert "at least one discovery source" in response.json()["detail"].lower()


def test_discovery_status_initial(client, db):
    """Test discovery status endpoint before any runs."""
    response = client.get("/api/discovery/status")

    assert response.status_code == 200
    data = response.json()
    assert data["is_running"] is False
    assert data["last_run_timestamp"] is None
    assert data["last_run_status"] is None


@pytest.mark.asyncio
async def test_discovery_status_after_run(client, db, mock_discovery_result):
    """Test discovery status endpoint after a successful run."""
    with patch("app.routes.discovery.DiscoveryService") as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.discover_all = AsyncMock(return_value=mock_discovery_result)

        from app.services.discovery import UpsertResult
        mock_service.upsert_discovery_results.return_value = UpsertResult(
            new_servers=2,
            updated_servers=0,
            new_tools=5,
            updated_tools=0,
        )

        # Run discovery
        client.post(
            "/api/discovery/refresh",
            json={"server_urls": ["https://mcp.example.com"]},
        )

        # Check status
        response = client.get("/api/discovery/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is False
        assert data["last_run_timestamp"] is not None
        assert data["last_run_status"] == "success"


def test_upsert_discovery_creates_new_server(db):
    """Test upserting discovery results creates new servers."""
    from app.services.discovery import DiscoveryService

    service = DiscoveryService()

    discovery_result = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=2,
        servers=[
            DiscoveredServer(
                server_url="https://new-server.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(
                        name="new_tool1",
                        description="New tool 1",
                        parameters="{}",
                    ),
                    NormalizedTool(
                        name="new_tool2",
                        description="New tool 2",
                        parameters="{}",
                    ),
                ],
            ),
        ],
        errors=[],
    )

    upsert_result = service.upsert_discovery_results(db, discovery_result)

    assert upsert_result.new_servers == 1
    assert upsert_result.updated_servers == 0
    assert upsert_result.new_tools == 2
    assert upsert_result.updated_tools == 0

    # Verify database
    server = db.query(MCPServer).filter_by(server_url="https://new-server.example.com").first()
    assert server is not None
    assert server.kind == MCPServerKind.CUSTOM

    tools = db.query(Tool).filter_by(mcp_server_id=server.id).all()
    assert len(tools) == 2
    assert {t.name for t in tools} == {"new_tool1", "new_tool2"}


def test_upsert_discovery_updates_existing_server(db, sample_mcp_server):
    """Test upserting discovery results updates existing servers."""
    from app.services.discovery import DiscoveryService

    service = DiscoveryService()

    # Update existing server with new tool
    discovery_result = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=1,
        servers=[
            DiscoveredServer(
                server_url=sample_mcp_server.server_url,
                kind="custom",
                tools=[
                    NormalizedTool(
                        name="new_tool",
                        description="New tool",
                        parameters="{}",
                    ),
                ],
            ),
        ],
        errors=[],
    )

    upsert_result = service.upsert_discovery_results(db, discovery_result)

    assert upsert_result.new_servers == 0
    assert upsert_result.updated_servers == 1
    assert upsert_result.new_tools == 1
    assert upsert_result.updated_tools == 0

    # Verify tool was added
    tools = db.query(Tool).filter_by(mcp_server_id=sample_mcp_server.id).all()
    assert len(tools) == 1
    assert tools[0].name == "new_tool"


def test_upsert_discovery_updates_existing_tool(db, sample_mcp_server, sample_tool):
    """Test upserting discovery results updates existing tools."""
    from app.services.discovery import DiscoveryService

    service = DiscoveryService()

    # Update existing tool
    discovery_result = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=1,
        servers=[
            DiscoveredServer(
                server_url=sample_mcp_server.server_url,
                kind="custom",
                tools=[
                    NormalizedTool(
                        name=sample_tool.name,
                        description="Updated description",
                        parameters='{"type": "object", "properties": {"new": {"type": "string"}}}',
                    ),
                ],
            ),
        ],
        errors=[],
    )

    upsert_result = service.upsert_discovery_results(db, discovery_result)

    assert upsert_result.new_servers == 0
    assert upsert_result.updated_servers == 1
    assert upsert_result.new_tools == 0
    assert upsert_result.updated_tools == 1

    # Verify tool was updated
    db.refresh(sample_tool)
    assert sample_tool.description == "Updated description"
    assert "new" in sample_tool.parameters


def test_upsert_discovery_handles_duplicates(db):
    """Test upserting discovery results handles duplicate tools gracefully."""
    from app.services.discovery import DiscoveryService

    service = DiscoveryService()

    # First discovery
    discovery_result1 = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=2,
        servers=[
            DiscoveredServer(
                server_url="https://server.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(name="tool1", description="Tool 1", parameters="{}"),
                    NormalizedTool(name="tool2", description="Tool 2", parameters="{}"),
                ],
            ),
        ],
        errors=[],
    )

    result1 = service.upsert_discovery_results(db, discovery_result1)
    assert result1.new_servers == 1
    assert result1.new_tools == 2

    # Second discovery with same tools (should update, not create)
    discovery_result2 = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=2,
        servers=[
            DiscoveredServer(
                server_url="https://server.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(name="tool1", description="Updated Tool 1", parameters="{}"),
                    NormalizedTool(name="tool2", description="Updated Tool 2", parameters="{}"),
                ],
            ),
        ],
        errors=[],
    )

    result2 = service.upsert_discovery_results(db, discovery_result2)
    assert result2.new_servers == 0
    assert result2.updated_servers == 1
    assert result2.new_tools == 0
    assert result2.updated_tools == 2

    # Verify only 2 tools exist (no duplicates)
    server = db.query(MCPServer).filter_by(server_url="https://server.example.com").first()
    tools = db.query(Tool).filter_by(mcp_server_id=server.id).all()
    assert len(tools) == 2


def test_upsert_discovery_skips_servers_with_errors(db):
    """Test upserting discovery results skips servers with errors."""
    from app.services.discovery import DiscoveryService

    service = DiscoveryService()

    discovery_result = DiscoveryResult(
        servers_discovered=1,
        tools_discovered=1,
        servers=[
            DiscoveredServer(
                server_url="https://good-server.example.com",
                kind="custom",
                tools=[
                    NormalizedTool(name="tool1", description="Tool 1", parameters="{}"),
                ],
            ),
            DiscoveredServer(
                server_url="https://bad-server.example.com",
                kind="custom",
                tools=[],
                error="Connection failed",
            ),
        ],
        errors=["https://bad-server.example.com: Connection failed"],
    )

    upsert_result = service.upsert_discovery_results(db, discovery_result)

    assert upsert_result.new_servers == 1
    assert upsert_result.new_tools == 1

    # Verify only good server was created
    servers = db.query(MCPServer).all()
    assert len(servers) == 1
    assert servers[0].server_url == "https://good-server.example.com"
