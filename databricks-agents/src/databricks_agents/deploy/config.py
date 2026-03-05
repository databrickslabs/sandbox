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
      tables: [expert_transcripts]
      env:
        UC_CATALOG: "${uc.catalog}"
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator


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
    tables: list[str] = []
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

            agents.append(
                AgentSpec(
                    name=agent_data["name"],
                    source=source,
                    tables=agent_data.get("tables", []),
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
