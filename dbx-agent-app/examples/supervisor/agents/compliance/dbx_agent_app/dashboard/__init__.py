"""
Developer dashboard for agent discovery.

Launch via CLI:
    dbx-agent-app dashboard --profile my-profile

Or programmatically:
    from dbx_agent_app.dashboard import create_dashboard_app, run_dashboard
"""

from .app import create_dashboard_app
from .cli import main as run_dashboard

__all__ = ["create_dashboard_app", "run_dashboard"]
