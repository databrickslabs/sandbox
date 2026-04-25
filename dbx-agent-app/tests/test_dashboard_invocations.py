"""Tests for dashboard /api/agents/{name}/test endpoint (invocations proxy)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from dbx_agent_app.dashboard.app import create_dashboard_app
from dbx_agent_app.dashboard.scanner import DashboardScanner
from dbx_agent_app.discovery import DiscoveredAgent


@pytest.fixture
def mock_scanner():
    """DashboardScanner with a fake agent and mocked call_invocations."""
    scanner = MagicMock(spec=DashboardScanner)

    fake_agent = DiscoveredAgent(
        name="test_agent",
        endpoint_url="https://fake-agent.example.com",
        app_name="test-agent-app",
        description="Test agent",
        capabilities=["test"],
    )

    scanner.get_agents.return_value = [fake_agent]
    scanner.get_agent_by_name.side_effect = lambda name: fake_agent if name in ("test_agent", "test-agent-app") else None

    scanner.call_invocations = AsyncMock(return_value={
        "parts": [{"text": "Hello from /invocations!"}],
        "_trace": {
            "protocol": "invocations",
            "latency_ms": 150.0,
        },
    })

    # Disable auto-scan by not providing a real scan method
    scanner.scan = AsyncMock(return_value=[fake_agent])

    return scanner


@pytest.fixture
def dashboard_client(mock_scanner):
    """TestClient for the dashboard app with mocked scanner."""
    app = create_dashboard_app(mock_scanner, auto_scan_interval=0)
    return TestClient(app)


def test_test_endpoint_success(dashboard_client, mock_scanner):
    """POST /api/agents/{name}/test calls agent via /invocations."""
    response = dashboard_client.post(
        "/api/agents/test_agent/test",
        json={"message": "hello"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"]["parts"][0]["text"] == "Hello from /invocations!"
    assert data["result"]["_trace"]["protocol"] == "invocations"

    mock_scanner.call_invocations.assert_called_once_with(
        "https://fake-agent.example.com", "hello"
    )


def test_test_endpoint_agent_not_found(dashboard_client):
    """POST /api/agents/{name}/test returns 404 for unknown agent."""
    response = dashboard_client.post(
        "/api/agents/nonexistent/test",
        json={"message": "hello"},
    )

    assert response.status_code == 404


def test_test_endpoint_proxy_error(dashboard_client, mock_scanner):
    """POST /api/agents/{name}/test returns 502 on proxy failure."""
    mock_scanner.call_invocations = AsyncMock(side_effect=Exception("Connection refused"))

    response = dashboard_client.post(
        "/api/agents/test_agent/test",
        json={"message": "hello"},
    )

    assert response.status_code == 502
    assert "Connection refused" in response.json()["error"]
