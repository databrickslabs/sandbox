"""Tests for the developer dashboard — scanner, routes, and CLI."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from databricks_agents.discovery import DiscoveredAgent
from databricks_agents.dashboard.scanner import DashboardScanner
from databricks_agents.dashboard.app import create_dashboard_app
from databricks_agents.dashboard.cli import main as cli_main


# --- Fixtures -------------------------------------------------------------

FAKE_AGENTS = [
    DiscoveredAgent(
        name="research_agent",
        endpoint_url="https://research.example.com",
        app_name="research-app",
        description="Does research",
        capabilities="search,analysis",
        protocol_version="a2a/1.0",
    ),
    DiscoveredAgent(
        name="data_agent",
        endpoint_url="https://data.example.com",
        app_name="data-app",
        description="Queries data",
        capabilities="sql",
        protocol_version="a2a/1.0",
    ),
]

FAKE_CARD = {
    "name": "research_agent",
    "description": "Does research",
    "capabilities": ["search", "analysis"],
    "protocolVersion": "a2a/1.0",
    "skills": [
        {"name": "web_search", "description": "Search the web"},
        {"name": "summarize", "description": "Summarize documents"},
    ],
}


@pytest.fixture
def scanner():
    """DashboardScanner pre-loaded with fake agents (no workspace call)."""
    s = DashboardScanner.__new__(DashboardScanner)
    s._discovery = MagicMock()
    s._agents = list(FAKE_AGENTS)
    s._scan_lock = __import__("asyncio").Lock()
    s._scanned = True

    # Mock scan() for lifespan startup handler
    async def _mock_scan():
        return list(FAKE_AGENTS)
    s.scan = _mock_scan

    return s


@pytest.fixture
def dashboard_client(scanner):
    """FastAPI TestClient wired to a pre-loaded scanner."""
    app = create_dashboard_app(scanner, profile="test-profile", auto_scan_interval=0)
    return TestClient(app)


# --- DashboardScanner tests -----------------------------------------------


@pytest.mark.asyncio
async def test_scan_populates_cache():
    """scan() calls discover_agents and caches results."""
    scanner = DashboardScanner.__new__(DashboardScanner)
    scanner._agents = []
    scanner._scan_lock = __import__("asyncio").Lock()
    scanner._scanned = False

    mock_discovery = AsyncMock()
    mock_discovery.discover_agents.return_value = MagicMock(
        agents=FAKE_AGENTS, errors=[]
    )
    scanner._discovery = mock_discovery

    result = await scanner.scan()

    assert len(result) == 2
    assert scanner.get_agents() == list(FAKE_AGENTS)
    mock_discovery.discover_agents.assert_awaited_once()


@pytest.mark.asyncio
async def test_scan_returns_cached_on_get():
    """get_agents() returns cache without re-scanning."""
    scanner = DashboardScanner.__new__(DashboardScanner)
    scanner._agents = list(FAKE_AGENTS)
    scanner._scan_lock = __import__("asyncio").Lock()
    scanner._scanned = True
    scanner._discovery = MagicMock()

    agents = scanner.get_agents()
    assert len(agents) == 2
    scanner._discovery.discover_agents.assert_not_called()


def test_get_agent_by_name(scanner):
    """Look up agents by name or app_name."""
    assert scanner.get_agent_by_name("research_agent") is not None
    assert scanner.get_agent_by_name("research-app") is not None
    assert scanner.get_agent_by_name("nonexistent") is None


@pytest.mark.asyncio
async def test_get_agent_card(scanner):
    """get_agent_card fetches via A2AClient."""
    with patch("databricks_agents.dashboard.scanner.A2AClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.fetch_agent_card = AsyncMock(return_value=FAKE_CARD)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        card = await scanner.get_agent_card("https://research.example.com")

    assert card["name"] == "research_agent"
    assert len(card["skills"]) == 2


@pytest.mark.asyncio
async def test_proxy_mcp(scanner):
    """proxy_mcp forwards JSON-RPC to agent's /api/mcp endpoint."""
    scanner._discovery._workspace_token = "test-token"

    mcp_response = {"jsonrpc": "2.0", "id": "1", "result": {"tools": []}}

    with patch("databricks_agents.dashboard.scanner.httpx.AsyncClient") as mock_http_cls:
        mock_http = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = mcp_response
        mock_resp.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await scanner.proxy_mcp(
            "https://research.example.com",
            {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
        )

    assert result == mcp_response
    mock_http.post.assert_awaited_once()
    call_url = mock_http.post.call_args[0][0]
    assert call_url == "https://research.example.com/api/mcp"


# --- FastAPI route tests --------------------------------------------------


def test_index_returns_spa(dashboard_client):
    """GET / returns 200 with React SPA index.html."""
    resp = dashboard_client.get("/")
    assert resp.status_code == 200
    assert "<!DOCTYPE html>" in resp.text
    assert '<div id="root">' in resp.text


def test_spa_catch_all_returns_index(dashboard_client):
    """GET /agent/{name} returns 200 with SPA (client-side routing)."""
    resp = dashboard_client.get("/agent/research_agent")
    assert resp.status_code == 200
    assert '<div id="root">' in resp.text


def test_spa_catch_all_nonexistent(dashboard_client):
    """GET for unknown route returns 200 with SPA (React handles 404)."""
    resp = dashboard_client.get("/agent/nonexistent")
    assert resp.status_code == 200
    assert '<div id="root">' in resp.text


def test_api_agents(dashboard_client):
    """GET /api/agents returns JSON agent list."""
    resp = dashboard_client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "research_agent"


def test_api_agent_card(dashboard_client, scanner):
    """GET /api/agents/{name}/card returns card JSON."""
    with patch.object(scanner, "get_agent_card", new_callable=AsyncMock) as mock_card:
        mock_card.return_value = FAKE_CARD
        resp = dashboard_client.get("/api/agents/research_agent/card")

    assert resp.status_code == 200
    assert resp.json()["name"] == "research_agent"


def test_api_agent_card_not_found(dashboard_client):
    """GET /api/agents/{name}/card returns 404 for unknown agent."""
    resp = dashboard_client.get("/api/agents/nonexistent/card")
    assert resp.status_code == 404


def test_api_mcp_proxy(dashboard_client, scanner):
    """POST /api/agents/{name}/mcp proxies to agent's MCP endpoint."""
    mcp_response = {"jsonrpc": "2.0", "id": "1", "result": {"tools": []}}
    with patch.object(scanner, "proxy_mcp", new_callable=AsyncMock) as mock_mcp:
        mock_mcp.return_value = mcp_response
        resp = dashboard_client.post(
            "/api/agents/research_agent/mcp",
            json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
        )

    assert resp.status_code == 200
    assert resp.json() == mcp_response


def test_api_mcp_proxy_not_found(dashboard_client):
    """POST /api/agents/{name}/mcp returns 404 for unknown agent."""
    resp = dashboard_client.post(
        "/api/agents/nonexistent/mcp",
        json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 404


def test_api_scan(dashboard_client, scanner):
    """POST /api/scan triggers rescan and returns count."""
    with patch.object(scanner, "scan", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = FAKE_AGENTS
        resp = dashboard_client.post("/api/scan")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2


def test_health(dashboard_client):
    """GET /health returns status and profile."""
    resp = dashboard_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["agents_cached"] == 2
    assert data["profile"] == "test-profile"


# --- CLI argument parsing -------------------------------------------------


def test_cli_help(capsys):
    """CLI --help exits cleanly."""
    with pytest.raises(SystemExit) as exc:
        import sys
        sys.argv = ["databricks-agents", "dashboard", "--help"]
        cli_main()
    assert exc.value.code == 0


def test_cli_no_command(capsys):
    """CLI with no subcommand prints help and exits."""
    import sys
    sys.argv = ["databricks-agents"]
    with pytest.raises(SystemExit) as exc:
        cli_main()
    assert exc.value.code == 1
