#!/usr/bin/env python3
"""Deploy or drop masking functions via Databricks Statement Execution API.

Called by Terraform (null_resource + local-exec) during apply and destroy.
Auth is read from environment variables set by the provisioner:
  DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET

Usage:
  python3 deploy_masking_functions.py \
      --sql-file masking_functions.sql --warehouse-id <id>
  python3 deploy_masking_functions.py \
      --sql-file masking_functions.sql --warehouse-id <id> --drop
"""

import argparse
import re
import subprocess
import sys

REQUIRED_PACKAGES = {"databricks-sdk": "databricks.sdk"}


def _ensure_packages():
    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print(f"  Installing missing packages: {', '.join(missing)}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *missing],
        )


_ensure_packages()

from databricks.sdk import WorkspaceClient  # noqa: E402
from databricks.sdk.service.sql import (  # noqa: E402
    StatementState,
)


def parse_sql_blocks(sql_text: str) -> list:
    """Parse a SQL file into (catalog, schema, statement) tuples.

    Tracks USE CATALOG / USE SCHEMA directives to determine the execution
    context for each CREATE statement.
    """
    catalog, schema = None, None
    blocks = []

    for raw_stmt in re.split(r";\s*\n", sql_text):
        lines = [l for l in raw_stmt.split("\n")
                 if l.strip() and not l.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if not stmt:
            continue

        m = re.match(r"USE\s+CATALOG\s+(\S+)", stmt, re.IGNORECASE)
        if m:
            catalog = m.group(1)
            continue

        m = re.match(r"USE\s+SCHEMA\s+(\S+)", stmt, re.IGNORECASE)
        if m:
            schema = m.group(1)
            continue

        if stmt.upper().startswith("CREATE"):
            blocks.append((catalog, schema, stmt))

    return blocks


def extract_function_name(stmt: str) -> str:
    """Extract function name from a CREATE FUNCTION statement."""
    m = re.search(
        r"FUNCTION\s+(\S+)\s*\(", stmt, re.IGNORECASE
    )
    return m.group(1) if m else "<unknown>"


def deploy(sql_file: str, warehouse_id: str) -> None:
    w = WorkspaceClient()

    with open(sql_file) as f:
        sql_text = f.read()

    blocks = parse_sql_blocks(sql_text)
    if not blocks:
        print("  No CREATE statements found in SQL file — nothing to deploy.")
        return

    total = len(blocks)
    print(f"  Deploying {total} function(s) via Statement Execution API...")

    failed = 0
    for i, (catalog, schema, stmt) in enumerate(blocks, 1):
        func_name = extract_function_name(stmt)
        target = f"{catalog}.{schema}" if catalog and schema else "<default>"
        print(f"  [{i}/{total}] {target}.{func_name} ...", end=" ", flush=True)

        try:
            resp = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=stmt,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s",
            )
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
            continue

        state = resp.status.state
        if state == StatementState.SUCCEEDED:
            print("OK")
        else:
            error_msg = ""
            if resp.status.error:
                error_msg = resp.status.error.message or str(resp.status.error)
            print(f"FAILED ({state.value}): {error_msg}")
            failed += 1

    print()
    if failed:
        print(f"  {failed}/{total} statement(s) failed.")
        sys.exit(1)
    else:
        print(f"  All {total} function(s) deployed successfully.")


def drop(sql_file: str, warehouse_id: str) -> None:
    w = WorkspaceClient()

    with open(sql_file) as f:
        sql_text = f.read()

    blocks = parse_sql_blocks(sql_text)
    if not blocks:
        print("  No functions found in SQL file — nothing to drop.")
        return

    total = len(blocks)
    print(f"  Dropping {total} function(s) via Statement Execution API...")

    failed = 0
    for i, (catalog, schema, stmt) in enumerate(blocks, 1):
        func_name = extract_function_name(stmt)
        fqn = f"{catalog}.{schema}.{func_name}" if catalog and schema else func_name
        target = f"{catalog}.{schema}" if catalog and schema else "<default>"
        print(f"  [{i}/{total}] DROP {target}.{func_name} ...", end=" ", flush=True)

        drop_stmt = f"DROP FUNCTION IF EXISTS {fqn}"
        try:
            resp = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=drop_stmt,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s",
            )
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
            continue

        state = resp.status.state
        if state == StatementState.SUCCEEDED:
            print("OK")
        else:
            error_msg = ""
            if resp.status.error:
                error_msg = resp.status.error.message or str(resp.status.error)
            print(f"FAILED ({state.value}): {error_msg}")
            failed += 1

    print()
    if failed:
        print(f"  {failed}/{total} drop(s) failed.")
        sys.exit(1)
    else:
        print(f"  All {total} function(s) dropped successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy or drop masking functions via "
        "Databricks Statement Execution API"
    )
    parser.add_argument(
        "--sql-file",
        required=True,
        help="Path to masking_functions.sql",
    )
    parser.add_argument(
        "--warehouse-id",
        required=True,
        help="SQL warehouse ID for statement execution",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop functions instead of creating them (used during terraform destroy)",
    )
    args = parser.parse_args()

    if args.drop:
        drop(args.sql_file, args.warehouse_id)
    else:
        deploy(args.sql_file, args.warehouse_id)


if __name__ == "__main__":
    main()
