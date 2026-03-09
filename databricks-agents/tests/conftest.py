"""Shared test fixtures for databricks-agents SDK tests."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from databricks_agents import add_agent_card, add_mcp_endpoints


# --- Helper-based fixtures ---


@pytest.fixture
def plain_app():
    """Plain FastAPI app with agent card (no MCP)."""
    app = FastAPI()
    add_agent_card(
        app,
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    return app


@pytest.fixture
def plain_client(plain_app):
    """TestClient for the plain app with agent card."""
    return TestClient(plain_app)


@pytest.fixture
def mcp_tool():
    """A sample async tool function."""
    async def echo(text: str) -> dict:
        return {"echo": text}

    return {
        "name": "echo",
        "description": "Echo back the input",
        "function": echo,
        "parameters": {
            "text": {"type": "string", "required": True},
        },
    }


@pytest.fixture
def mcp_app(mcp_tool):
    """FastAPI app with agent card + MCP endpoints."""
    app = FastAPI()
    add_agent_card(
        app,
        name="mcp_agent",
        description="MCP test agent",
        capabilities=["test"],
        tools=[{"name": mcp_tool["name"], "description": mcp_tool["description"], "parameters": mcp_tool["parameters"]}],
    )
    add_mcp_endpoints(app, tools=[mcp_tool])
    return app


@pytest.fixture
def mcp_client(mcp_app):
    """TestClient for the MCP-enabled app."""
    return TestClient(mcp_app)


@pytest.fixture
def mock_workspace_client():
    """A mocked databricks.sdk.WorkspaceClient."""
    with patch("databricks.sdk.WorkspaceClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client
