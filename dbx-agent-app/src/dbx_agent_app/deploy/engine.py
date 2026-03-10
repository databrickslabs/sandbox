"""
DeployEngine — orchestrates full multi-agent deployment sequence.

Phases:
  0. Parse + validate config, load existing state
  1. Deploy each agent (create app, upload code, deploy, extract metadata)
  2. Set app resources (uc_securable, warehouse, job, secret, serving_endpoint, database) + app-to-app grants
  3. Verify health (poll /health endpoints)
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import (
    App,
    AppAccessControlRequest,
    AppDeployment,
    AppDeploymentMode,
    AppPermissionLevel,
)
from databricks.sdk.service.workspace import ImportFormat

from .config import AgentSpec, DeployConfig
from .state import DeployState

logger = logging.getLogger(__name__)


class DeployEngine:
    """Orchestrates multi-agent deployment to Databricks Apps."""

    def __init__(
        self,
        config: DeployConfig,
        profile: str | None = None,
        state_path: str | Path = ".agents-deploy.json",
        dry_run: bool = False,
        mode: str = "snapshot",
    ):
        self.config = config
        self.profile = profile
        self.dry_run = dry_run
        self.deploy_mode = mode.upper()  # SNAPSHOT or AUTO_SYNC
        self.state_path = Path(state_path)

        self._w: WorkspaceClient | None = None
        self.state = DeployState.load(self.state_path)
        self.state.project = config.project.name
        self.state.profile = profile or ""

    @property
    def w(self) -> WorkspaceClient:
        if self._w is None:
            self._w = WorkspaceClient(profile=self.profile) if self.profile else WorkspaceClient()
        return self._w

    # ------------------------------------------------------------------
    # Full deploy sequence
    # ------------------------------------------------------------------

    def deploy(self, agent_filter: str | None = None) -> None:
        """Run the full deploy sequence (or a single agent if filtered)."""
        ordered = self.config.ordered_agents
        if agent_filter:
            ordered = [a for a in ordered if a.name == agent_filter]
            if not ordered:
                raise ValueError(f"Agent '{agent_filter}' not found in config")

        self._print_plan(ordered)
        if self.dry_run:
            return

        # Phase 1: Deploy each agent in dependency order
        for agent in ordered:
            self._deploy_agent(agent)

        # Phase 2: Set app resources (uc_securable, warehouse) + app-to-app grants
        print(f"\n{'='*60}")
        print("App Resources & Permissions")
        print(f"{'='*60}")

        for agent in ordered:
            self._set_app_resources(agent)

        for agent in ordered:
            if not agent.depends_on:
                continue
            agent_state = self.state.get_agent(agent.name)
            if not agent_state or not agent_state.sp_client_id:
                continue
            for dep_name in agent.depends_on:
                dep_state = self.state.get_agent(dep_name)
                if dep_state:
                    self._grant_app_to_app(agent_state.sp_client_id, dep_state.app_name)

        # Phase 3: Health checks
        self._verify_health(ordered)

        self.state.save(self.state_path)
        print(f"\nDeploy state saved to {self.state_path}")

    # ------------------------------------------------------------------
    # Status command
    # ------------------------------------------------------------------

    def status(self, as_json: bool = False) -> dict[str, Any] | None:
        """Print or return status of all deployed agents."""
        if not self.state.agents:
            print("No agents deployed. Run 'dbx-agent-app deploy' first.")
            return None

        results: dict[str, dict[str, str]] = {}
        print(f"\nMulti-Agent Deployment: {self.state.project}")
        print(f"{'Agent':<16} {'Compute':<10} {'Deploy':<12} {'Health':<10} {'Last Deployed'}")
        print("-" * 80)

        for name, agent_state in self.state.agents.items():
            compute = "UNKNOWN"
            deploy = "UNKNOWN"
            health = "UNKNOWN"

            try:
                app = self.w.apps.get(name=agent_state.app_name)
                cs = getattr(app, "compute_status", None)
                compute = str(cs.state.value) if cs and cs.state else "UNKNOWN"
                active = getattr(app, "active_deployment", None)
                if active and active.status:
                    deploy = str(active.status.state.value) if active.status.state else "UNKNOWN"
            except Exception:
                compute = "NOT_FOUND"
                deploy = "NOT_FOUND"

            # Quick health check (follow redirects for OAuth)
            if agent_state.url:
                try:
                    import httpx

                    resp = httpx.get(
                        f"{agent_state.url}/health",
                        timeout=5.0,
                        follow_redirects=True,
                    )
                    health = "HEALTHY" if resp.status_code == 200 else f"HTTP_{resp.status_code}"
                except Exception:
                    health = "UNREACHABLE"

            deployed_at = agent_state.deployed_at[:16].replace("T", " ") if agent_state.deployed_at else "—"
            print(f"{name:<16} {compute:<10} {deploy:<12} {health:<10} {deployed_at}")
            results[name] = {
                "compute": compute,
                "deploy": deploy,
                "health": health,
                "deployed_at": deployed_at,
            }

        healthy = sum(1 for r in results.values() if r["health"] == "HEALTHY")
        print(f"\n{len(results)} agents deployed. {healthy}/{len(results)} healthy.")

        if as_json:
            return results
        return None

    # ------------------------------------------------------------------
    # Destroy command
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """Tear down all deployed agents: stop apps, delete apps, clean state."""
        if not self.state.agents:
            print("No agents to destroy.")
            return

        for name, agent_state in list(self.state.agents.items()):
            app_name = agent_state.app_name
            print(f"Destroying {app_name}...")
            try:
                self.w.apps.stop(name=app_name)
                logger.info("Stopped %s", app_name)
            except Exception as e:
                logger.warning("Failed to stop %s: %s", app_name, e)
            try:
                self.w.apps.delete(name=app_name)
                logger.info("Deleted %s", app_name)
            except Exception as e:
                logger.warning("Failed to delete %s: %s", app_name, e)
            self.state.remove_agent(name)

        self.state.save(self.state_path)
        print("All agents destroyed. State cleaned.")

    # ------------------------------------------------------------------
    # Internal: deploy a single agent
    # ------------------------------------------------------------------

    def _deploy_agent(self, agent: AgentSpec) -> None:
        app_name = self.config.app_name(agent)
        print(f"\n{'='*60}")
        print(f"Deploying: {agent.name} → {app_name}")
        print(f"{'='*60}")

        # 1. Create app if not exists
        self._create_app_if_needed(app_name)

        # 2. Build env vars (static env + url_env_map from already-deployed deps)
        env_vars = dict(agent.env)
        for dep_name, env_key in agent.url_env_map.items():
            dep_url = self.state.get_url(dep_name)
            if dep_url:
                env_vars[env_key] = dep_url
                logger.info("Wired %s=%s", env_key, dep_url)
            else:
                logger.warning("Dependency %s not yet deployed, %s will be empty", dep_name, env_key)

        # 3. Upload source code to workspace (merges env vars into app.yaml)
        workspace_path = f"{self.config.project.workspace_path}/{app_name}"
        self._upload_source(agent.source, workspace_path, env_vars=env_vars)

        # 4. Deploy
        self._deploy_app(app_name, workspace_path)

        # 5. Extract metadata (URL, SP)
        self._extract_metadata(agent.name, app_name)

    def _create_app_if_needed(self, app_name: str) -> None:
        """Create the Databricks App if it doesn't exist."""
        try:
            self.w.apps.get(name=app_name)
            logger.info("App %s already exists", app_name)
        except Exception:
            print(f"  Creating app {app_name}...")
            self.w.apps.create_and_wait(App(name=app_name))
            logger.info("Created app %s", app_name)

    def _upload_source(
        self, source_dir: str, workspace_path: str, env_vars: dict[str, str] | None = None
    ) -> None:
        """Upload local source directory to Databricks workspace.

        If env_vars is provided, merges them into app.yaml before uploading.
        """
        source = Path(source_dir)
        if not source.exists():
            raise FileNotFoundError(f"Source directory not found: {source}")

        print(f"  Uploading {source} → {workspace_path}")

        # Collect files to upload, tracking which directories need creation
        dirs_needed: set[str] = {workspace_path}
        files_to_upload: list[tuple[Path, str, bytes]] = []

        for local_file in source.rglob("*"):
            if local_file.is_dir():
                continue
            # Skip common non-deployable files
            if any(
                part.startswith(".")
                for part in local_file.relative_to(source).parts
                if part != "."
            ):
                continue
            if local_file.name == "__pycache__" or local_file.suffix == ".pyc":
                continue

            rel_path = local_file.relative_to(source)
            remote_path = f"{workspace_path}/{rel_path}"

            # Track parent directories
            parent = str(Path(remote_path).parent)
            while parent != workspace_path and parent.startswith(workspace_path):
                dirs_needed.add(parent)
                parent = str(Path(parent).parent)

            # Merge env vars into app.yaml before uploading
            if rel_path.name == "app.yaml" and env_vars:
                content = self._merge_app_yaml(local_file, env_vars)
            else:
                content = local_file.read_bytes()

            files_to_upload.append((rel_path, remote_path, content))

        # Create all directories first (sorted so parents come before children)
        for dir_path in sorted(dirs_needed):
            try:
                self.w.workspace.mkdirs(path=dir_path)
            except Exception:
                pass  # Directory may already exist

        # Upload files
        file_count = 0
        for rel_path, remote_path, content in files_to_upload:
            try:
                self.w.workspace.import_(
                    path=remote_path,
                    content=base64.b64encode(content).decode(),
                    format=ImportFormat.AUTO,
                    overwrite=True,
                )
                file_count += 1
            except Exception as e:
                logger.warning("Failed to upload %s: %s", rel_path, e)

        print(f"  Uploaded {file_count} files")

    def _merge_app_yaml(self, app_yaml_path: Path, env_vars: dict[str, str]) -> bytes:
        """Merge env vars from agents.yaml into the agent's app.yaml."""
        app_config = yaml.safe_load(app_yaml_path.read_text()) or {}
        # Build env list in app.yaml format: [{name: X, value: Y}, ...]
        env_list = [{"name": k, "value": v} for k, v in env_vars.items()]
        app_config["env"] = env_list
        merged = yaml.dump(app_config, default_flow_style=False, sort_keys=False)
        logger.info("Merged %d env vars into app.yaml", len(env_vars))
        return merged.encode()

    def _deploy_app(self, app_name: str, workspace_path: str) -> None:
        """Deploy (or redeploy) the app. Env vars are already in app.yaml."""
        mode = getattr(AppDeploymentMode, self.deploy_mode, AppDeploymentMode.SNAPSHOT)
        print(f"  Deploying {app_name} (mode={mode.value})...")

        deployment = AppDeployment(
            source_code_path=workspace_path,
            mode=mode,
        )

        result = self.w.apps.deploy_and_wait(app_name=app_name, app_deployment=deployment)
        status = getattr(result, "status", None)
        state = getattr(status, "state", "UNKNOWN") if status else "UNKNOWN"
        print(f"  Deploy status: {state}")

    def _extract_metadata(self, agent_name: str, app_name: str) -> None:
        """Extract URL and SP info from the deployed app."""
        try:
            app = self.w.apps.get(name=app_name)
            url = getattr(app, "url", "") or ""
            sp_name = getattr(app, "service_principal_name", "") or ""
            sp_id = str(getattr(app, "service_principal_client_id", "") or "")

            self.state.set_agent(
                agent_name,
                app_name=app_name,
                url=url,
                sp_name=sp_name,
                sp_client_id=sp_id,
            )
            print(f"  URL: {url}")
            print(f"  SP:  {sp_name}")
        except Exception as e:
            logger.warning("Failed to extract metadata for %s: %s", app_name, e)
            self.state.set_agent(agent_name, app_name=app_name)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def _verify_health(self, agents: list[AgentSpec]) -> None:
        """Poll /health for each agent using workspace auth, retrying up to 10 times."""
        import httpx

        print(f"\n{'='*60}")
        print("Health Checks")
        print(f"{'='*60}")

        # Get auth token from the workspace client for authenticated health checks
        headers = {}
        try:
            token = self.w.config.authenticate()
            if callable(token):
                auth_headers = token()
                headers = dict(auth_headers) if auth_headers else {}
        except Exception:
            pass

        for agent in agents:
            agent_state = self.state.get_agent(agent.name)
            if not agent_state or not agent_state.url:
                print(f"  {agent.name:<20} NO URL — skipping health check")
                continue

            url = f"{agent_state.url}/health"
            healthy = False
            for attempt in range(1, 11):
                try:
                    resp = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
                    if resp.status_code == 200:
                        healthy = True
                        break
                except Exception:
                    pass
                if attempt < 10:
                    time.sleep(5)

            status = "HEALTHY" if healthy else "UNHEALTHY"
            print(f"  {agent.name:<20} {status:<12} {agent_state.url}")

    # ------------------------------------------------------------------
    # App resources — all types via REST API
    # ------------------------------------------------------------------

    def _set_app_resources(self, agent: AgentSpec) -> None:
        """Declare all resources on the app via REST API.

        Uses the REST API directly rather than SDK enums because the SDK's
        uc_securable type enum only covers VOLUME. TABLE, FUNCTION, and
        CONNECTION require REST (same approach as the Terraform provider).
        """
        app_name = self.config.app_name(agent)
        if not agent.resources and not agent.user_api_scopes:
            return

        payload_resources = []
        for r in agent.resources:
            res: dict[str, Any] = {"name": r.name}
            if r.description:
                res["description"] = r.description

            if r.uc_securable:
                res["uc_securable"] = {
                    "securable_full_name": r.uc_securable.securable_full_name,
                    "securable_type": r.uc_securable.securable_type,
                    "permission": r.uc_securable.permission,
                }
            elif r.sql_warehouse:
                res["sql_warehouse"] = {
                    "id": r.sql_warehouse.id,
                    "permission": r.sql_warehouse.permission,
                }
            elif r.job:
                res["job"] = {
                    "id": r.job.id,
                    "permission": r.job.permission,
                }
            elif r.secret:
                res["secret"] = {
                    "scope": r.secret.scope,
                    "key": r.secret.key,
                    "permission": r.secret.permission,
                }
            elif r.serving_endpoint:
                res["serving_endpoint"] = {
                    "name": r.serving_endpoint.name,
                    "permission": r.serving_endpoint.permission,
                }
            elif r.database:
                res["database"] = {
                    "instance_name": r.database.instance_name,
                    "database_name": r.database.database_name,
                    "permission": r.database.permission,
                }
            elif r.genie_space:
                res["genie_space"] = {
                    "id": r.genie_space.id,
                    "permission": r.genie_space.permission,
                }
            else:
                continue

            payload_resources.append(res)

        if not payload_resources and not agent.user_api_scopes:
            return

        body: dict[str, Any] = {"name": app_name}
        if payload_resources:
            body["resources"] = payload_resources
        if agent.user_api_scopes:
            body["user_api_scopes"] = agent.user_api_scopes

        try:
            self.w.api_client.do(
                "PATCH",
                f"/api/2.0/apps/{app_name}",
                body=body,
            )
            print(f"  {agent.name:<20} {len(payload_resources)} resource(s) set")
        except Exception as e:
            logger.warning("Failed to set resources on %s: %s", app_name, e)
            print(f"  {agent.name:<20} FAILED setting resources ({e})")

    def _grant_app_to_app(self, supervisor_sp_id: str, target_app_name: str) -> None:
        """Grant CAN_USE on sub-agent app to the supervisor's service principal."""
        try:
            self.w.apps.update_permissions(
                app_name=target_app_name,
                access_control_list=[
                    AppAccessControlRequest(
                        service_principal_name=supervisor_sp_id,
                        permission_level=AppPermissionLevel.CAN_USE,
                    )
                ],
            )
            logger.info("Granted CAN_USE on %s to %s", target_app_name, supervisor_sp_id)
        except Exception as e:
            logger.warning("App-to-app grant failed for %s → %s: %s", supervisor_sp_id, target_app_name, e)

    # ------------------------------------------------------------------
    # LoggedModel registration (opt-in)
    # ------------------------------------------------------------------

    def register_models(self, agents: list[AgentSpec] | None = None) -> None:
        """Register deployed agents as MLflow LoggedModels.

        Creates an external model for each deployed agent so it appears in
        the MLflow model lineage view, linked to traces and evaluations.

        Requires ``mlflow>=3.0.0``.  Skips gracefully if mlflow is not installed.
        """
        try:
            import mlflow
        except ImportError:
            print("  mlflow not installed — skipping model registration")
            return

        if agents is None:
            agents = self.config.ordered_agents

        experiment_name = f"/dbx-agent-app/{self.config.project.name}"
        mlflow.set_experiment(experiment_name)

        print(f"\n{'='*60}")
        print("MLflow Model Registration")
        print(f"{'='*60}")
        print(f"  Experiment: {experiment_name}")

        for agent in agents:
            agent_state = self.state.get_agent(agent.name)
            if not agent_state:
                continue

            try:
                model = mlflow.create_external_model(
                    name=agent.name,
                    model_type="databricks-app-agent",
                    params={
                        "endpoint_url": agent_state.url or "",
                        "app_name": agent_state.app_name,
                        "source": agent.source,
                    },
                    tags={
                        "deployed_at": agent_state.deployed_at or "",
                        "profile": self.profile or "",
                        "sdk": "dbx-agent-app",
                    },
                )
                print(f"  {agent.name:<20} registered (model_id={model.model_id})")
            except Exception as e:
                print(f"  {agent.name:<20} registration failed — {e}")

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def _print_plan(self, agents: list[AgentSpec]) -> None:
        """Print what would be deployed without executing."""
        print(f"\nDeployment Plan: {self.config.project.name}")
        print(f"Profile: {self.profile or 'default'}")
        print(f"Mode: {self.deploy_mode}")
        print(f"UC: {self.config.uc.catalog}.{self.config.uc.schema_}")
        print(f"Warehouse: {self.config.warehouse.id}")
        print()
        print(f"{'#':<4} {'Agent':<18} {'App Name':<35} {'Resources':<16} {'Deps'}")
        print("-" * 100)
        for i, agent in enumerate(agents, 1):
            app_name = self.config.app_name(agent)
            res_count = f"{len(agent.resources)} resource(s)" if agent.resources else "—"
            deps = ", ".join(agent.depends_on) or "—"
            print(f"{i:<4} {agent.name:<18} {app_name:<35} {res_count:<16} {deps}")

        if self.dry_run:
            print("\n[DRY RUN] No changes will be made.")
