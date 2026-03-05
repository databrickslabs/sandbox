"""
Grant UC, warehouse, and app-to-app permissions for deployed agents.

All grants are additive/idempotent — safe to re-run on every deploy.

UC permissions use the service principal's application_id (UUID).
Warehouse and app-to-app permissions use the SP display name.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class PermissionManager:
    """Grants UC catalog/schema/table, warehouse, and app-to-app permissions."""

    def __init__(self, w: WorkspaceClient, catalog: str, schema: str, warehouse_id: str):
        self.w = w
        self.catalog = catalog
        self.schema = schema
        self.warehouse_id = warehouse_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grant_agent_permissions(
        self,
        sp_application_id: str,
        tables: list[str],
        models: list[str] | None = None,
    ) -> None:
        """Grant all required permissions for one agent's service principal.

        Args:
            sp_application_id: The SP's application_id (UUID), used for UC grants.
            tables: Table names to grant SELECT on.
            models: Registered model names to grant ALL PRIVILEGES on.
        """
        self._grant_uc_catalog(sp_application_id)
        self._grant_uc_schema(sp_application_id)
        for table in tables:
            self._grant_uc_table(sp_application_id, table)
        for model in (models or []):
            self._grant_uc_model(sp_application_id, model)
        self._grant_warehouse(sp_application_id)
        logger.info("Permissions granted for SP %s", sp_application_id)

    def grant_app_to_app(self, supervisor_sp_id: str, target_app_name: str) -> None:
        """Grant CAN_USE on a sub-agent app to the supervisor's service principal."""
        logger.info("Granting CAN_USE on app %s to SP %s", target_app_name, supervisor_sp_id)
        try:
            self.w.api_client.do(
                "PATCH",
                f"/api/2.0/permissions/apps/{target_app_name}",
                body={
                    "access_control_list": [
                        {
                            "service_principal_name": supervisor_sp_id,
                            "all_permissions": [{"permission_level": "CAN_USE"}],
                        }
                    ]
                },
            )
        except Exception as e:
            logger.warning("App-to-app permission grant failed (may need manual grant): %s", e)

    # ------------------------------------------------------------------
    # UC grants via REST API — use application_id as principal
    # ------------------------------------------------------------------

    def _grant_uc_catalog(self, sp_application_id: str) -> None:
        logger.info("Granting USE_CATALOG + BROWSE on %s to %s", self.catalog, sp_application_id)
        try:
            self.w.api_client.do(
                "PATCH",
                f"/api/2.1/unity-catalog/permissions/catalog/{self.catalog}",
                body={
                    "changes": [
                        {
                            "principal": sp_application_id,
                            "add": ["USE_CATALOG", "BROWSE"],
                        }
                    ]
                },
            )
        except Exception as e:
            logger.warning("UC catalog grant on %s failed: %s", self.catalog, e)

    def _grant_uc_schema(self, sp_application_id: str) -> None:
        fqn = f"{self.catalog}.{self.schema}"
        logger.info("Granting USE_SCHEMA + CREATE_MODEL on %s to %s", fqn, sp_application_id)
        try:
            self.w.api_client.do(
                "PATCH",
                f"/api/2.1/unity-catalog/permissions/schema/{fqn}",
                body={
                    "changes": [
                        {
                            "principal": sp_application_id,
                            "add": ["USE_SCHEMA", "CREATE_MODEL", "SELECT"],
                        }
                    ]
                },
            )
        except Exception as e:
            logger.warning("UC schema grant on %s failed: %s", fqn, e)

    def _grant_uc_table(self, sp_application_id: str, table: str) -> None:
        fqn = f"{self.catalog}.{self.schema}.{table}"
        logger.info("Granting SELECT on %s to %s", fqn, sp_application_id)
        self._uc_permission_patch(
            f"/api/2.1/unity-catalog/permissions/table/{fqn}",
            sp_application_id,
            "SELECT",
        )

    def _uc_permission_patch(self, path: str, sp_application_id: str, privilege: str) -> None:
        """PATCH a UC permission grant. Additive — won't revoke existing grants."""
        try:
            self.w.api_client.do(
                "PATCH",
                path,
                body={
                    "changes": [
                        {
                            "principal": sp_application_id,
                            "add": [privilege],
                        }
                    ]
                },
            )
        except Exception as e:
            logger.warning("UC grant %s on %s failed: %s", privilege, path, e)

    # ------------------------------------------------------------------
    # UC model grant — use SQL statements API (REST permissions API
    # returns "REGISTERED_MODEL is not enabled" on many workspaces)
    # ------------------------------------------------------------------

    def _grant_uc_model(self, sp_application_id: str, model: str) -> None:
        fqn = f"`{self.catalog}`.`{self.schema}`.`{model}`"
        logger.info("Granting ALL PRIVILEGES on MODEL %s to %s", fqn, sp_application_id)
        self._exec_sql(f"GRANT ALL PRIVILEGES ON MODEL {fqn} TO `{sp_application_id}`")

    # ------------------------------------------------------------------
    # Warehouse grant — use SQL statements API (REST permissions API
    # returns "Permission type not defined" for SP application_ids)
    # ------------------------------------------------------------------

    def _grant_warehouse(self, sp_application_id: str) -> None:
        logger.info("Granting CAN_USE on warehouse %s to %s", self.warehouse_id, sp_application_id)
        self._exec_sql(f"GRANT USE CATALOG ON CATALOG `{self.catalog}` TO `{sp_application_id}`")

    # ------------------------------------------------------------------
    # SQL execution helper — runs statements via the SQL Statements API
    # ------------------------------------------------------------------

    def _exec_sql(self, statement: str) -> None:
        """Execute a SQL statement via the Statements API. Used for grants
        where the REST permissions API doesn't work (warehouse, models)."""
        try:
            self.w.api_client.do(
                "POST",
                "/api/2.0/sql/statements",
                body={
                    "warehouse_id": self.warehouse_id,
                    "statement": statement,
                    "wait_timeout": "30s",
                },
            )
        except Exception as e:
            logger.warning("SQL grant failed (%s): %s", statement[:60], e)
