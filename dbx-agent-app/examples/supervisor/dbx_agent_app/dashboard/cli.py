"""
CLI entry point for the developer dashboard.

Usage:
    dbx-agent-app dashboard --profile my-profile --port 8501
"""

import argparse
import asyncio
import logging
import sys
import webbrowser

import uvicorn

from .scanner import DashboardScanner
from .app import create_dashboard_app


def main():
    parser = argparse.ArgumentParser(
        prog="dbx-agent-app",
        description="Developer dashboard for Databricks agent discovery",
    )
    sub = parser.add_subparsers(dest="command")

    dash = sub.add_parser("dashboard", help="Launch the agent discovery dashboard")
    dash.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    dash.add_argument("--port", type=int, default=8501, help="Port to serve on (default: 8501)")
    dash.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    dash.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

    args = parser.parse_args()

    if args.command != "dashboard":
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    scanner = DashboardScanner(profile=args.profile)

    # Run initial scan
    print(f"Scanning workspace for agents (profile={args.profile or 'default'})...")
    try:
        agents = asyncio.run(scanner.scan())
        print(f"Found {len(agents)} agent(s)")
    except Exception as e:
        print(f"Initial scan failed: {e}", file=sys.stderr)
        print("Dashboard will start anyway — use the Scan button to retry.")

    app = create_dashboard_app(scanner, profile=args.profile)

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        webbrowser.open(url)

    print(f"Dashboard running at {url}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
