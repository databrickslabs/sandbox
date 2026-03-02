#!/usr/bin/env python3
"""Sync tag policy values from abac.auto.tfvars to Databricks via SDK.

The Databricks Terraform provider has a bug where it reorders tag policy
values after apply, causing "Provider produced inconsistent result" errors.
This script bypasses Terraform by updating tag policy values directly via
the Databricks SDK, so Terraform can use ignore_changes = [values] safely.

Usage:
    python3 scripts/sync_tag_policies.py [path/to/abac.auto.tfvars]
"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def _load_auth():
    """Read auth.auto.tfvars and set SDK env vars."""
    auth_path = PROJECT_DIR / "auth.auto.tfvars"
    if not auth_path.exists():
        return
    try:
        import hcl2
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "python-hcl2"])
        import hcl2

    with open(auth_path) as f:
        cfg = hcl2.load(f)

    mapping = {
        "databricks_workspace_host": "DATABRICKS_HOST",
        "databricks_client_id": "DATABRICKS_CLIENT_ID",
        "databricks_client_secret": "DATABRICKS_CLIENT_SECRET",
    }
    for tfvar_key, env_key in mapping.items():
        val = cfg.get(tfvar_key, "")
        if val and not os.environ.get(env_key):
            os.environ[env_key] = val


def main():
    tfvars_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "abac.auto.tfvars"
    if not tfvars_path.exists():
        print(f"  [SKIP] {tfvars_path} not found")
        return

    import hcl2

    with open(tfvars_path) as f:
        config = hcl2.load(f)

    desired_policies = config.get("tag_policies", [])
    if not desired_policies:
        print("  [SKIP] No tag_policies found in config")
        return

    _load_auth()

    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.tags import TagPolicy, Value

    w = WorkspaceClient()

    existing = {}
    for tp in w.tag_policies.list_tag_policies():
        existing[tp.tag_key] = set(v.name for v in (tp.values or []))

    updated = 0
    for tp in desired_policies:
        key = tp["key"]
        desired_values = set(tp["values"])
        current_values = existing.get(key)

        if current_values is None:
            continue

        if desired_values == current_values:
            continue

        missing = desired_values - current_values
        removed = current_values - desired_values
        all_values = sorted(desired_values)
        policy = TagPolicy(
            tag_key=key,
            values=[Value(name=v) for v in all_values],
        )
        try:
            w.tag_policies.update_tag_policy(tag_key=key, tag_policy=policy, update_mask="values")
            changes = []
            if missing:
                changes.append(f"added {sorted(missing)}")
            if removed:
                changes.append(f"removed {sorted(removed)}")
            print(f"  [SYNC] {key}: {', '.join(changes)}")
            updated += 1
        except Exception as e:
            print(f"  [ERROR] {key}: {e}")

    if updated:
        print(f"  Synced {updated} tag policy/ies")
    else:
        print("  Tag policies already in sync")


if __name__ == "__main__":
    main()
