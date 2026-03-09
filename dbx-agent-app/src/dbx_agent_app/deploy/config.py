"""
YAML config parsing, validation, and ${...} interpolation for agents.yaml.

The config schema:
  project:
    name: sgp-multi-agent
    workspace_path: /Workspace/Shared/apps
  uc:
    catalog: serverless_dxukih_catalog
    schema: agents
  warehouse:
    id: 387bcda0f2ece20c
  agents:
    - name: research
      source: ./agents/research
      resources:
        - name: transcripts-table
          uc_securable:
            securable_type: TABLE
            securable_full_name: "${uc.catalog}.${uc.schema}.expert_transcripts"
            permission: SELECT
        - name: warehouse
          sql_warehouse:
            id: "${warehouse.id}"
            permission: CAN_USE
        - name: api-key
          secret:
            scope: agent-secrets
            key: openai-key
            permission: READ
        - name: llm
          serving_endpoint:
            name: gpt-4-endpoint
            permission: CAN_QUERY
        - name: etl-job
          job:
            id: "12345"
            permission: CAN_MANAGE_RUN
      env:
        UC_CATALOG: "${uc.catalog}"

  Legacy form (auto-converted to resources):
    - name: research
      source: ./agents/research
      tables: [expert_transcripts]
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

from typing import Optional


# ---------------------------------------------------------------------------
# App resource declarations (maps to Databricks Apps API resource types)
# ---------------------------------------------------------------------------

# Valid enum values for UC securable resources (matches Apps API)
UC_SECURABLE_TYPES = {"TABLE", "VOLUME", "FUNCTION", "CONNECTION"}
UC_SECURABLE_PERMISSIONS = {
    "SELECT", "EXECUTE", "READ_VOLUME", "WRITE_VOLUME", "USE_CONNECTION", "MANAGE",
}

# Resource type field names (for validation)
_RESOURCE_TYPE_FIELDS = (
    "uc_securable", "sql_warehouse", "job", "secret", "serving_endpoint", "database",
)


class UCSecurableResource(BaseModel):
    """A Unity Catalog securable resource the agent needs access to."""

    securable_type: str  # TABLE | VOLUME | FUNCTION | CONNECTION
    securable_full_name: str  # catalog.schema.name (supports ${...} interpolation)
    permission: str  # SELECT | EXECUTE | READ_VOLUME | WRITE_VOLUME | USE_CONNECTION | MANAGE

    @field_validator("securable_type")
    @classmethod
    def validate_securable_type(cls, v: str) -> str:
        if v not in UC_SECURABLE_TYPES:
            raise ValueError(f"securable_type must be one of {UC_SECURABLE_TYPES}, got '{v}'")
        return v

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        if v not in UC_SECURABLE_PERMISSIONS:
            raise ValueError(f"permission must be one of {UC_SECURABLE_PERMISSIONS}, got '{v}'")
        return v


class SqlWarehouseResource(BaseModel):
    """A SQL warehouse resource the agent needs access to."""

    id: str  # warehouse ID (supports ${...} interpolation)
    permission: str = "CAN_USE"


class JobResource(BaseModel):
    """A job resource the agent needs access to."""

    id: str  # job ID (supports ${...} interpolation)
    permission: str = "CAN_MANAGE_RUN"


class SecretResource(BaseModel):
    """A secret resource the agent needs access to."""

    scope: str  # secret scope name
    key: str  # secret key name
    permission: str = "READ"


class ServingEndpointResource(BaseModel):
    """A model serving endpoint resource the agent needs access to."""

    name: str  # endpoint name
    permission: str = "CAN_QUERY"


class DatabaseResource(BaseModel):
    """A database resource the agent needs access to."""

    instance_name: str
    database_name: str
    permission: str = "CAN_CONNECT_AND_CREATE"


class AppResourceSpec(BaseModel):
    """A resource declaration for an agent's Databricks App.

    Exactly one resource type field must be set.
    """

    name: str
    description: str = ""
    uc_securable: Optional[UCSecurableResource] = None
    sql_warehouse: Optional[SqlWarehouseResource] = None
    job: Optional[JobResource] = None
    secret: Optional[SecretResource] = None
    serving_endpoint: Optional[ServingEndpointResource] = None
    database: Optional[DatabaseResource] = None

    @model_validator(mode="after")
    def exactly_one_resource_type(self) -> AppResourceSpec:
        set_types = [f for f in _RESOURCE_TYPE_FIELDS if getattr(self, f) is not None]
        if len(set_types) == 0:
            raise ValueError(f"Resource '{self.name}': exactly one resource type must be set, got none")
        if len(set_types) > 1:
            raise ValueError(
                f"Resource '{self.name}': exactly one resource type must be set, got {set_types}"
            )
        return self


class ProjectConfig(BaseModel):
    name: str
    workspace_path: str = "/Workspace/Shared/apps"


class UCConfig(BaseModel):
    catalog: str
    schema_: str  # 'schema' is a Pydantic reserved name

    class Config:
        populate_by_name = True

    @classmethod
    def from_dict(cls, data: dict) -> UCConfig:
        return cls(catalog=data["catalog"], schema_=data["schema"])


class WarehouseConfig(BaseModel):
    id: str


class AgentSpec(BaseModel):
    """Specification for a single agent in the deployment."""

    name: str
    source: str
    tables: list[str] = []  # Legacy — auto-converted to uc_securable resources
    resources: list[AppResourceSpec] = []
    depends_on: list[str] = []
    url_env_map: dict[str, str] = {}
    env: dict[str, str] = {}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(f"Agent name must be lowercase alphanumeric with hyphens: {v}")
        return v


class DeployConfig(BaseModel):
    """Parsed and validated deployment configuration."""

    project: ProjectConfig
    uc: UCConfig
    warehouse: WarehouseConfig
    agents: list[AgentSpec]

    @property
    def ordered_agents(self) -> list[AgentSpec]:
        """Return agents in topological order (dependencies first)."""
        return _topological_sort(self.agents)

    def app_name(self, agent: AgentSpec) -> str:
        """Derive the Databricks App name for an agent."""
        return f"{self.project.name}-{agent.name}"

    @classmethod
    def from_yaml(cls, path: str | Path) -> DeployConfig:
        """Load config from a YAML file, resolving ${...} interpolation."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        raw = yaml.safe_load(path.read_text())
        return cls.from_dict(raw, base_dir=path.parent)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], base_dir: Path | None = None) -> DeployConfig:
        """Build config from a raw dict (useful for testing)."""
        # Build interpolation context from top-level sections
        context = _build_context(raw)

        project = ProjectConfig(**raw["project"])
        uc = UCConfig.from_dict(raw["uc"])
        warehouse = WarehouseConfig(**raw["warehouse"])

        agents = []
        for agent_data in raw.get("agents", []):
            # Interpolate env values
            env = {}
            for k, v in agent_data.get("env", {}).items():
                env[k] = _interpolate(str(v), context)

            # Resolve source path relative to config file
            source = agent_data["source"]
            if base_dir and not Path(source).is_absolute():
                source = str((base_dir / source).resolve())

            # Parse explicit resources with interpolation
            resources: list[AppResourceSpec] = []
            for r in agent_data.get("resources", []):
                resources.append(_parse_resource(r, context))

            # Legacy backward compat: auto-convert tables → uc_securable resources
            tables = agent_data.get("tables", [])
            if tables and not resources:
                for table in tables:
                    full_name = _interpolate(
                        f"${{uc.catalog}}.${{uc.schema}}.{table}", context
                    )
                    resources.append(AppResourceSpec(
                        name=f"table-{table}",
                        uc_securable=UCSecurableResource(
                            securable_type="TABLE",
                            securable_full_name=full_name,
                            permission="SELECT",
                        ),
                    ))
                # Also add warehouse (old PermissionManager always granted it)
                wh_id = _interpolate("${warehouse.id}", context)
                resources.append(AppResourceSpec(
                    name="warehouse",
                    sql_warehouse=SqlWarehouseResource(id=wh_id),
                ))

            agents.append(
                AgentSpec(
                    name=agent_data["name"],
                    source=source,
                    tables=tables,
                    resources=resources,
                    depends_on=agent_data.get("depends_on", []),
                    url_env_map=agent_data.get("url_env_map", {}),
                    env=env,
                )
            )

        return cls(project=project, uc=uc, warehouse=warehouse, agents=agents)


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

_INTERP_RE = re.compile(r"\$\{([^}]+)\}")


def _build_context(raw: dict[str, Any]) -> dict[str, str]:
    """Flatten top-level YAML sections into dotted keys for interpolation.

    Example: {"uc": {"catalog": "foo"}} → {"uc.catalog": "foo"}
    """
    ctx: dict[str, str] = {}
    for section_key, section_val in raw.items():
        if section_key == "agents":
            continue
        if isinstance(section_val, dict):
            for k, v in section_val.items():
                ctx[f"{section_key}.{k}"] = str(v)
    return ctx


def _parse_resource(data: dict[str, Any], context: dict[str, str]) -> AppResourceSpec:
    """Parse a resource block from YAML, interpolating all string values."""
    name = data["name"]
    description = data.get("description", "")
    kwargs: dict[str, Any] = {"name": name, "description": description}

    if "uc_securable" in data:
        s = data["uc_securable"]
        kwargs["uc_securable"] = UCSecurableResource(
            securable_type=s["securable_type"],
            securable_full_name=_interpolate(str(s["securable_full_name"]), context),
            permission=s["permission"],
        )

    if "sql_warehouse" in data:
        w = data["sql_warehouse"]
        kwargs["sql_warehouse"] = SqlWarehouseResource(
            id=_interpolate(str(w["id"]), context),
            permission=w.get("permission", "CAN_USE"),
        )

    if "job" in data:
        j = data["job"]
        kwargs["job"] = JobResource(
            id=_interpolate(str(j["id"]), context),
            permission=j.get("permission", "CAN_MANAGE_RUN"),
        )

    if "secret" in data:
        s = data["secret"]
        kwargs["secret"] = SecretResource(
            scope=s["scope"],
            key=s["key"],
            permission=s.get("permission", "READ"),
        )

    if "serving_endpoint" in data:
        e = data["serving_endpoint"]
        kwargs["serving_endpoint"] = ServingEndpointResource(
            name=e["name"],
            permission=e.get("permission", "CAN_QUERY"),
        )

    if "database" in data:
        d = data["database"]
        kwargs["database"] = DatabaseResource(
            instance_name=d["instance_name"],
            database_name=d["database_name"],
            permission=d.get("permission", "CAN_CONNECT_AND_CREATE"),
        )

    return AppResourceSpec(**kwargs)


def _interpolate(value: str, context: dict[str, str]) -> str:
    """Replace ${dotted.key} placeholders with values from context."""

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in context:
            raise ValueError(f"Unknown interpolation key: ${{{key}}}")
        return context[key]

    return _INTERP_RE.sub(replacer, value)


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


def _topological_sort(agents: list[AgentSpec]) -> list[AgentSpec]:
    """Kahn's algorithm — returns agents ordered so dependencies come first."""
    by_name: dict[str, AgentSpec] = {a.name: a for a in agents}

    # Validate all depends_on references exist
    for a in agents:
        for dep in a.depends_on:
            if dep not in by_name:
                raise ValueError(f"Agent '{a.name}' depends on unknown agent '{dep}'")

    # Build in-degree map
    in_degree: dict[str, int] = {a.name: 0 for a in agents}
    reverse_deps: dict[str, list[str]] = {a.name: [] for a in agents}
    for a in agents:
        for dep in a.depends_on:
            in_degree[a.name] += 1
            reverse_deps[dep].append(a.name)

    # Start with nodes that have no dependencies
    queue: deque[str] = deque(name for name, deg in in_degree.items() if deg == 0)
    ordered: list[AgentSpec] = []

    while queue:
        name = queue.popleft()
        ordered.append(by_name[name])
        for dependent in reverse_deps[name]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(ordered) != len(agents):
        raise ValueError("Circular dependency detected among agents")

    return ordered
