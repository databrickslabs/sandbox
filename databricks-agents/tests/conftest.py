"""Shared test fixtures for databricks-agents SDK tests."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from databricks_agents import AgentApp


@pytest.fixture
def basic_app():
    """AgentApp with no UC registration and no MCP."""
    return AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
        auto_register=False,
        enable_mcp=False,
    )


@pytest.fixture
def mcp_app():
    """AgentApp with MCP enabled but no UC registration."""
    return AgentApp(
        name="mcp_agent",
        description="MCP test agent",
        capabilities=["test"],
        auto_register=False,
        enable_mcp=True,
    )


@pytest.fixture
def client(basic_app):
    """TestClient for the basic app."""
    return TestClient(basic_app)


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
