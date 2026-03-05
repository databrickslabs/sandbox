"""
Developer dashboard for agent discovery.

Launch via CLI:
    databricks-agents dashboard --profile my-profile

Or programmatically:
    from databricks_agents.dashboard import create_dashboard_app, run_dashboard
"""

from .app import create_dashboard_app
from .cli import main as run_dashboard

__all__ = ["create_dashboard_app", "run_dashboard"]
