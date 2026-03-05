"""
System Builder service — visual agent wiring and deployment.

Manages system definitions (saved wiring configurations) and deploys
them to the workspace: updates env vars, redeploys apps, grants
app-to-app permissions, and optionally registers agents in UC.

Storage: JSON file in the data directory (no DB needed).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class WiringEdge(BaseModel):
    source_agent: str  # agent name (the dependency — the one being called)
    target_agent: str  # agent name (the caller — receives env var)
    env_var: str  # env var name injected into target (e.g. RESEARCH_URL)


class SystemDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    agents: List[str] = Field(default_factory=list)
    edges: List[WiringEdge] = Field(default_factory=list)
    uc_catalog: str = ""
    uc_schema: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DeployStepResult(BaseModel):
    agent: str
    action: str  # 'env_update' | 'redeploy' | 'grant_permission' | 'uc_register'
    status: str  # 'success' | 'failed' | 'skipped'
    detail: str = ""


class DeployResult(BaseModel):
    system_id: str
    steps: List[DeployStepResult] = Field(default_factory=list)
    status: str = "success"  # 'success' | 'partial' | 'failed'


class DeployProgress(BaseModel):
    """Async deploy progress — tracks background deploy tasks."""
    deploy_id: str
    system_id: str
    status: str = "pending"  # 'pending' | 'deploying' | 'success' | 'partial' | 'failed'
    current_step: int = 0
    total_steps: int = 0
    steps: List[DeployStepResult] = Field(default_factory=list)


class SystemCreate(BaseModel):
    name: str
    description: str = ""
    agents: List[str] = Field(default_factory=list)
    edges: List[WiringEdge] = Field(default_factory=list)
    uc_catalog: str = ""
    uc_schema: str = ""


class SystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agents: Optional[List[str]] = None
    edges: Optional[List[WiringEdge]] = None
    uc_catalog: Optional[str] = None
    uc_schema: Optional[str] = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SystemBuilderService:
    """CRUD for system definitions + deploy wiring to live agents."""

    def __init__(
        self,
        scanner: Any,
        profile: Optional[str] = None,
        data_dir: Optional[Path] = None,
    ):
        self._scanner = scanner
        self._profile = profile
        self._data_dir = data_dir or Path(__file__).parent / "data"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self._data_dir / "systems.json"
        self._systems: Dict[str, SystemDefinition] = {}
        self._active_deploys: Dict[str, DeployProgress] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._store_path.exists():
            try:
                raw = json.loads(self._store_path.read_text())
                for item in raw:
                    defn = SystemDefinition(**item)
                    self._systems[defn.id] = defn
            except Exception as e:
                logger.warning("Failed to load systems store: %s", e)

    def _save(self) -> None:
        raw = [defn.model_dump() for defn in self._systems.values()]
        self._store_path.write_text(json.dumps(raw, indent=2))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_systems(self) -> List[SystemDefinition]:
        return list(self._systems.values())

    def get_system(self, system_id: str) -> Optional[SystemDefinition]:
        return self._systems.get(system_id)

    def create_system(self, data: SystemCreate) -> SystemDefinition:
        self._validate_edges(data.agents, data.edges)
        defn = SystemDefinition(
            name=data.name,
            description=data.description,
            agents=data.agents,
            edges=data.edges,
            uc_catalog=data.uc_catalog,
            uc_schema=data.uc_schema,
        )
        self._systems[defn.id] = defn
        self._save()
        return defn

    def update_system(self, system_id: str, data: SystemUpdate) -> Optional[SystemDefinition]:
        defn = self._systems.get(system_id)
        if not defn:
            return None

        if data.name is not None:
            defn.name = data.name
        if data.description is not None:
            defn.description = data.description
        if data.agents is not None:
            defn.agents = data.agents
        if data.edges is not None:
            self._validate_edges(data.agents or defn.agents, data.edges)
            defn.edges = data.edges
        if data.uc_catalog is not None:
            defn.uc_catalog = data.uc_catalog
        if data.uc_schema is not None:
            defn.uc_schema = data.uc_schema

        defn.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return defn

    def delete_system(self, system_id: str) -> bool:
        if system_id in self._systems:
            del self._systems[system_id]
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_edges(self, agents: List[str], edges: List[WiringEdge]) -> None:
        agent_set = set(agents)
        for edge in edges:
            if edge.source_agent == edge.target_agent:
                raise ValueError(
                    f"Self-loop not allowed: {edge.source_agent} -> {edge.target_agent}"
                )
            if edge.source_agent not in agent_set:
                raise ValueError(f"Edge source '{edge.source_agent}' not in agents list")
            if edge.target_agent not in agent_set:
                raise ValueError(f"Edge target '{edge.target_agent}' not in agents list")

    # ------------------------------------------------------------------
    # Deploy
    # ------------------------------------------------------------------

    async def deploy_system(self, system_id: str) -> DeployResult:
        """
        Deploy wiring for a system:
          1. Resolve agent metadata from scanner
          2. Update env vars + redeploy target agents
          3. Grant app-to-app permissions
          4. UC registration (if configured)
        """
        defn = self._systems.get(system_id)
        if not defn:
            return DeployResult(
                system_id=system_id,
                status="failed",
                steps=[DeployStepResult(
                    agent="", action="lookup", status="failed",
                    detail=f"System {system_id} not found",
                )],
            )

        result = DeployResult(system_id=system_id)

        # 1. Resolve agent metadata (scanner first, then Apps API fallback)
        agent_meta: Dict[str, Dict[str, Any]] = {}
        ws_client_for_resolve = self._get_ws_client()

        # Build a name->app lookup from the Apps API for fallback resolution
        apps_by_name: Dict[str, Dict[str, str]] = {}
        if ws_client_for_resolve:
            try:
                for app in ws_client_for_resolve.apps.list():
                    app_url = getattr(app, "url", "") or ""
                    app_url = app_url.rstrip("/")
                    apps_by_name[app.name] = {
                        "app_name": app.name,
                        "endpoint_url": app_url,
                    }
            except Exception as e:
                logger.warning("Could not list apps for resolution: %s", e)

        for agent_name in defn.agents:
            # Try scanner first (has full agent card data)
            agent = self._scanner.get_agent_by_name(agent_name)
            if agent:
                agent_meta[agent_name] = {
                    "endpoint_url": agent.endpoint_url,
                    "app_name": agent.app_name,
                }
                result.steps.append(DeployStepResult(
                    agent=agent_name, action="resolve",
                    status="success", detail=f"Resolved via scanner: {agent.app_name}",
                ))
                continue

            # Fallback: match by app name (exact or prefix match)
            matched_app = apps_by_name.get(agent_name)
            if not matched_app:
                # Try common naming patterns: "sgp-multi-agent-{name}"
                for app_key, app_val in apps_by_name.items():
                    if app_key.endswith(f"-{agent_name}") or app_key == agent_name:
                        matched_app = app_val
                        break

            if matched_app:
                agent_meta[agent_name] = matched_app
                result.steps.append(DeployStepResult(
                    agent=agent_name, action="resolve",
                    status="success",
                    detail=f"Resolved via Apps API: {matched_app['app_name']}",
                ))
            else:
                result.steps.append(DeployStepResult(
                    agent=agent_name, action="resolve",
                    status="failed",
                    detail=f"Agent not found in scanner or Apps API (searched for '{agent_name}')",
                ))

        # 2. Build env var maps per target agent
        env_maps: Dict[str, Dict[str, str]] = {}
        for edge in defn.edges:
            source_meta = agent_meta.get(edge.source_agent)
            if not source_meta:
                result.steps.append(DeployStepResult(
                    agent=edge.target_agent, action="env_update",
                    status="skipped",
                    detail=f"Source agent '{edge.source_agent}' not resolved",
                ))
                continue
            env_maps.setdefault(edge.target_agent, {})[edge.env_var] = (
                source_meta["endpoint_url"]
            )

        # 3. Update env vars + redeploy each target
        ws_client = self._get_ws_client()
        for target_name, env_vars in env_maps.items():
            target_meta = agent_meta.get(target_name)
            if not target_meta or not ws_client:
                result.steps.append(DeployStepResult(
                    agent=target_name, action="env_update",
                    status="skipped", detail="No workspace client or agent not resolved",
                ))
                continue

            step = await self._update_env_and_redeploy(
                ws_client, target_meta["app_name"], env_vars
            )
            step.agent = target_name
            result.steps.append(step)

        # 4. Grant app-to-app permissions
        if ws_client:
            for edge in defn.edges:
                target_meta = agent_meta.get(edge.target_agent)
                source_meta = agent_meta.get(edge.source_agent)
                if not target_meta or not source_meta:
                    continue
                step = self._grant_app_permission(
                    ws_client, target_meta["app_name"], source_meta["app_name"]
                )
                step.agent = edge.target_agent
                result.steps.append(step)

        # 5. UC registration (if configured)
        if defn.uc_catalog and defn.uc_schema:
            for agent_name in defn.agents:
                meta = agent_meta.get(agent_name)
                if not meta:
                    continue
                step = await self._register_in_uc(
                    agent_name, meta["endpoint_url"],
                    defn.uc_catalog, defn.uc_schema,
                )
                result.steps.append(step)

        # Determine overall status
        statuses = {s.status for s in result.steps}
        if statuses == {"success"}:
            result.status = "success"
        elif "success" in statuses:
            result.status = "partial"
        else:
            result.status = "failed"

        return result

    # ------------------------------------------------------------------
    # Async deploy with progress tracking
    # ------------------------------------------------------------------

    def start_deploy(self, system_id: str) -> DeployProgress:
        """Start an async deploy — kicks off background task, returns immediately."""
        defn = self._systems.get(system_id)
        if not defn:
            return DeployProgress(
                deploy_id="", system_id=system_id, status="failed",
                steps=[DeployStepResult(
                    agent="", action="lookup", status="failed",
                    detail=f"System {system_id} not found",
                )],
            )

        deploy_id = str(uuid.uuid4())[:8]
        # Estimate total steps: resolve + env_update + permissions + UC
        total = len(defn.agents) + len(defn.edges) * 2  # resolve + env + grant
        if defn.uc_catalog and defn.uc_schema:
            total += len(defn.agents)

        progress = DeployProgress(
            deploy_id=deploy_id,
            system_id=system_id,
            status="pending",
            total_steps=max(total, 1),
        )
        self._active_deploys[system_id] = progress

        # Fire off background task
        asyncio.ensure_future(self._run_deploy_async(system_id, deploy_id))
        return progress

    async def _run_deploy_async(self, system_id: str, deploy_id: str) -> None:
        """Background deploy — updates _active_deploys as steps complete."""
        progress = self._active_deploys.get(system_id)
        if not progress:
            return

        progress.status = "deploying"
        try:
            result = await self.deploy_system(system_id)
            progress.steps = result.steps
            progress.current_step = len(result.steps)
            progress.status = result.status
        except Exception as e:
            progress.status = "failed"
            progress.steps.append(DeployStepResult(
                agent="", action="deploy", status="failed", detail=str(e),
            ))

    def get_deploy_status(self, system_id: str) -> Optional[DeployProgress]:
        """Get current deploy progress for a system."""
        return self._active_deploys.get(system_id)

    # ------------------------------------------------------------------
    # Deploy helpers
    # ------------------------------------------------------------------

    def _get_ws_client(self):
        try:
            from databricks.sdk import WorkspaceClient
            return (
                WorkspaceClient(profile=self._profile)
                if self._profile
                else WorkspaceClient()
            )
        except Exception as e:
            logger.warning("Could not create WorkspaceClient: %s", e)
            return None

    async def _update_env_and_redeploy(
        self,
        ws_client: Any,
        app_name: str,
        env_vars: Dict[str, str],
    ) -> DeployStepResult:
        """Fetch current app config, merge env vars, redeploy."""
        try:
            import yaml
            from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode

            # Get the current app to find source code path
            app = ws_client.apps.get(name=app_name)
            active = getattr(app, "active_deployment", None)
            if not active or not active.source_code_path:
                return DeployStepResult(
                    agent="", action="env_update", status="failed",
                    detail=f"No active deployment found for {app_name}",
                )

            source_path = active.source_code_path
            app_yaml_path = f"{source_path}/app.yaml"

            # Read current app.yaml
            import base64
            try:
                export = ws_client.workspace.export(path=app_yaml_path)
                content = base64.b64decode(export.content).decode() if export.content else ""
                app_config = yaml.safe_load(content) or {}
            except Exception:
                app_config = {}

            # Merge env vars (preserve existing, add/update wiring vars)
            existing_env = {
                e["name"]: e["value"]
                for e in (app_config.get("env") or [])
                if isinstance(e, dict) and "name" in e
            }
            existing_env.update(env_vars)
            app_config["env"] = [
                {"name": k, "value": v} for k, v in existing_env.items()
            ]

            # Upload updated app.yaml
            merged_content = yaml.dump(app_config, default_flow_style=False, sort_keys=False)
            from databricks.sdk.service.workspace import ImportFormat
            ws_client.workspace.import_(
                path=app_yaml_path,
                content=base64.b64encode(merged_content.encode()).decode(),
                format=ImportFormat.AUTO,
                overwrite=True,
            )

            # Redeploy
            deployment = AppDeployment(
                source_code_path=source_path,
                mode=AppDeploymentMode.SNAPSHOT,
            )
            ws_client.apps.deploy(app_name=app_name, app_deployment=deployment)

            env_summary = ", ".join(f"{k}=..." for k in env_vars)
            return DeployStepResult(
                agent="", action="env_update", status="success",
                detail=f"Updated env vars ({env_summary}) and redeployed {app_name}",
            )

        except Exception as e:
            return DeployStepResult(
                agent="", action="env_update", status="failed",
                detail=str(e),
            )

    def _grant_app_permission(
        self,
        ws_client: Any,
        caller_app_name: str,
        target_app_name: str,
    ) -> DeployStepResult:
        """Grant caller's SP CAN_USE on the target app."""
        try:
            # Get caller app's service principal
            caller_app = ws_client.apps.get(name=caller_app_name)
            sp_id = getattr(caller_app, "service_principal_id", None)
            if not sp_id:
                return DeployStepResult(
                    agent="", action="grant_permission", status="skipped",
                    detail=f"No SP found for {caller_app_name}",
                )

            # Resolve SP application_id (UUID) — required by permissions API
            sp = ws_client.service_principals.get(id=sp_id)
            sp_uuid = sp.application_id

            ws_client.api_client.do(
                "PATCH",
                f"/api/2.0/permissions/apps/{target_app_name}",
                body={
                    "access_control_list": [
                        {
                            "service_principal_name": sp_uuid,
                            "permission_level": "CAN_USE",
                        }
                    ]
                },
            )

            return DeployStepResult(
                agent="", action="grant_permission", status="success",
                detail=f"Granted {caller_app_name} SP ({sp_uuid}) CAN_USE on {target_app_name}",
            )

        except Exception as e:
            return DeployStepResult(
                agent="", action="grant_permission", status="failed",
                detail=str(e),
            )

    async def _register_in_uc(
        self,
        agent_name: str,
        endpoint_url: str,
        catalog: str,
        schema: str,
    ) -> DeployStepResult:
        """Register an agent in Unity Catalog."""
        try:
            from ..registry.uc_registry import UCAgentRegistry, UCAgentSpec

            registry = UCAgentRegistry(profile=self._profile)
            spec = UCAgentSpec(
                name=agent_name.replace("-", "_"),
                catalog=catalog,
                schema=schema,
                endpoint_url=endpoint_url,
                description=f"{agent_name} agent",
            )
            registry.register_agent(spec)

            return DeployStepResult(
                agent=agent_name, action="uc_register", status="success",
                detail=f"Registered as {catalog}.{schema}.{agent_name}",
            )

        except Exception as e:
            return DeployStepResult(
                agent=agent_name, action="uc_register", status="failed",
                detail=str(e),
            )
