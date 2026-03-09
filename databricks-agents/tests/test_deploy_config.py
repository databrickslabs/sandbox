"""Tests for deploy config parsing, resource types, and validation."""

import pytest
import yaml
from pathlib import Path

from databricks_agents.deploy.config import (
    AppResourceSpec,
    AgentSpec,
    DeployConfig,
    UCSecurableResource,
    SqlWarehouseResource,
    JobResource,
    SecretResource,
    ServingEndpointResource,
    DatabaseResource,
    _parse_resource,
    _interpolate,
    _build_context,
)


# ===================================================================
# Interpolation
# ===================================================================


def test_interpolation_basic():
    ctx = {"uc.catalog": "main", "uc.schema": "agents"}
    assert _interpolate("${uc.catalog}.${uc.schema}.table", ctx) == "main.agents.table"


def test_interpolation_unknown_key():
    with pytest.raises(ValueError, match="Unknown interpolation key"):
        _interpolate("${missing.key}", {})


def test_build_context_skips_agents():
    raw = {
        "project": {"name": "test"},
        "uc": {"catalog": "cat", "schema": "sch"},
        "agents": [{"name": "skip-me"}],
    }
    ctx = _build_context(raw)
    assert "uc.catalog" in ctx
    assert "project.name" in ctx
    assert not any(k.startswith("agents") for k in ctx)


# ===================================================================
# UC securable validation
# ===================================================================


def test_uc_securable_valid_types():
    for stype in ("TABLE", "VOLUME", "FUNCTION", "CONNECTION"):
        r = UCSecurableResource(securable_type=stype, securable_full_name="a.b.c", permission="SELECT")
        assert r.securable_type == stype


def test_uc_securable_invalid_type():
    with pytest.raises(ValueError, match="securable_type must be one of"):
        UCSecurableResource(securable_type="INVALID", securable_full_name="a.b.c", permission="SELECT")


def test_uc_securable_valid_permissions():
    for perm in ("SELECT", "EXECUTE", "READ_VOLUME", "WRITE_VOLUME", "USE_CONNECTION", "MANAGE"):
        r = UCSecurableResource(securable_type="TABLE", securable_full_name="a.b.c", permission=perm)
        assert r.permission == perm


def test_uc_securable_invalid_permission():
    with pytest.raises(ValueError, match="permission must be one of"):
        UCSecurableResource(securable_type="TABLE", securable_full_name="a.b.c", permission="DROP")


# ===================================================================
# AppResourceSpec — exactly one resource type
# ===================================================================


def test_resource_spec_no_type_set():
    with pytest.raises(ValueError, match="exactly one resource type must be set, got none"):
        AppResourceSpec(name="empty")


def test_resource_spec_multiple_types():
    with pytest.raises(ValueError, match="exactly one resource type must be set"):
        AppResourceSpec(
            name="multi",
            uc_securable=UCSecurableResource(
                securable_type="TABLE", securable_full_name="a.b.c", permission="SELECT"
            ),
            sql_warehouse=SqlWarehouseResource(id="abc"),
        )


def test_resource_spec_each_type_valid():
    """Each resource type works when set alone."""
    specs = [
        AppResourceSpec(
            name="t1",
            uc_securable=UCSecurableResource(
                securable_type="TABLE", securable_full_name="a.b.c", permission="SELECT"
            ),
        ),
        AppResourceSpec(name="t2", sql_warehouse=SqlWarehouseResource(id="wh1")),
        AppResourceSpec(name="t3", job=JobResource(id="j1")),
        AppResourceSpec(name="t4", secret=SecretResource(scope="s", key="k")),
        AppResourceSpec(name="t5", serving_endpoint=ServingEndpointResource(name="ep1")),
        AppResourceSpec(
            name="t6",
            database=DatabaseResource(instance_name="db1", database_name="prod"),
        ),
    ]
    assert len(specs) == 6


# ===================================================================
# _parse_resource — all 6 types
# ===================================================================


@pytest.fixture
def context():
    return {"uc.catalog": "cat", "uc.schema": "sch", "warehouse.id": "wh123"}


def test_parse_uc_securable(context):
    data = {
        "name": "my-table",
        "uc_securable": {
            "securable_type": "TABLE",
            "securable_full_name": "${uc.catalog}.${uc.schema}.users",
            "permission": "SELECT",
        },
    }
    spec = _parse_resource(data, context)
    assert spec.uc_securable is not None
    assert spec.uc_securable.securable_full_name == "cat.sch.users"
    assert spec.uc_securable.securable_type == "TABLE"
    assert spec.uc_securable.permission == "SELECT"


def test_parse_sql_warehouse(context):
    data = {"name": "wh", "sql_warehouse": {"id": "${warehouse.id}", "permission": "CAN_USE"}}
    spec = _parse_resource(data, context)
    assert spec.sql_warehouse is not None
    assert spec.sql_warehouse.id == "wh123"
    assert spec.sql_warehouse.permission == "CAN_USE"


def test_parse_job(context):
    data = {"name": "etl", "job": {"id": "999", "permission": "CAN_MANAGE_RUN"}}
    spec = _parse_resource(data, context)
    assert spec.job is not None
    assert spec.job.id == "999"
    assert spec.job.permission == "CAN_MANAGE_RUN"


def test_parse_secret(context):
    data = {"name": "api-key", "secret": {"scope": "my-scope", "key": "openai", "permission": "READ"}}
    spec = _parse_resource(data, context)
    assert spec.secret is not None
    assert spec.secret.scope == "my-scope"
    assert spec.secret.key == "openai"


def test_parse_serving_endpoint(context):
    data = {"name": "llm", "serving_endpoint": {"name": "gpt4-ep", "permission": "CAN_QUERY"}}
    spec = _parse_resource(data, context)
    assert spec.serving_endpoint is not None
    assert spec.serving_endpoint.name == "gpt4-ep"


def test_parse_database(context):
    data = {
        "name": "ext-db",
        "database": {
            "instance_name": "my-rds",
            "database_name": "prod",
            "permission": "CAN_CONNECT_AND_CREATE",
        },
    }
    spec = _parse_resource(data, context)
    assert spec.database is not None
    assert spec.database.instance_name == "my-rds"
    assert spec.database.database_name == "prod"


def test_parse_resource_default_permissions(context):
    """Resource types use correct defaults when permission is omitted."""
    wh = _parse_resource({"name": "wh", "sql_warehouse": {"id": "x"}}, context)
    assert wh.sql_warehouse.permission == "CAN_USE"

    job = _parse_resource({"name": "j", "job": {"id": "1"}}, context)
    assert job.job.permission == "CAN_MANAGE_RUN"

    secret = _parse_resource({"name": "s", "secret": {"scope": "a", "key": "b"}}, context)
    assert secret.secret.permission == "READ"

    ep = _parse_resource({"name": "e", "serving_endpoint": {"name": "x"}}, context)
    assert ep.serving_endpoint.permission == "CAN_QUERY"

    db = _parse_resource(
        {"name": "d", "database": {"instance_name": "x", "database_name": "y"}}, context
    )
    assert db.database.permission == "CAN_CONNECT_AND_CREATE"


# ===================================================================
# DeployConfig.from_dict — full YAML parsing
# ===================================================================


def _base_raw(**overrides):
    """Build a minimal valid raw config dict."""
    raw = {
        "project": {"name": "test-project", "workspace_path": "/Workspace/Shared/apps"},
        "uc": {"catalog": "cat", "schema": "sch"},
        "warehouse": {"id": "wh1"},
        "agents": [],
    }
    raw.update(overrides)
    return raw


def test_from_dict_basic():
    raw = _base_raw(agents=[{"name": "echo", "source": "/tmp/echo"}])
    config = DeployConfig.from_dict(raw)
    assert config.project.name == "test-project"
    assert len(config.agents) == 1
    assert config.agents[0].name == "echo"


def test_from_dict_with_resources():
    raw = _base_raw(agents=[{
        "name": "research",
        "source": "/tmp/research",
        "resources": [
            {
                "name": "data",
                "uc_securable": {
                    "securable_type": "TABLE",
                    "securable_full_name": "${uc.catalog}.${uc.schema}.t",
                    "permission": "SELECT",
                },
            },
            {"name": "wh", "sql_warehouse": {"id": "${warehouse.id}"}},
            {"name": "j", "job": {"id": "42"}},
            {"name": "s", "secret": {"scope": "sc", "key": "k"}},
            {"name": "ep", "serving_endpoint": {"name": "gpt4"}},
            {
                "name": "db",
                "database": {"instance_name": "rds", "database_name": "prod"},
            },
        ],
    }])
    config = DeployConfig.from_dict(raw)
    agent = config.agents[0]
    assert len(agent.resources) == 6
    assert agent.resources[0].uc_securable.securable_full_name == "cat.sch.t"
    assert agent.resources[1].sql_warehouse.id == "wh1"


def test_from_dict_legacy_tables():
    """Legacy `tables` field auto-converts to uc_securable + warehouse resources."""
    raw = _base_raw(agents=[{
        "name": "legacy",
        "source": "/tmp/legacy",
        "tables": ["users", "orders"],
    }])
    config = DeployConfig.from_dict(raw)
    agent = config.agents[0]
    # 2 tables + 1 warehouse = 3 resources
    assert len(agent.resources) == 3
    assert agent.resources[0].uc_securable.securable_full_name == "cat.sch.users"
    assert agent.resources[1].uc_securable.securable_full_name == "cat.sch.orders"
    assert agent.resources[2].sql_warehouse.id == "wh1"


def test_from_dict_env_interpolation():
    raw = _base_raw(agents=[{
        "name": "test",
        "source": "/tmp/test",
        "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}],
        "env": {"UC_CATALOG": "${uc.catalog}", "STATIC": "plain"},
    }])
    config = DeployConfig.from_dict(raw)
    assert config.agents[0].env["UC_CATALOG"] == "cat"
    assert config.agents[0].env["STATIC"] == "plain"


def test_from_dict_topological_order():
    raw = _base_raw(agents=[
        {"name": "supervisor", "source": "/s", "depends_on": ["research"],
         "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}]},
        {"name": "research", "source": "/r",
         "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}]},
    ])
    config = DeployConfig.from_dict(raw)
    ordered = config.ordered_agents
    names = [a.name for a in ordered]
    assert names.index("research") < names.index("supervisor")


def test_from_dict_circular_dependency():
    raw = _base_raw(agents=[
        {"name": "a", "source": "/a", "depends_on": ["b"],
         "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}]},
        {"name": "b", "source": "/b", "depends_on": ["a"],
         "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}]},
    ])
    config = DeployConfig.from_dict(raw)
    with pytest.raises(ValueError, match="Circular dependency"):
        config.ordered_agents


def test_app_name():
    raw = _base_raw(agents=[{"name": "research", "source": "/tmp/r",
                             "resources": [{"name": "wh", "sql_warehouse": {"id": "x"}}]}])
    config = DeployConfig.from_dict(raw)
    assert config.app_name(config.agents[0]) == "test-project-research"


def test_from_yaml(tmp_path):
    yaml_content = {
        "project": {"name": "yaml-test"},
        "uc": {"catalog": "c", "schema": "s"},
        "warehouse": {"id": "w"},
        "agents": [{
            "name": "agent",
            "source": "./agent",
            "resources": [{"name": "wh", "sql_warehouse": {"id": "${warehouse.id}"}}],
        }],
    }
    config_file = tmp_path / "agents.yaml"
    config_file.write_text(yaml.dump(yaml_content))

    config = DeployConfig.from_yaml(config_file)
    assert config.agents[0].resources[0].sql_warehouse.id == "w"
    # Source path should be resolved relative to config file
    assert Path(config.agents[0].source).is_absolute()
