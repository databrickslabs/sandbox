"""Tests for add_agent_card() and add_mcp_endpoints() helpers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from databricks_agents import add_agent_card, add_mcp_endpoints


# ===================================================================
# Tests for add_agent_card()
# ===================================================================


def test_agent_card_endpoint(plain_client):
    """add_agent_card() creates a working /.well-known/agent.json."""
    response = plain_client.get("/.well-known/agent.json")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "test_agent"
    assert data["description"] == "Test agent"
    assert data["capabilities"] == ["test"]
    assert data["schema_version"] == "a2a/1.0"
    assert data["endpoints"]["invocations"] == "/invocations"


def test_health_endpoint(plain_client):
    """add_agent_card() also adds /health."""
    response = plain_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["agent"] == "test_agent"


def test_agent_card_with_tools():
    """Tools metadata appears in the agent card."""
    app = FastAPI()
    add_agent_card(
        app,
        name="tooled",
        description="Agent with tools",
        capabilities=["test"],
        tools=[
            {"name": "search", "description": "Search things", "parameters": {"q": {"type": "string"}}},
        ],
    )

    client = TestClient(app)
    data = client.get("/.well-known/agent.json").json()

    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "search"


def test_agent_card_custom_version():
    """Version parameter is reflected in the card."""
    app = FastAPI()
    add_agent_card(app, name="v2", description="V2", capabilities=[], version="2.0.0")

    client = TestClient(app)
    data = client.get("/.well-known/agent.json").json()
    assert data["version"] == "2.0.0"


# ===================================================================
# Tests for add_mcp_endpoints()
# ===================================================================


def test_mcp_tools_list(mcp_client):
    """MCP tools/list returns registered tools."""
    response = mcp_client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"
    assert "inputSchema" in tools[0]


def test_mcp_tools_call(mcp_client):
    """MCP tools/call executes a tool."""
    response = mcp_client.post(
        "/api/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hello"}},
            "id": "2",
        },
    )
    assert response.status_code == 200
    result = response.json()["result"]["result"]
    assert result["echo"] == "hello"


def test_mcp_server_info(mcp_client):
    """MCP server/info returns metadata."""
    response = mcp_client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "server/info", "id": "3"},
    )
    assert response.status_code == 200
    info = response.json()["result"]
    assert "name" in info
    assert "protocol_version" in info


def test_mcp_unknown_method(mcp_client):
    """Unknown JSON-RPC method returns -32601."""
    response = mcp_client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "unknown/method", "id": "4"},
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32601


def test_mcp_tool_not_found(mcp_client):
    """Calling nonexistent tool returns -32603."""
    response = mcp_client.post(
        "/api/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "nonexistent", "arguments": {}},
            "id": "5",
        },
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32603


def test_mcp_get_tools_endpoint(mcp_client):
    """GET /api/mcp/tools returns tool list."""
    response = mcp_client.get("/api/mcp/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"


def test_no_mcp_without_add():
    """Without add_mcp_endpoints(), /api/mcp doesn't exist."""
    app = FastAPI()
    add_agent_card(app, name="no_mcp", description="No MCP", capabilities=[])

    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    assert response.status_code in (404, 405)


def test_mcp_multiple_tools():
    """Multiple tools all appear in MCP tools/list."""
    app = FastAPI()

    async def tool_a(x: str) -> dict:
        return {"a": x}

    async def tool_b(y: int) -> dict:
        return {"b": y}

    tools = [
        {"name": "tool_a", "description": "First", "function": tool_a, "parameters": {"x": {"type": "string", "required": True}}},
        {"name": "tool_b", "description": "Second", "function": tool_b, "parameters": {"y": {"type": "integer", "required": True}}},
    ]
    add_mcp_endpoints(app, tools=tools)

    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    mcp_tools = response.json()["result"]["tools"]
    assert len(mcp_tools) == 2
    names = {t["name"] for t in mcp_tools}
    assert names == {"tool_a", "tool_b"}
