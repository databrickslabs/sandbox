"""Tests for AgentApp core functionality."""

from typing import Dict, List, Optional
from fastapi.testclient import TestClient

from databricks_agents import AgentApp


def test_agent_app_creation(basic_app):
    """Test creating a basic agent app."""
    assert basic_app.agent_metadata.name == "test_agent"
    assert basic_app.agent_metadata.description == "Test agent"
    assert basic_app.agent_metadata.capabilities == ["test"]


def test_agent_card_endpoint(client):
    """Test that agent card endpoint is auto-generated."""
    response = client.get("/.well-known/agent.json")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "test_agent"
    assert data["description"] == "Test agent"
    assert data["capabilities"] == ["test"]
    assert "endpoints" in data
    assert "tools" in data


def test_openid_config_endpoint(client):
    """Test that OIDC configuration endpoint is auto-generated."""
    response = client.get("/.well-known/openid-configuration")

    assert response.status_code == 200
    data = response.json()

    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data


def test_health_endpoint(client):
    """Test that health check endpoint is auto-generated."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["agent"] == "test_agent"


def test_tool_registration(basic_app):
    """Test registering a tool with the agent."""

    @basic_app.tool(description="Test tool")
    async def test_tool(param: str) -> dict:
        return {"result": param}

    assert len(basic_app.agent_metadata.tools) == 1
    tool = basic_app.agent_metadata.tools[0]
    assert tool.name == "test_tool"
    assert tool.description == "Test tool"

    client = TestClient(basic_app)
    # FastAPI treats simple type params as query parameters
    response = client.post("/api/tools/test_tool?param=value")
    assert response.status_code == 200
    assert response.json()["result"] == "value"


def test_tool_in_agent_card(basic_app):
    """Test that tools appear in the agent card."""

    @basic_app.tool(description="Test tool")
    async def test_tool(param: str) -> dict:
        return {"result": param}

    client = TestClient(basic_app)
    response = client.get("/.well-known/agent.json")
    data = response.json()

    assert len(data["tools"]) == 1
    tool = data["tools"][0]
    assert tool["name"] == "test_tool"
    assert tool["description"] == "Test tool"
    assert "parameters" in tool


def test_multiple_tools():
    """Test registering multiple tools."""
    app = AgentApp(
        name="multi",
        description="Multi-tool agent",
        capabilities=["test"],
        auto_register=False,
        enable_mcp=False,
    )

    @app.tool(description="First tool")
    async def tool_a(x: str) -> dict:
        return {"tool": "a", "x": x}

    @app.tool(description="Second tool")
    async def tool_b(y: int) -> dict:
        return {"tool": "b", "y": y}

    assert len(app.agent_metadata.tools) == 2
    names = {t.name for t in app.agent_metadata.tools}
    assert names == {"tool_a", "tool_b"}


# --- Phase 1a validation: generic type annotations ---


def test_tool_with_list_type():
    """List[str] parameter should produce 'array' JSON schema type."""
    app = AgentApp(
        name="t", description="t", capabilities=["t"],
        auto_register=False, enable_mcp=False,
    )

    @app.tool(description="Takes a list")
    async def list_tool(items: List[str]) -> dict:
        return {"count": len(items)}

    param = app.agent_metadata.tools[0].parameters["items"]
    assert param["type"] == "array"


def test_tool_with_optional_type():
    """Optional[int] should produce 'integer' JSON schema type."""
    app = AgentApp(
        name="t", description="t", capabilities=["t"],
        auto_register=False, enable_mcp=False,
    )

    @app.tool(description="Takes optional int")
    async def opt_tool(count: Optional[int] = None) -> dict:
        return {"count": count}

    param = app.agent_metadata.tools[0].parameters["count"]
    assert param["type"] == "integer"
    assert param["required"] is False


def test_tool_with_dict_type():
    """Dict[str, Any] should produce 'object' JSON schema type."""
    app = AgentApp(
        name="t", description="t", capabilities=["t"],
        auto_register=False, enable_mcp=False,
    )

    @app.tool(description="Takes a dict")
    async def dict_tool(data: Dict[str, int]) -> dict:
        return data

    param = app.agent_metadata.tools[0].parameters["data"]
    assert param["type"] == "object"


def test_tool_with_explicit_parameters():
    """Explicit parameter schema should be used when provided."""
    app = AgentApp(
        name="t", description="t", capabilities=["t"],
        auto_register=False, enable_mcp=False,
    )

    custom_params = {
        "query": {"type": "string", "required": True, "description": "Search query"},
    }

    @app.tool(description="Explicit params", parameters=custom_params)
    async def search(query: str) -> dict:
        return {"q": query}

    assert app.agent_metadata.tools[0].parameters == custom_params


def test_tool_with_no_annotation():
    """Unannotated parameter defaults to 'string'."""
    app = AgentApp(
        name="t", description="t", capabilities=["t"],
        auto_register=False, enable_mcp=False,
    )

    @app.tool(description="No annotation")
    async def raw(value) -> dict:
        return {"v": value}

    param = app.agent_metadata.tools[0].parameters["value"]
    assert param["type"] == "string"


# --- MCP toggle ---


def test_mcp_disabled():
    """When enable_mcp=False, /api/mcp should not exist."""
    app = AgentApp(
        name="no_mcp", description="No MCP", capabilities=["test"],
        auto_register=False, enable_mcp=False,
    )
    client = TestClient(app)
    response = client.post("/api/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    assert response.status_code in (404, 405)


def test_mcp_enabled(mcp_client):
    """When enable_mcp=True, /api/mcp should respond."""
    response = mcp_client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data


# --- MCP JSON-RPC via AgentApp ---


def test_mcp_tools_list():
    """MCP tools/list should return registered tools."""
    app = AgentApp(
        name="mcp_test", description="MCP", capabilities=["test"],
        auto_register=False, enable_mcp=True,
    )

    @app.tool(description="Ping tool")
    async def ping(msg: str) -> dict:
        return {"pong": msg}

    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "ping"


def test_mcp_tools_call():
    """MCP tools/call should execute a registered tool."""
    app = AgentApp(
        name="mcp_call", description="MCP", capabilities=["test"],
        auto_register=False, enable_mcp=True,
    )

    @app.tool(description="Echo tool")
    async def echo(text: str) -> dict:
        return {"echo": text}

    client = TestClient(app)
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
    result = response.json()["result"]["result"]
    assert result["echo"] == "hello"


# --- UC auto_register toggle ---


def test_auto_register_false():
    """auto_register=False should not attempt UC registration."""
    # Just verify the app starts without error and no UC code runs
    app = AgentApp(
        name="no_uc", description="No UC", capabilities=["test"],
        auto_register=False, enable_mcp=False,
    )
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
