"""Tests for DeployEngine resource setting and permission grants."""

from unittest.mock import MagicMock, patch, call

import pytest

from databricks_agents.deploy.config import (
    AgentSpec,
    AppResourceSpec,
    DatabaseResource,
    DeployConfig,
    JobResource,
    ProjectConfig,
    SecretResource,
    ServingEndpointResource,
    SqlWarehouseResource,
    UCConfig,
    UCSecurableResource,
    WarehouseConfig,
)
from databricks_agents.deploy.engine import DeployEngine


# ===================================================================
# Fixtures
# ===================================================================


def _make_config(agents=None):
    return DeployConfig(
        project=ProjectConfig(name="test-project"),
        uc=UCConfig(catalog="cat", schema_="sch"),
        warehouse=WarehouseConfig(id="wh1"),
        agents=agents or [],
    )


def _make_engine(config, mock_ws=None):
    engine = DeployEngine(config, dry_run=True)
    engine._w = mock_ws or MagicMock()
    return engine


# ===================================================================
# _set_app_resources — builds correct REST payloads
# ===================================================================


def test_set_app_resources_uc_securable():
    agent = AgentSpec(
        name="research",
        source="/tmp",
        resources=[
            AppResourceSpec(
                name="data",
                uc_securable=UCSecurableResource(
                    securable_type="TABLE",
                    securable_full_name="cat.sch.users",
                    permission="SELECT",
                ),
            ),
        ],
    )
    config = _make_config([agent])
    mock_ws = MagicMock()
    engine = _make_engine(config, mock_ws)

    engine._set_app_resources(agent)

    mock_ws.api_client.do.assert_called_once()
    args = mock_ws.api_client.do.call_args
    assert args[0] == ("PATCH", "/api/2.0/apps/test-project-research")
    body = args[1]["body"]
    assert len(body["resources"]) == 1
    res = body["resources"][0]
    assert res["name"] == "data"
    assert res["uc_securable"]["securable_type"] == "TABLE"
    assert res["uc_securable"]["securable_full_name"] == "cat.sch.users"
    assert res["uc_securable"]["permission"] == "SELECT"


def test_set_app_resources_sql_warehouse():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[AppResourceSpec(name="wh", sql_warehouse=SqlWarehouseResource(id="wh1"))],
    )
    config = _make_config([agent])
    engine = _make_engine(config)

    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["sql_warehouse"]["id"] == "wh1"
    assert body["resources"][0]["sql_warehouse"]["permission"] == "CAN_USE"


def test_set_app_resources_job():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[AppResourceSpec(name="etl", job=JobResource(id="42"))],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["job"]["id"] == "42"
    assert body["resources"][0]["job"]["permission"] == "CAN_MANAGE_RUN"


def test_set_app_resources_secret():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[AppResourceSpec(name="key", secret=SecretResource(scope="sc", key="k"))],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["secret"]["scope"] == "sc"
    assert body["resources"][0]["secret"]["key"] == "k"


def test_set_app_resources_serving_endpoint():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[
            AppResourceSpec(name="llm", serving_endpoint=ServingEndpointResource(name="gpt4"))
        ],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["serving_endpoint"]["name"] == "gpt4"
    assert body["resources"][0]["serving_endpoint"]["permission"] == "CAN_QUERY"


def test_set_app_resources_database():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[
            AppResourceSpec(
                name="ext",
                database=DatabaseResource(instance_name="rds", database_name="prod"),
            )
        ],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["database"]["instance_name"] == "rds"
    assert body["resources"][0]["database"]["database_name"] == "prod"


def test_set_app_resources_multiple():
    """Multiple resources of different types in one call."""
    agent = AgentSpec(
        name="multi",
        source="/tmp",
        resources=[
            AppResourceSpec(
                name="table",
                uc_securable=UCSecurableResource(
                    securable_type="TABLE", securable_full_name="a.b.c", permission="SELECT"
                ),
            ),
            AppResourceSpec(name="wh", sql_warehouse=SqlWarehouseResource(id="wh1")),
            AppResourceSpec(name="secret", secret=SecretResource(scope="s", key="k")),
        ],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert len(body["resources"]) == 3


def test_set_app_resources_empty():
    """Agent with no resources — no API call made."""
    agent = AgentSpec(name="bare", source="/tmp", resources=[])
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    engine.w.api_client.do.assert_not_called()


def test_set_app_resources_with_description():
    agent = AgentSpec(
        name="agent",
        source="/tmp",
        resources=[
            AppResourceSpec(
                name="data",
                description="Main data table",
                uc_securable=UCSecurableResource(
                    securable_type="TABLE", securable_full_name="a.b.c", permission="SELECT"
                ),
            ),
        ],
    )
    engine = _make_engine(_make_config([agent]))
    engine._set_app_resources(agent)

    body = engine.w.api_client.do.call_args[1]["body"]
    assert body["resources"][0]["description"] == "Main data table"


# ===================================================================
# _grant_app_to_app — permission grants
# ===================================================================


def test_grant_app_to_app():
    from databricks.sdk.service.apps import AppPermissionLevel

    engine = _make_engine(_make_config())
    engine._grant_app_to_app("sp-uuid-123", "target-app")

    engine.w.apps.update_permissions.assert_called_once()
    call_args = engine.w.apps.update_permissions.call_args
    assert call_args[1]["app_name"] == "target-app"
    acl = call_args[1]["access_control_list"]
    assert len(acl) == 1
    assert acl[0].service_principal_name == "sp-uuid-123"
    assert acl[0].permission_level == AppPermissionLevel.CAN_USE


def test_grant_app_to_app_handles_failure(caplog):
    engine = _make_engine(_make_config())
    engine.w.apps.update_permissions.side_effect = Exception("perm denied")

    # Should not raise
    engine._grant_app_to_app("sp-1", "app-2")


# ===================================================================
# Dry run
# ===================================================================


def test_dry_run_skips_deployment():
    agent = AgentSpec(
        name="test",
        source="/tmp/test",
        resources=[AppResourceSpec(name="wh", sql_warehouse=SqlWarehouseResource(id="x"))],
    )
    config = _make_config([agent])
    engine = DeployEngine(config, dry_run=True)
    engine._w = MagicMock()

    engine.deploy()

    # No app creation, no resource setting, no health checks
    engine.w.apps.create_and_wait.assert_not_called()
    engine.w.api_client.do.assert_not_called()
