"""Tests for AgentDiscovery — workspace agent scanning."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass

from databricks_agents.discovery.agent_discovery import (
    AgentDiscovery,
    DiscoveredAgent,
)


@dataclass
class _FakeApp:
    """Minimal stand-in for a Databricks SDK App object."""
    name: str
    url: str = ""
    creator: str = "user@example.com"
    updater: str = "user@example.com"
    compute_status: object = None
    active_deployment: object = None


@dataclass
class _FakeComputeStatus:
    state: str = "ACTIVE"


@dataclass
class _FakeDeploymentStatus:
    state: str = "SUCCEEDED"


@dataclass
class _FakeDeployment:
    status: object = None


def _make_running_app(name, url):
    """Create a fake app that looks ACTIVE/SUCCEEDED."""
    return _FakeApp(
        name=name,
        url=url,
        compute_status=_FakeComputeStatus(state="ACTIVE"),
        active_deployment=_FakeDeployment(
            status=_FakeDeploymentStatus(state="SUCCEEDED"),
        ),
    )


def _make_stopped_app(name):
    """Create a fake app with no URL / stopped compute."""
    return _FakeApp(
        name=name,
        url="",
        compute_status=_FakeComputeStatus(state="STOPPED"),
    )


AGENT_CARD = {
    "name": "research_agent",
    "description": "Does research",
    "capabilities": ["search", "analysis"],
    "protocolVersion": "a2a/1.0",
}


# --- discover_agents ---


@pytest.mark.asyncio
async def test_discover_agents_finds_agent():
    """Discovers an agent from a running app with a valid agent card."""
    discovery = AgentDiscovery()

    with patch.object(discovery, "_list_workspace_apps", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            {"name": "research-app", "url": "https://research.example.com", "compute_state": "ACTIVE", "deploy_state": "SUCCEEDED"},
        ]

        with patch.object(discovery, "_probe_app_for_agent", new_callable=AsyncMock) as mock_probe:
            mock_probe.return_value = DiscoveredAgent(
                name="research_agent",
                endpoint_url="https://research.example.com",
                app_name="research-app",
                description="Does research",
                capabilities="search,analysis",
                protocol_version="a2a/1.0",
            )

            result = await discovery.discover_agents()

    assert len(result.agents) == 1
    assert result.agents[0].name == "research_agent"
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_discover_agents_empty_workspace():
    """Returns empty result for a workspace with no apps."""
    discovery = AgentDiscovery()

    with patch.object(discovery, "_list_workspace_apps", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        result = await discovery.discover_agents()

    assert result.agents == []
    assert result.errors == []


@pytest.mark.asyncio
async def test_discover_agents_listing_failure():
    """Returns error when workspace listing fails."""
    discovery = AgentDiscovery()

    with patch.object(discovery, "_list_workspace_apps", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = RuntimeError("Permission denied")
        result = await discovery.discover_agents()

    assert result.agents == []
    assert len(result.errors) == 1
    assert "Permission denied" in result.errors[0]


@pytest.mark.asyncio
async def test_discover_agents_skip_no_url():
    """Apps without a URL are skipped during probing."""
    discovery = AgentDiscovery()

    with patch.object(discovery, "_list_workspace_apps", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            {"name": "no-url-app", "compute_state": "ACTIVE", "deploy_state": "SUCCEEDED"},
        ]

        result = await discovery.discover_agents()

    assert result.agents == []


@pytest.mark.asyncio
async def test_discover_agents_probe_returns_none():
    """Non-agent apps (probe returns None) are filtered out."""
    discovery = AgentDiscovery()

    with patch.object(discovery, "_list_workspace_apps", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            {"name": "webapp", "url": "https://webapp.example.com", "compute_state": "ACTIVE", "deploy_state": "SUCCEEDED"},
        ]

        with patch.object(discovery, "_probe_app_for_agent", new_callable=AsyncMock) as mock_probe:
            mock_probe.return_value = None
            result = await discovery.discover_agents()

    assert result.agents == []


# --- capabilities parsing ---


@pytest.mark.asyncio
async def test_probe_parses_dict_capabilities():
    """Capabilities as dict keys are extracted correctly."""
    discovery = AgentDiscovery()
    discovery._workspace_token = "fake-token"

    card_with_dict_caps = {
        "name": "agent",
        "description": "test",
        "capabilities": {"streaming": True, "pushNotifications": False},
    }

    with patch("databricks_agents.discovery.agent_discovery.A2AClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.fetch_agent_card = AsyncMock(return_value=card_with_dict_caps)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await discovery._probe_app_for_agent(
            {"name": "app", "url": "https://app.example.com"}
        )

    assert result is not None
    assert "streaming" in result.capabilities
    assert "pushNotifications" in result.capabilities


@pytest.mark.asyncio
async def test_probe_parses_list_capabilities():
    """Capabilities as list are joined with commas."""
    discovery = AgentDiscovery()
    discovery._workspace_token = "fake-token"

    card_with_list_caps = {
        "name": "agent",
        "description": "test",
        "capabilities": ["search", "analysis"],
    }

    with patch("databricks_agents.discovery.agent_discovery.A2AClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.fetch_agent_card = AsyncMock(return_value=card_with_list_caps)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await discovery._probe_app_for_agent(
            {"name": "app", "url": "https://app.example.com"}
        )

    assert result is not None
    assert result.capabilities == "search,analysis"
