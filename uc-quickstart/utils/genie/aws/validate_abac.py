#!/usr/bin/env python3
"""
Validate AI-generated ABAC configuration before terraform apply.

Checks:
  1. terraform.tfvars structure and required fields
  2. masking_functions.sql function definitions
  3. Cross-references between both files

Usage:
  pip install python-hcl2          # one-time
  python validate_abac.py terraform.tfvars masking_functions.sql
  python validate_abac.py terraform.tfvars   # skip SQL check
"""

import sys
import re
import argparse
from pathlib import Path

try:
    import hcl2
except ImportError:
    print("ERROR: python-hcl2 is required.  Install with:")
    print("  pip install python-hcl2")
    sys.exit(2)

VALID_ENTITY_TYPES = {"tables", "columns"}
VALID_POLICY_TYPES = {"POLICY_TYPE_COLUMN_MASK", "POLICY_TYPE_ROW_FILTER"}
BUILTIN_PRINCIPALS = {"account users"}

COLUMN_MASK_REQUIRED = {"name", "policy_type", "to_principals", "match_condition", "match_alias", "function_name"}
ROW_FILTER_REQUIRED = {"name", "policy_type", "to_principals", "when_condition", "function_name"}


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def ok(self, msg: str):
        self.info.append(msg)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def print_report(self):
        width = 60
        print("=" * width)
        print("  ABAC Configuration Validation Report")
        print("=" * width)

        if self.info:
            for line in self.info:
                print(f"  [PASS] {line}")

        if self.warnings:
            print()
            for line in self.warnings:
                print(f"  [WARN] {line}")

        if self.errors:
            print()
            for line in self.errors:
                print(f"  [FAIL] {line}")

        print("-" * width)
        counts = (
            f"{len(self.info)} passed, "
            f"{len(self.warnings)} warnings, "
            f"{len(self.errors)} errors"
        )
        if self.passed:
            print(f"  RESULT: PASS  ({counts})")
        else:
            print(f"  RESULT: FAIL  ({counts})")
        print("=" * width)


def parse_tfvars(path: Path) -> dict:
    with open(path) as f:
        return hcl2.load(f)


def parse_sql_functions(path: Path) -> set[str]:
    """Extract function names from CREATE [OR REPLACE] FUNCTION statements."""
    text = path.read_text()
    pattern = re.compile(
        r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+"
        r"(?:[\w]+\.[\w]+\.)?"   # optional catalog.schema. prefix
        r"([\w]+)\s*\(",
        re.IGNORECASE,
    )
    return {m.group(1) for m in pattern.finditer(text)}


def validate_groups(cfg: dict, result: ValidationResult):
    groups = cfg.get("groups")
    if not groups:
        result.error("'groups' is missing or empty — at least one group is required")
        return set()
    if not isinstance(groups, dict):
        result.error("'groups' must be a map of group_name -> { description = \"...\" }")
        return set()
    for name, val in groups.items():
        if not isinstance(val, dict):
            result.error(f"groups[\"{name}\"] must be an object with a 'description' key")
    result.ok(f"groups: {len(groups)} group(s) defined")
    return set(groups.keys())


def validate_tag_policies(cfg: dict, result: ValidationResult) -> dict[str, set[str]]:
    """Returns a map of tag_key -> set of allowed values."""
    policies = cfg.get("tag_policies", [])
    if not isinstance(policies, list):
        result.error("'tag_policies' must be a list")
        return {}
    tag_map: dict[str, set[str]] = {}
    seen_keys: set[str] = set()
    for i, tp in enumerate(policies):
        key = tp.get("key", "")
        if not key:
            result.error(f"tag_policies[{i}]: 'key' is missing")
            continue
        if key in seen_keys:
            result.error(f"tag_policies[{i}]: duplicate key '{key}'")
        seen_keys.add(key)
        values = tp.get("values", [])
        if not values:
            result.error(f"tag_policies[{i}] (key='{key}'): 'values' is empty")
        tag_map[key] = set(values)
    result.ok(f"tag_policies: {len(policies)} policy/ies, {sum(len(v) for v in tag_map.values())} total values")
    return tag_map


def validate_tag_assignments(cfg: dict, tag_map: dict[str, set[str]], result: ValidationResult):
    assignments = cfg.get("tag_assignments", [])
    if not isinstance(assignments, list):
        result.error("'tag_assignments' must be a list")
        return
    seen_keys: set[str] = set()
    for i, ta in enumerate(assignments):
        prefix = f"tag_assignments[{i}]"
        etype = ta.get("entity_type", "")
        ename = ta.get("entity_name", "")
        tkey = ta.get("tag_key", "")
        tval = ta.get("tag_value", "")

        if etype not in VALID_ENTITY_TYPES:
            result.error(f"{prefix}: entity_type '{etype}' invalid — must be 'tables' or 'columns'")

        if etype == "tables" and "." in ename:
            result.error(
                f"{prefix}: entity_name '{ename}' looks like a column "
                f"(contains '.') but entity_type is 'tables' — use 'columns' or remove the dot"
            )
        if etype == "columns" and "." not in ename:
            result.error(
                f"{prefix}: entity_name '{ename}' has no '.' but entity_type is 'columns' "
                f"— expected 'Table.Column'"
            )
        if etype == "columns" and ename.count(".") > 1:
            result.error(
                f"{prefix}: entity_name '{ename}' has too many dots — "
                f"use relative name 'Table.Column' (catalog.schema is added by Terraform)"
            )

        if tkey and tkey not in tag_map:
            result.error(f"{prefix}: tag_key '{tkey}' not defined in tag_policies")
        elif tkey and tval and tval not in tag_map.get(tkey, set()):
            result.error(
                f"{prefix}: tag_value '{tval}' is not an allowed value for "
                f"tag_key '{tkey}' — allowed: {sorted(tag_map[tkey])}"
            )

        composite = f"{etype}|{ename}|{tkey}|{tval}"
        if composite in seen_keys:
            result.warn(f"{prefix}: duplicate assignment ({etype}, {ename}, {tkey}={tval})")
        seen_keys.add(composite)

    result.ok(f"tag_assignments: {len(assignments)} assignment(s)")


def validate_fgac_policies(
    cfg: dict,
    group_names: set[str],
    tag_map: dict[str, set[str]],
    sql_functions: set[str] | None,
    result: ValidationResult,
):
    policies = cfg.get("fgac_policies", [])
    if not isinstance(policies, list):
        result.error("'fgac_policies' must be a list")
        return
    seen_names: set[str] = set()
    referenced_functions: set[str] = set()

    for i, p in enumerate(policies):
        name = p.get("name", "")
        prefix = f"fgac_policies[{i}] (name='{name}')"
        ptype = p.get("policy_type", "")

        if not name:
            result.error(f"fgac_policies[{i}]: 'name' is missing")
        if name in seen_names:
            result.error(f"{prefix}: duplicate policy name")
        seen_names.add(name)

        if ptype not in VALID_POLICY_TYPES:
            result.error(f"{prefix}: policy_type '{ptype}' invalid — must be one of {sorted(VALID_POLICY_TYPES)}")
            continue

        provided = {k for k, v in p.items() if v is not None and v != "" and v != []}

        if ptype == "POLICY_TYPE_COLUMN_MASK":
            missing = COLUMN_MASK_REQUIRED - provided
            if missing:
                result.error(f"{prefix}: COLUMN_MASK requires {sorted(missing)}")
        elif ptype == "POLICY_TYPE_ROW_FILTER":
            missing = ROW_FILTER_REQUIRED - provided
            if missing:
                result.error(f"{prefix}: ROW_FILTER requires {sorted(missing)}")

        # Validate principals reference existing groups
        for principal in p.get("to_principals", []):
            if principal.lower() not in BUILTIN_PRINCIPALS and principal not in group_names:
                result.error(
                    f"{prefix}: to_principals group '{principal}' not defined in 'groups'"
                )
        for principal in p.get("except_principals", []) or []:
            if principal.lower() not in BUILTIN_PRINCIPALS and principal not in group_names:
                result.error(
                    f"{prefix}: except_principals group '{principal}' not defined in 'groups'"
                )

        # Validate condition syntax — only hasTagValue() and hasTag() are allowed
        condition = p.get("match_condition") or p.get("when_condition") or ""
        for forbidden in ["columnName()", "tableName()", " IN (", " IN("]:
            if forbidden in condition:
                result.error(
                    f"{prefix}: condition contains '{forbidden}' which is NOT supported "
                    f"by Databricks ABAC. Only hasTagValue() and hasTag() are allowed."
                )
        for tag_ref in re.findall(r"hasTagValue\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", condition):
            ref_key, ref_val = tag_ref
            if ref_key not in tag_map:
                result.error(f"{prefix}: condition references undefined tag_key '{ref_key}'")
            elif ref_val not in tag_map.get(ref_key, set()):
                result.error(
                    f"{prefix}: condition references tag_value '{ref_val}' "
                    f"not in tag_policy '{ref_key}' — allowed: {sorted(tag_map[ref_key])}"
                )
        for tag_ref in re.findall(r"hasTag\(\s*'([^']+)'\s*\)", condition):
            if tag_ref not in tag_map:
                result.error(f"{prefix}: condition references undefined tag_key '{tag_ref}'")

        fn = p.get("function_name", "")
        if fn:
            referenced_functions.add(fn)
            if "." in fn:
                result.error(
                    f"{prefix}: function_name '{fn}' should be relative (no dots) — "
                    f"Terraform prepends catalog.schema automatically"
                )

    # Cross-reference with SQL file
    if sql_functions is not None:
        for fn in referenced_functions:
            if fn not in sql_functions:
                result.error(
                    f"function '{fn}' referenced in fgac_policies but not found "
                    f"in SQL file — define it with CREATE OR REPLACE FUNCTION {fn}(...)"
                )
        unused = sql_functions - referenced_functions
        if unused:
            result.warn(
                f"SQL file defines functions not used by any policy: {sorted(unused)}. "
                f"These will be created but won't mask anything."
            )

    result.ok(f"fgac_policies: {len(policies)} policy/ies, {len(referenced_functions)} unique function(s)")


def validate_group_members(cfg: dict, group_names: set[str], result: ValidationResult):
    members = cfg.get("group_members", {})
    if not isinstance(members, dict):
        result.error("'group_members' must be a map of group_name -> list of user IDs")
        return
    for grp, ids in members.items():
        if grp not in group_names:
            result.error(f"group_members: group '{grp}' not defined in 'groups'")
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            result.error(f"group_members[\"{grp}\"]: must be a list of user ID strings")
    if members:
        result.ok(f"group_members: {len(members)} group(s) with member assignments")


def _find_auth_file(tfvars_path: Path) -> Path | None:
    """Locate auth.auto.tfvars relative to the given tfvars file."""
    candidates = [
        tfvars_path.parent / "auth.auto.tfvars",
        tfvars_path.parent.parent / "auth.auto.tfvars",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def validate_auth(cfg: dict, result: ValidationResult, tfvars_path: Path):
    required = [
        "databricks_account_id",
        "databricks_client_id",
        "databricks_client_secret",
        "databricks_workspace_id",
        "databricks_workspace_host",
        "uc_catalog_name",
        "uc_schema_name",
    ]

    auth_cfg = cfg
    if not any(k in cfg for k in required):
        auth_file = _find_auth_file(tfvars_path)
        if auth_file:
            try:
                auth_cfg = parse_tfvars(auth_file)
                result.ok(
                    f"Auth vars loaded from {auth_file.name}"
                )
            except Exception as e:
                result.warn(f"Could not parse {auth_file}: {e}")
                return
        else:
            result.warn(
                "Auth vars not in tfvars and auth.auto.tfvars not found."
            )
            return

    for key in required:
        val = auth_cfg.get(key, "")
        if not val:
            result.warn(f"'{key}' is empty — fill in before terraform apply")
        else:
            result.ok(f"{key}: set")


def main():
    parser = argparse.ArgumentParser(
        description="Validate AI-generated ABAC configuration files",
        epilog="Example: python validate_abac.py terraform.tfvars masking_functions.sql",
    )
    parser.add_argument("tfvars", help="Path to terraform.tfvars file")
    parser.add_argument("sql", nargs="?", help="Path to masking_functions.sql (optional)")
    args = parser.parse_args()

    tfvars_path = Path(args.tfvars)
    sql_path = Path(args.sql) if args.sql else None

    if not tfvars_path.exists():
        print(f"ERROR: {tfvars_path} not found")
        sys.exit(1)

    result = ValidationResult()

    # --- Parse tfvars ---
    try:
        cfg = parse_tfvars(tfvars_path)
    except Exception as e:
        result.error(f"Failed to parse {tfvars_path}: {e}")
        result.print_report()
        sys.exit(1)

    # --- Parse SQL (optional) ---
    sql_functions: set[str] | None = None
    if sql_path:
        if not sql_path.exists():
            result.error(f"SQL file {sql_path} not found")
        else:
            sql_functions = parse_sql_functions(sql_path)
            if not sql_functions:
                result.warn(
                    f"No CREATE FUNCTION statements found in {sql_path} — "
                    f"is it the right file?"
                )
            else:
                result.ok(f"SQL file: {len(sql_functions)} function(s) found — {sorted(sql_functions)}")

    # --- Run validations ---
    validate_auth(cfg, result, tfvars_path)
    group_names = validate_groups(cfg, result)
    tag_map = validate_tag_policies(cfg, result)
    validate_tag_assignments(cfg, tag_map, result)
    validate_fgac_policies(cfg, group_names, tag_map, sql_functions, result)
    validate_group_members(cfg, group_names, result)

    result.print_report()
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
