"""Tests for UCAgentRegistry — Unity Catalog agent registration."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from databricks_agents.registry.uc_registry import (
    UCAgentRegistry,
    UCAgentSpec,
    UCRegistrationError,
)


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

    # Update fails (model doesn't exist) → falls through to create
    client.registered_models.update.side_effect = Exception("Not found")
    client.registered_models.create.return_value = _FakeModel()

    result = reg.register_agent(agent_spec)

    assert result["full_name"] == "main.agents.test_agent"
    assert result["endpoint_url"] == "https://app.example.com"
    client.registered_models.create.assert_called_once()


def test_register_agent_updates_existing(registry, agent_spec):
    """Updates metadata when agent already exists."""
    reg, client = registry

    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.return_value = MagicMock()

    # Update succeeds (model exists)
    client.registered_models.update.return_value = MagicMock()

    result = reg.register_agent(agent_spec)

    assert result["full_name"] == "main.agents.test_agent"
    client.registered_models.update.assert_called_once()
    # Should not try to create
    client.registered_models.create.assert_not_called()


def test_register_agent_embeds_meta_in_comment(registry, agent_spec):
    """Embeds agent metadata as JSON in the model comment."""
    import json

    reg, client = registry

    client.catalogs.get.return_value = MagicMock()
    client.schemas.get.return_value = MagicMock()
    client.registered_models.update.side_effect = Exception("Not found")
    client.registered_models.create.return_value = _FakeModel()

    reg.register_agent(agent_spec)

    # Verify comment contains ---AGENT_META--- marker with correct keys
    create_call = client.registered_models.create.call_args
    comment = create_call.kwargs.get("comment", create_call[1].get("comment", ""))
    assert "---AGENT_META---" in comment

    meta_json = comment.split("---AGENT_META---")[1].strip()
    meta = json.loads(meta_json)
    assert meta["databricks_agent"] is True
    assert meta["endpoint_url"] == "https://app.example.com"
    assert "agent_card_url" in meta


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
    """Returns agent metadata when comment contains AGENT_META marker."""
    import json

    reg, client = registry

    meta = json.dumps({
        "databricks_agent": True,
        "endpoint_url": "https://app.example.com",
        "capabilities": "search,analysis",
    })
    comment = f"Research agent\n---AGENT_META---\n{meta}"

    client.registered_models.get.return_value = _FakeModel(
        name="main.agents.research",
        comment=comment,
    )

    result = reg.get_agent("main", "agents", "research")

    assert result is not None
    assert result["full_name"] == "main.agents.research"
    assert result["endpoint_url"] == "https://app.example.com"
    assert result["capabilities"] == ["search", "analysis"]
    assert result["description"] == "Research agent"


def test_get_agent_not_an_agent(registry):
    """Returns None for a model without the AGENT_META marker."""
    reg, client = registry

    client.registered_models.get.return_value = _FakeModel(
        comment="Just a regular model, no agent meta"
    )

    result = reg.get_agent("main", "agents", "test_agent")
    assert result is None


def test_get_agent_not_found(registry):
    """Returns None when the model doesn't exist."""
    reg, client = registry

    client.registered_models.get.side_effect = Exception("Not found")

    result = reg.get_agent("main", "agents", "nonexistent")
    assert result is None


# --- list_agents ---


def test_list_agents_filters_by_comment_meta(registry):
    """Only returns models with AGENT_META marker in comment."""
    import json

    reg, client = registry

    agent_meta = json.dumps({"databricks_agent": True, "endpoint_url": "https://a.com"})
    model_a = _FakeModel(
        name="agent_a",
        comment=f"Agent A\n---AGENT_META---\n{agent_meta}",
    )
    # full_name needed by list_agents
    model_a.full_name = "main.agents.agent_a"

    model_b = _FakeModel(name="not_agent", comment="Regular model")
    model_b.full_name = "main.agents.not_agent"

    client.registered_models.list.return_value = [model_a, model_b]

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
