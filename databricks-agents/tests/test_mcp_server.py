"""Tests for MCP server — works with plain FastAPI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from dbx_agent_app.mcp import MCPServerConfig, setup_mcp_server


def _make_mcp_app():
    """Create a plain FastAPI app with MCP endpoints via setup_mcp_server."""
    app = FastAPI()

    async def echo(text: str) -> dict:
        return {"echo": text}

    tools = [
        {
            "name": "echo",
            "description": "Echo back the input",
            "parameters": {"text": {"type": "string", "required": True}},
            "function": echo,
        }
    ]

    config = MCPServerConfig(name="test_mcp", description="Test MCP server")
    setup_mcp_server(tools, config=config, fastapi_app=app)

    return app


# --- tools/list ---


def test_mcp_tools_list():
    """tools/list returns all registered tools in MCP format."""
    client = TestClient(_make_mcp_app())

    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "1"

    tools = data["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"
    assert tools[0]["description"] == "Echo back the input"
    assert "inputSchema" in tools[0]


def test_mcp_tools_list_empty():
    """tools/list returns empty list when no tools registered."""
    app = FastAPI()
    config = MCPServerConfig(name="empty")
    setup_mcp_server([], config=config, fastapi_app=app)

    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )

    assert response.status_code == 200
    assert response.json()["result"]["tools"] == []


# --- tools/call ---


def test_mcp_tools_call_success():
    """tools/call executes a tool and returns the result."""
    client = TestClient(_make_mcp_app())

    response = client.post(
        "/api/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hello"}},
            "id": "2",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"]["result"]["echo"] == "hello"


def test_mcp_tools_call_not_found():
    """tools/call with unknown tool name returns error."""
    client = TestClient(_make_mcp_app())

    response = client.post(
        "/api/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "nonexistent", "arguments": {}},
            "id": "3",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32603


# --- server/info ---


def test_mcp_server_info():
    """server/info returns server metadata."""
    client = TestClient(_make_mcp_app())

    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "server/info", "id": "4"},
    )

    assert response.status_code == 200
    data = response.json()
    info = data["result"]
    assert info["name"] == "test_mcp"
    assert "version" in info
    assert "protocol_version" in info


# --- unknown method ---


def test_mcp_unknown_method():
    """Unknown JSON-RPC method returns -32601 error."""
    client = TestClient(_make_mcp_app())

    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "unknown/method", "id": "5"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"]["code"] == -32601
    assert "unknown/method" in data["error"]["message"]


# --- GET /api/mcp/tools ---


def test_mcp_tools_get_endpoint():
    """GET /api/mcp/tools returns tool list."""
    client = TestClient(_make_mcp_app())

    response = client.get("/api/mcp/tools")

    assert response.status_code == 200
    tools = response.json()["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"
