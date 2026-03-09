"""Tests for @app_agent decorator and AppAgent class."""

import json

import pytest
from fastapi.testclient import TestClient

from dbx_agent_app import app_agent, AgentRequest, AgentResponse, StreamEvent, UserContext
from dbx_agent_app.core.app_agent import AppAgent


# ===================================================================
# Helper: create a basic agent
# ===================================================================


def _make_echo_agent(**kwargs):
    """Create a simple echo agent for testing."""

    @app_agent(
        name=kwargs.get("name", "echo"),
        description=kwargs.get("description", "Echo agent"),
        capabilities=kwargs.get("capabilities", ["test"]),
        enable_mcp=kwargs.get("enable_mcp", False),
    )
    async def echo(request: AgentRequest) -> AgentResponse:
        return AgentResponse.text(f"Echo: {request.last_user_message}")

    return echo


# ===================================================================
# Basic agent creation
# ===================================================================


def test_decorator_returns_app_agent():
    """@app_agent returns an AppAgent instance."""
    agent = _make_echo_agent()
    assert isinstance(agent, AppAgent)
    assert agent.name == "echo"
    assert agent.description == "Echo agent"
    assert agent.capabilities == ["test"]


def test_app_property_returns_fastapi():
    """agent.app returns a FastAPI instance."""
    from fastapi import FastAPI

    agent = _make_echo_agent()
    assert isinstance(agent.app, FastAPI)


def test_app_property_is_cached():
    """agent.app returns the same instance on subsequent calls."""
    agent = _make_echo_agent()
    assert agent.app is agent.app


# ===================================================================
# /invocations endpoint
# ===================================================================


def test_invocations_basic():
    """/invocations returns correct wire format."""
    agent = _make_echo_agent()
    client = TestClient(agent.app)

    response = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200

    data = response.json()
    assert "output" in data
    assert data["output"][0]["type"] == "message"
    assert data["output"][0]["content"][0]["text"] == "Echo: hello"


def test_invocations_no_user_message():
    """/invocations returns 400 when no user message in input."""
    agent = _make_echo_agent()
    client = TestClient(agent.app)

    response = client.post(
        "/invocations",
        json={"input": [{"role": "system", "content": "prompt"}]},
    )
    assert response.status_code == 400


def test_invocations_empty_input():
    """/invocations returns 400 for empty input."""
    agent = _make_echo_agent()
    client = TestClient(agent.app)

    response = client.post("/invocations", json={"input": []})
    assert response.status_code == 400


# ===================================================================
# Return type coercion
# ===================================================================


def test_string_return_coercion():
    """Handler returning a string is auto-wrapped."""

    @app_agent(name="str", description="str agent", capabilities=[])
    async def str_agent(request: AgentRequest) -> str:
        return "plain string"

    client = TestClient(str_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "go"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["output"][0]["content"][0]["text"] == "plain string"


def test_dict_return_coercion():
    """Handler returning a dict is auto-wrapped via from_dict."""

    @app_agent(name="dict", description="dict agent", capabilities=[])
    async def dict_agent(request: AgentRequest) -> dict:
        return {"response": "from dict"}

    client = TestClient(dict_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "go"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["output"][0]["content"][0]["text"] == "from dict"


def test_dict_without_response_key():
    """Dict without 'response' key gets JSON-serialized."""

    @app_agent(name="raw", description="raw dict", capabilities=[])
    async def raw_agent(request: AgentRequest) -> dict:
        return {"foo": "bar"}

    client = TestClient(raw_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "go"}]},
    )
    text = resp.json()["output"][0]["content"][0]["text"]
    assert json.loads(text) == {"foo": "bar"}


# ===================================================================
# Agent card and health
# ===================================================================


def test_agent_card():
    """/.well-known/agent.json returns correct metadata."""
    agent = _make_echo_agent()
    client = TestClient(agent.app)

    resp = client.get("/.well-known/agent.json")
    assert resp.status_code == 200

    data = resp.json()
    assert data["name"] == "echo"
    assert data["schema_version"] == "a2a/1.0"
    assert data["endpoints"]["invocations"] == "/invocations"


def test_health():
    """/health returns healthy status."""
    agent = _make_echo_agent()
    client = TestClient(agent.app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["agent"] == "echo"


# ===================================================================
# Tool registration
# ===================================================================


def test_tool_registration():
    """@agent.tool() registers tools visible in agent card."""
    agent = _make_echo_agent(enable_mcp=False)

    @agent.tool(description="Search things")
    async def search(query: str) -> dict:
        return {"results": [query]}

    client = TestClient(agent.app)
    card = client.get("/.well-known/agent.json").json()

    assert len(card["tools"]) == 1
    assert card["tools"][0]["name"] == "search"
    assert card["tools"][0]["description"] == "Search things"


def test_tool_endpoint():
    """Registered tools get /api/tools/<name> endpoints."""
    agent = _make_echo_agent(enable_mcp=False)

    @agent.tool(description="Echo tool")
    async def my_tool(text: str) -> dict:
        return {"echo": text}

    client = TestClient(agent.app)
    # FastAPI treats bare str params as query params
    resp = client.post("/api/tools/my_tool?text=hello")
    assert resp.status_code == 200
    assert resp.json()["echo"] == "hello"


# ===================================================================
# Direct call (testing without HTTP)
# ===================================================================


@pytest.mark.asyncio
async def test_direct_call():
    """agent(request) calls handler directly."""
    agent = _make_echo_agent()
    req = AgentRequest(input=[{"role": "user", "content": "direct"}])

    result = await agent(req)
    assert isinstance(result, AgentResponse)
    assert result.output[0].content[0].text == "Echo: direct"


# ===================================================================
# MCP integration
# ===================================================================


# ===================================================================
# User context header extraction
# ===================================================================


def test_invocations_extracts_user_context():
    """/invocations populates user_context from X-Forwarded-* headers."""
    captured = {}

    @app_agent(
        name="auth_test",
        description="Auth test",
        capabilities=[],
    )
    async def auth_agent(request: AgentRequest) -> AgentResponse:
        captured["user_context"] = request.user_context
        return AgentResponse.text("ok")

    client = TestClient(auth_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "test"}]},
        headers={
            "X-Forwarded-Access-Token": "user-token-123",
            "X-Forwarded-Email": "alice@example.com",
            "X-Forwarded-User": "alice",
        },
    )
    assert resp.status_code == 200

    ctx = captured["user_context"]
    assert ctx is not None
    assert ctx.access_token == "user-token-123"
    assert ctx.email == "alice@example.com"
    assert ctx.user == "alice"
    assert ctx.is_authenticated is True


def test_invocations_no_headers_means_no_user_context():
    """/invocations without X-Forwarded-* headers leaves user_context as None."""
    captured = {}

    @app_agent(
        name="no_auth",
        description="No auth",
        capabilities=[],
    )
    async def no_auth_agent(request: AgentRequest) -> AgentResponse:
        captured["user_context"] = request.user_context
        return AgentResponse.text("ok")

    client = TestClient(no_auth_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "test"}]},
    )
    assert resp.status_code == 200
    assert captured["user_context"] is None


def test_invocations_partial_headers():
    """/invocations with only email header still creates UserContext."""
    captured = {}

    @app_agent(
        name="partial",
        description="Partial",
        capabilities=[],
    )
    async def partial_agent(request: AgentRequest) -> AgentResponse:
        captured["user_context"] = request.user_context
        return AgentResponse.text("ok")

    client = TestClient(partial_agent.app)
    resp = client.post(
        "/invocations",
        json={"input": [{"role": "user", "content": "test"}]},
        headers={"X-Forwarded-Email": "bob@example.com"},
    )
    assert resp.status_code == 200

    ctx = captured["user_context"]
    assert ctx is not None
    assert ctx.email == "bob@example.com"
    assert ctx.access_token is None
    assert ctx.is_authenticated is False


# ===================================================================
# MCP integration
# ===================================================================


def test_mcp_with_tools():
    """MCP endpoints are added when enable_mcp=True and tools exist."""

    @app_agent(
        name="mcp_test",
        description="MCP test",
        capabilities=[],
        enable_mcp=True,
    )
    async def mcp_agent(request: AgentRequest) -> str:
        return "ok"

    @mcp_agent.tool(description="Search")
    async def search(query: str) -> dict:
        return {"results": [query]}

    client = TestClient(mcp_agent.app)

    # Check agent card includes MCP endpoint
    card = client.get("/.well-known/agent.json").json()
    assert "mcp" in card["endpoints"]

    # Check MCP tools/list works
    resp = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": "1"},
    )
    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "search"
