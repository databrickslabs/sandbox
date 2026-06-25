"""
Entry point for the Agent Platform when deployed as a Databricks App.

Deployed via: dbx-agent-app platform --profile <p>
Runtime: uvicorn dbx_agent_app.dashboard.__main__:app --host 0.0.0.0 --port 8000

Environment variables (set automatically by Databricks Apps):
  DATABRICKS_HOST        — workspace URL
  DATABRICKS_TOKEN       — auth token (via service principal)
  DATABRICKS_APP_URL     — this app's public URL
"""

import logging
import os

from .app import create_dashboard_app
from .governance import GovernanceService
from .scanner import DashboardScanner
from .system_builder import SystemBuilderService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Use the Databricks CLI profile if set, otherwise rely on env vars
profile = os.getenv("DATABRICKS_PROFILE")
catalog = os.getenv("UC_CATALOG", "main")

scanner = DashboardScanner(profile=profile)
governance = GovernanceService(scanner, profile=profile, catalog=catalog)
system_builder = SystemBuilderService(scanner=scanner, profile=profile)

app = create_dashboard_app(
    scanner,
    profile=profile,
    governance=governance,
    system_builder=system_builder,
    auto_scan_interval=60,
)

logger.info("Agent Platform app initialized (catalog=%s)", catalog)
