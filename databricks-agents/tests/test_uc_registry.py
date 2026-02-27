"""Tests for UCAgentRegistry — Unity Catalog agent registration."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from databricks_agents.registry.uc_registry import (
    UCAgentRegistry,
    UCAgentSpec,
    UCRegistrationError,
)


@dataclass
class _FakeTag:
    key: str
    value: str


@dataclass
class _FakeModel:
    name: str = "main.agents.test_agent"
    comment: str = "A test agent"


@pytest.fixture
def registry():
    """UCAgentRegistry with a mocked WorkspaceClient."""
    reg = UCAgentRegistry()
    mock_client = MagicMock()
    reg._client = mock_client
    return reg, mock_client


@pytest.fixture
def agent_spec():
    """Standard agent spec for tests."""
    return UCAgentSpec(
        name="test_agent",
        catalog="main",
        schema="agents",
        endpoint_url="https://app.example.com",
        description="A test agent",
        capabilities=["search", "analysis"],
    )


# --- register_agent ---


def test_register_agent_creates_new(registry, agent_spec):
    """Creates a new registered model when agent doesn't exist."""
    reg, client = registry

    # Catalog and schema exist
    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.return_value = MagicMock()

    # Model doesn't exist — force creation path
    client.registered_models.get.side_effect = Exception("Not found")
    client.registered_models.create.return_value = _FakeModel()
    client.registered_models.set_tag.return_value = None

    result = reg.register_agent(agent_spec)

    assert result["full_name"] == "main.agents.test_agent"
    assert result["endpoint_url"] == "https://app.example.com"
    client.registered_models.create.assert_called_once()


def test_register_agent_updates_existing(registry, agent_spec):
    """Updates metadata when agent already exists."""
    reg, client = registry

    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.return_value = MagicMock()

    # Model already exists
    client.registered_models.get.return_value = _FakeModel()
    client.registered_models.update.return_value = MagicMock()
    client.registered_models.set_tag.return_value = None

    result = reg.register_agent(agent_spec)

    assert result["full_name"] == "main.agents.test_agent"
    client.registered_models.update.assert_called_once()
    # Should not try to create
    client.registered_models.create.assert_not_called()


def test_register_agent_sets_tags(registry, agent_spec):
    """Sets property tags including the databricks_agent marker."""
    reg, client = registry

    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.return_value = MagicMock()
    client.registered_models.get.side_effect = Exception("Not found")
    client.registered_models.create.return_value = _FakeModel()
    client.registered_models.set_tag.return_value = None

    reg.register_agent(agent_spec)

    tag_calls = client.registered_models.set_tag.call_args_list
    tag_keys = {call.kwargs.get("key", call[1].get("key", "")) for call in tag_calls}

    # Should include standard tags
    assert "databricks_agent" in tag_keys
    assert "endpoint_url" in tag_keys
    assert "agent_card_url" in tag_keys


def test_register_agent_catalog_not_found(registry, agent_spec):
    """Raises UCRegistrationError when catalog doesn't exist."""
    reg, client = registry

    client.catalogs.get.side_effect = Exception("Catalog not found")

    with pytest.raises(UCRegistrationError, match="does not exist"):
        reg.register_agent(agent_spec)


def test_register_agent_schema_not_found(registry, agent_spec):
    """Raises UCRegistrationError when schema doesn't exist."""
    reg, client = registry

    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.side_effect = Exception("Schema not found")

    with pytest.raises(UCRegistrationError, match="does not exist"):
        reg.register_agent(agent_spec)


# --- get_agent ---


def test_get_agent_found(registry):
    """Returns agent metadata when found with databricks_agent tag."""
    reg, client = registry

    client.registered_models.get.return_value = _FakeModel(
        name="main.agents.research",
        comment="Research agent",
    )
    client.registered_models.list_tags.return_value = [
        _FakeTag("databricks_agent", "true"),
        _FakeTag("endpoint_url", "https://app.example.com"),
        _FakeTag("capabilities", "search,analysis"),
    ]

    result = reg.get_agent("main", "agents", "research")

    assert result is not None
    assert result["full_name"] == "main.agents.research"
    assert result["endpoint_url"] == "https://app.example.com"
    assert result["capabilities"] == ["search", "analysis"]


def test_get_agent_not_an_agent(registry):
    """Returns None for a model without the databricks_agent tag."""
    reg, client = registry

    client.registered_models.get.return_value = _FakeModel()
    client.registered_models.list_tags.return_value = [
        _FakeTag("some_other_tag", "value"),
    ]

    result = reg.get_agent("main", "agents", "test_agent")
    assert result is None


def test_get_agent_not_found(registry):
    """Returns None when the model doesn't exist."""
    reg, client = registry

    client.registered_models.get.side_effect = Exception("Not found")

    result = reg.get_agent("main", "agents", "nonexistent")
    assert result is None


# --- list_agents ---


def test_list_agents_filters_by_tag(registry):
    """Only returns models tagged as databricks_agent."""
    reg, client = registry

    model_a = _FakeModel(name="main.agents.agent_a", comment="Agent A")
    model_b = _FakeModel(name="main.agents.not_agent", comment="Regular model")

    client.registered_models.list.return_value = [model_a, model_b]

    # agent_a has the tag, not_agent doesn't
    def list_tags(full_name):
        if "agent_a" in full_name:
            return [_FakeTag("databricks_agent", "true"), _FakeTag("endpoint_url", "https://a.com")]
        return [_FakeTag("other", "value")]

    client.registered_models.list_tags.side_effect = lambda fn: list_tags(fn)

    agents = reg.list_agents("main", schema="agents")

    assert len(agents) == 1
    assert agents[0]["name"] == "agent_a"


def test_list_agents_empty(registry):
    """Returns empty list when no agents found."""
    reg, client = registry

    client.registered_models.list.return_value = []

    agents = reg.list_agents("main")
    assert agents == []


# --- delete_agent ---


def test_delete_agent_success(registry):
    """Returns True when agent is deleted."""
    reg, client = registry

    client.registered_models.delete.return_value = None

    result = reg.delete_agent("main", "agents", "old_agent")
    assert result is True
    client.registered_models.delete.assert_called_once_with("main.agents.old_agent")


def test_delete_agent_not_found(registry):
    """Returns False when agent doesn't exist."""
    reg, client = registry

    client.registered_models.delete.side_effect = Exception("does not exist")

    result = reg.delete_agent("main", "agents", "missing")
    assert result is False


def test_delete_agent_other_error(registry):
    """Raises UCRegistrationError on unexpected errors."""
    reg, client = registry

    client.registered_models.delete.side_effect = Exception("Permission denied")

    with pytest.raises(UCRegistrationError, match="Permission denied"):
        reg.delete_agent("main", "agents", "locked_agent")
