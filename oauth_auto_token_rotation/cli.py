#!/usr/bin/env python3
"""
Command-line interface for Databricks OAuth Token Rotator
"""

import sys
import argparse
from .rotator import DatabricksOAuthRotator


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Databricks PostgreSQL OAuth Token Auto-Rotation Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once (test mode)
  databricks-oauth-rotator --once

  # Run as daemon with custom interval
  databricks-oauth-rotator --interval 45

  # Specify all parameters
  databricks-oauth-rotator \\
    --workspace-url https://workspace.cloud.databricks.com \\
    --pg-host instance-xyz.database.cloud.databricks.com \\
    --pg-username user@company.com \\
    --once

Environment Variables:
  DATABRICKS_HOST            Workspace URL
  DATABRICKS_CLIENT_ID       OAuth client ID (for M2M)
  DATABRICKS_CLIENT_SECRET   OAuth client secret (for M2M)
  DATABRICKS_PG_HOST         PostgreSQL hostname
  DATABRICKS_PG_USERNAME     PostgreSQL username
        """
    )

    # Mode arguments
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (for testing)'
    )

    # Configuration arguments
    parser.add_argument(
        '--workspace-url',
        help='Databricks workspace URL (or set DATABRICKS_HOST)'
    )
    parser.add_argument(
        '--client-id',
        help='OAuth client ID for M2M auth (or set DATABRICKS_CLIENT_ID)'
    )
    parser.add_argument(
        '--client-secret',
        help='OAuth client secret for M2M auth (or set DATABRICKS_CLIENT_SECRET)'
    )
    parser.add_argument(
        '--pg-host',
        help='PostgreSQL hostname (or set DATABRICKS_PG_HOST)'
    )
    parser.add_argument(
        '--pg-port',
        default='5432',
        help='PostgreSQL port (default: 5432)'
    )
    parser.add_argument(
        '--pg-database',
        default='databricks_postgres',
        help='PostgreSQL database name (default: databricks_postgres)'
    )
    parser.add_argument(
        '--pg-username',
        help='PostgreSQL username (or set DATABRICKS_PG_USERNAME)'
    )
    parser.add_argument(
        '--pgpass-file',
        default='~/.pgpass',
        help='Path to .pgpass file (default: ~/.pgpass)'
    )
    parser.add_argument(
        '--log-file',
        default='~/.databricks_oauth_rotator.log',
        help='Path to log file (default: ~/.databricks_oauth_rotator.log)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=50,
        help='Rotation interval in minutes (default: 50)'
    )

    args = parser.parse_args()

    try:
        # Create rotator instance
        rotator = DatabricksOAuthRotator(
            workspace_url=args.workspace_url,
            client_id=args.client_id,
            client_secret=args.client_secret,
            pg_host=args.pg_host,
            pg_port=args.pg_port,
            pg_database=args.pg_database,
            pg_username=args.pg_username,
            pgpass_file=args.pgpass_file,
            log_file=args.log_file,
            rotation_interval=args.interval
        )

        if args.once:
            # Run once and exit
            success = rotator.run_once()
            sys.exit(0 if success else 1)
        else:
            # Run as daemon
            try:
                rotator.run_daemon()
            except KeyboardInterrupt:
                rotator.logger.info("Interrupted by user")
                sys.exit(0)

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nUse --help for usage information", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
