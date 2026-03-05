"""
Top-level CLI dispatcher for databricks-agents.

Commands:
    databricks-agents deploy    Deploy agents from agents.yaml
    databricks-agents status    Show deployment status
    databricks-agents destroy   Tear down deployed agents
    databricks-agents dashboard Launch the agent discovery dashboard locally
    databricks-agents platform  Deploy the Agent Platform as a Databricks App
"""

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="databricks-agents",
        description="CLI for Databricks agent deployment, discovery, and platform management",
    )
    sub = parser.add_subparsers(dest="command")

    # ---- deploy ----
    deploy_cmd = sub.add_parser("deploy", help="Deploy agents from agents.yaml")
    deploy_cmd.add_argument(
        "--config", type=str, default="agents.yaml", help="Path to agents.yaml (default: agents.yaml)"
    )
    deploy_cmd.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    deploy_cmd.add_argument("--agent", type=str, default=None, help="Deploy a single agent by name")
    deploy_cmd.add_argument("--dry-run", action="store_true", help="Show plan without deploying")

    # ---- status ----
    status_cmd = sub.add_parser("status", help="Show deployment status")
    status_cmd.add_argument(
        "--config", type=str, default="agents.yaml", help="Path to agents.yaml (default: agents.yaml)"
    )
    status_cmd.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    status_cmd.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    # ---- destroy ----
    destroy_cmd = sub.add_parser("destroy", help="Tear down all deployed agents")
    destroy_cmd.add_argument(
        "--config", type=str, default="agents.yaml", help="Path to agents.yaml (default: agents.yaml)"
    )
    destroy_cmd.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    destroy_cmd.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    # ---- dashboard (local dev) ----
    dash_cmd = sub.add_parser("dashboard", help="Launch the agent discovery dashboard locally")
    dash_cmd.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    dash_cmd.add_argument("--port", type=int, default=8501, help="Port (default: 8501)")
    dash_cmd.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    dash_cmd.add_argument("--catalog", type=str, default=None, help="UC catalog for lineage")
    dash_cmd.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

    # ---- platform (deploy as Databricks App) ----
    platform_cmd = sub.add_parser("platform", help="Deploy the Agent Platform as a Databricks App")
    platform_cmd.add_argument("--profile", type=str, default=None, help="Databricks CLI profile")
    platform_cmd.add_argument(
        "--app-name", type=str, default="agent-platform",
        help="Databricks App name (default: agent-platform)",
    )
    platform_cmd.add_argument("--catalog", type=str, default="main", help="UC catalog (default: main)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "dashboard":
        _run_dashboard(args)
    elif args.command == "deploy":
        _run_deploy(args)
    elif args.command == "status":
        _run_status(args)
    elif args.command == "destroy":
        _run_destroy(args)
    elif args.command == "platform":
        _run_platform(args)


def _run_deploy(args):
    from .deploy.config import DeployConfig
    from .deploy.engine import DeployEngine

    config = DeployConfig.from_yaml(args.config)
    engine = DeployEngine(config, profile=args.profile, dry_run=args.dry_run)
    engine.deploy(agent_filter=args.agent)


def _run_status(args):
    import json as json_mod

    from .deploy.config import DeployConfig
    from .deploy.engine import DeployEngine

    config = DeployConfig.from_yaml(args.config)
    engine = DeployEngine(config, profile=args.profile)
    result = engine.status(as_json=args.as_json)
    if args.as_json and result:
        print(json_mod.dumps(result, indent=2))


def _run_destroy(args):
    from .deploy.config import DeployConfig
    from .deploy.engine import DeployEngine

    config = DeployConfig.from_yaml(args.config)
    engine = DeployEngine(config, profile=args.profile)

    if not args.yes:
        answer = input(f"Destroy all agents in '{config.project.name}'? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    engine.destroy()


def _run_dashboard(args):
    from .dashboard.cli import run_dashboard

    run_dashboard(args)


def _run_platform(args):
    """Deploy the Agent Platform as a Databricks App."""
    import shutil
    import tempfile
    from pathlib import Path

    print(f"Deploying Agent Platform as '{args.app_name}' (profile={args.profile or 'default'})...")

    # Create a temporary deployment directory with app.yaml
    platform_src = Path(__file__).parent / "dashboard"
    app_yaml_src = platform_src / "app.yaml"

    if not app_yaml_src.exists():
        print("Error: app.yaml not found in dashboard package", file=sys.stderr)
        sys.exit(1)

    # Build the deployment bundle in a temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        deploy_dir = Path(tmpdir)

        # Copy app.yaml
        shutil.copy2(app_yaml_src, deploy_dir / "app.yaml")

        # Write requirements.txt for the deployed app
        try:
            from importlib.metadata import version as _get_version
            pkg_version = _get_version("databricks-agent-deploy")
        except Exception:
            pkg_version = "0.3.0"

        (deploy_dir / "requirements.txt").write_text(
            f"databricks-agent-deploy>={pkg_version}\n"
        )

        # Copy static frontend assets if they exist
        static_dir = platform_src / "static"
        if static_dir.is_dir():
            shutil.copytree(static_dir, deploy_dir / "static")

        # Deploy via databricks CLI
        import subprocess

        cmd = [
            "databricks", "apps", "deploy", args.app_name,
            "--source-code-path", str(deploy_dir),
        ]
        if args.profile:
            cmd.extend(["--profile", args.profile])

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Deploy failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

        print(result.stdout)
        print(f"Agent Platform deployed as '{args.app_name}'")


if __name__ == "__main__":
    main()
