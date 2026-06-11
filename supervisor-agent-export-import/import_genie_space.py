#!/usr/bin/env python3
"""Import a Databricks Genie Space from an exported directory.

The export directory is expected to contain:
  - definition.json   (title, description, warehouse_id)
  - serialized.json    (the full serialized_space payload)

This mirrors the genie-room handling in import_supervisor_agent.py, but as a
standalone tool for a single Genie Space.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def parse_catalog_map(raw: str | None) -> list[tuple[str, str]]:
    """Parse --catalog-map into a sorted list of (old_prefix, new_prefix) rules.

    Rules are sorted by prefix length descending so longer (more specific)
    prefixes match first.
    """
    if not raw:
        return []
    rules = []
    for entry in raw.split(","):
        entry = entry.strip()
        if "=" not in entry:
            log.warning("Skipping invalid catalog-map entry (no '='): '%s'", entry)
            continue
        old, new = entry.split("=", 1)
        rules.append((old.strip(), new.strip()))
    # Sort by prefix length descending — longer prefixes match first
    rules.sort(key=lambda r: len(r[0]), reverse=True)
    return rules


def apply_catalog_map(name: str, rules: list[tuple[str, str]]) -> str:
    """Apply catalog map rules to a fully-qualified name (catalog.schema.table).

    Returns the rewritten name, or the original if no rule matches.
    """
    for old_prefix, new_prefix in rules:
        if name.startswith(old_prefix + "."):
            return new_prefix + name[len(old_prefix):]
    return name


def apply_catalog_map_to_text(text: str, rules: list[tuple[str, str]]) -> str:
    """Apply catalog mapping rules to free-form text or SQL.

    For each rule `old_prefix=new_prefix`, replaces occurrences of
    `<old_prefix>.<rest>` with `<new_prefix>.<rest>` using a left word-boundary
    so we don't match inside longer identifiers (e.g. `my_old_prefix.` won't
    match the `old_prefix=` rule). Rules are already sorted by prefix-length
    descending, so longer (more specific) prefixes match first.
    """
    if not text or not rules:
        return text
    for old_prefix, new_prefix in rules:
        pattern = re.compile(r"(?<![\w.])" + re.escape(old_prefix) + r"\.")
        text = pattern.sub(new_prefix + ".", text)
    return text


def rewrite_serialized_genie_space(serialized: dict, rules: list[tuple[str, str]]) -> None:
    """Apply catalog mapping rules to every place in a serialized Genie space
    that can contain fully-qualified table references. Mutates `serialized`
    in place.

    Covers:
      - data_sources.tables[].identifier (the table being registered)
      - data_sources.tables[].description (per-table descriptions, freeform text)
      - instructions.text_instructions[].content (freeform text)
      - instructions.example_question_sqls[].sql (SQL strings)
      - benchmarks.questions[].answer[].content (canonical SQL strings)
    """
    if not rules:
        return

    # Table identifiers (exact FQ name) and per-table descriptions (freeform text)
    for table in serialized.get("data_sources", {}).get("tables", []) or []:
        old_id = table.get("identifier", "")
        new_id = apply_catalog_map(old_id, rules)
        if new_id != old_id:
            log.info("  Table mapping: %s -> %s", old_id, new_id)
            table["identifier"] = new_id
        desc = table.get("description")
        if isinstance(desc, list):
            table["description"] = [apply_catalog_map_to_text(s, rules) for s in desc]

    # Text instructions and example SQL queries
    instr = serialized.get("instructions", {}) or {}
    for ti in instr.get("text_instructions", []) or []:
        content = ti.get("content")
        if isinstance(content, list):
            ti["content"] = [apply_catalog_map_to_text(s, rules) for s in content]
    for eq in instr.get("example_question_sqls", []) or []:
        sql = eq.get("sql")
        if isinstance(sql, list):
            eq["sql"] = [apply_catalog_map_to_text(s, rules) for s in sql]

    # Benchmark question canonical SQL
    for bq in serialized.get("benchmarks", {}).get("questions", []) or []:
        for ans in bq.get("answer", []) or []:
            content = ans.get("content")
            if isinstance(content, list):
                ans["content"] = [apply_catalog_map_to_text(s, rules) for s in content]


def _canonical(x):
    """Strip server-side noise from a serialized-space subtree for comparison:
    drop empty/null/false values, strip string whitespace, and sort
    order-irrelevant lists of dicts/lists.
    """
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            cv = _canonical(v)
            if cv in (None, "", [], {}, False):
                continue
            out[k] = cv
        return out
    if isinstance(x, list):
        items = [_canonical(v) for v in x]
        if items and all(isinstance(i, (dict, list)) for i in items):
            items = sorted(items, key=lambda i: json.dumps(i, sort_keys=True))
        return items
    if isinstance(x, str):
        return x.strip()
    return x


def _table_columns(table: dict) -> dict:
    """Map column_name -> frozenset of enabled (truthy) flags for a table's column_configs."""
    cols = {}
    for c in (table.get("column_configs") or []):
        name = c.get("column_name")
        if name is None:
            continue
        cols[name] = frozenset(
            k for k, v in c.items()
            if k != "column_name" and v not in (None, "", False, [], {})
        )
    return cols


def serialized_spaces_differ(existing_raw: str | None, expected_raw: str | None) -> bool:
    """True if two serialized_space payloads differ in user-authored content.

    serialized_space is normalized per workspace, so the form the target stores
    and returns is not byte- or structure-identical to what we send, even for the
    same logical space. Crucially, the target's Genie service drops column_configs
    for columns its tables don't have -- re-sending them never converges. A raw or
    naive structural comparison therefore yields false "differs" results forever.

    This compares only user-authored, convergent content:
      - tables matched by identifier (not order); a differing table set => differs
      - per-table description compared canonically
      - column_configs matched by column_name, compared only for columns present
        on BOTH sides (a config the target dropped can't be pushed back, so it is
        not an actionable difference)
      - everything else (version, instructions, example SQL, benchmarks) compared
        canonically -- whitespace-, order-, and default-insensitive

    Falls back to a raw string compare if either side isn't valid JSON.
    """
    try:
        live = json.loads(existing_raw) if existing_raw else None
        exp = json.loads(expected_raw) if expected_raw else None
    except json.JSONDecodeError:
        return (existing_raw or "") != (expected_raw or "")
    if live is None or exp is None:
        return live != exp

    live_tables = {t.get("identifier", ""): t
                   for t in (live.get("data_sources", {}).get("tables") or [])}
    exp_tables = {t.get("identifier", ""): t
                  for t in (exp.get("data_sources", {}).get("tables") or [])}
    if set(live_tables) != set(exp_tables):
        return True
    for ident, et in exp_tables.items():
        lt = live_tables[ident]
        if _canonical(lt.get("description")) != _canonical(et.get("description")):
            return True
        lc, ec = _table_columns(lt), _table_columns(et)
        for col in (set(lc) & set(ec)):
            if lc[col] != ec[col]:
                return True

    # Compare everything outside data_sources.tables canonically.
    def _rest(s):
        ds = {k: v for k, v in (s.get("data_sources") or {}).items() if k != "tables"}
        rest = {k: v for k, v in s.items() if k != "data_sources"}
        rest["data_sources"] = ds
        return _canonical(rest)
    return _rest(live) != _rest(exp)


# Conflict resolution decisions
CONFLICT_UPDATE = "update"
CONFLICT_SKIP = "skip"


def resolve_conflict(entity_kind: str, entity_name: str, diff_lines: list[str],
                     yes_update: bool, skip_existing: bool) -> str:
    """Decide whether to update or skip an existing entity that differs from the export.

    Returns CONFLICT_UPDATE or CONFLICT_SKIP.
    """
    if yes_update:
        log.info("%s '%s' differs; updating (--yes-update).", entity_kind, entity_name)
        return CONFLICT_UPDATE
    if skip_existing:
        log.info("%s '%s' differs; skipping (--skip-existing).", entity_kind, entity_name)
        return CONFLICT_SKIP

    # Interactive
    print(f"\n{entity_kind} '{entity_name}' differs from export:")
    for line in diff_lines:
        print(f"  {line}")
    while True:
        try:
            answer = input("Update? [y/N/s(kip)]: ").strip().lower()
        except EOFError:
            log.error("Cannot prompt: stdin closed.")
            sys.exit(1)
        if answer in ("y", "yes"):
            return CONFLICT_UPDATE
        if answer in ("", "n", "no"):
            log.error("User declined update for %s '%s'; aborting.", entity_kind, entity_name)
            sys.exit(1)
        if answer in ("s", "skip"):
            return CONFLICT_SKIP
        print("Please answer y, n, or s.")


def short_diff(name: str, old, new) -> str:
    """Format a single field diff for display.

    Long strings are summarized by length to keep the prompt readable.
    """
    LIMIT = 60
    if isinstance(old, str) and isinstance(new, str) and (len(old) > LIMIT or len(new) > LIMIT):
        return f"{name}: changed ({len(old)} chars -> {len(new)} chars)"
    return f"{name}: {old!r} -> {new!r}"


def find_existing_genie_space(w: WorkspaceClient, title: str):
    """Return the existing GenieSpace summary if one matches by title, else None."""
    page_token = None
    while True:
        resp = w.genie.list_spaces(page_token=page_token)
        for space in (resp.spaces or []):
            if space.title == title:
                return space
        page_token = resp.next_page_token
        if not page_token:
            break
    return None


def resolve_warehouse_id(w: WorkspaceClient, warehouse_id: str | None,
                         warehouse_name: str | None) -> str:
    """Return a warehouse ID, looking it up by name if only a name was given.

    Exits with an error if the name doesn't resolve to exactly one warehouse.
    """
    if warehouse_id:
        return warehouse_id
    matches = [wh for wh in w.warehouses.list() if wh.name == warehouse_name]
    if not matches:
        log.error("No SQL warehouse named '%s' found in the target workspace.", warehouse_name)
        sys.exit(1)
    if len(matches) > 1:
        log.error("Multiple SQL warehouses named '%s' (ids: %s); use --warehouse-id to disambiguate.",
                  warehouse_name, ", ".join(m.id for m in matches))
        sys.exit(1)
    log.info("Resolved warehouse '%s' to id %s", warehouse_name, matches[0].id)
    return matches[0].id


def preflight_check(w: WorkspaceClient, serialized: dict,
                    catalog_rules: list[tuple[str, str]], force: bool) -> None:
    """Validate that all referenced UC tables exist before importing.

    Applies catalog mapping to each table identifier, then checks existence.
    Aborts (unless --force) if any are missing.
    """
    missing: list[str] = []
    for table in serialized.get("data_sources", {}).get("tables", []) or []:
        old_id = table.get("identifier", "")
        if not old_id:
            continue
        name = apply_catalog_map(old_id, catalog_rules)
        try:
            w.tables.get(name)
        except Exception as e:
            log.warning("Table '%s' not found or not verifiable: %s", name, e)
            missing.append(name)

    if missing:
        log.error("Pre-flight check found missing tables:")
        for t in missing:
            log.error("    - %s", t)
        if not force:
            log.error("Aborting. Re-run with --force to import anyway.")
            sys.exit(1)
        log.warning("Proceeding despite missing tables (--force).")
    else:
        log.info("Pre-flight check passed: all referenced tables exist.")


def resolve_genie_space(w: WorkspaceClient, input_dir: Path, warehouse_id: str,
                        catalog_rules: list[tuple[str, str]],
                        yes_update: bool, skip_existing: bool,
                        force: bool) -> str | None:
    """Create, reuse, or update a Genie space from an export directory.

    Returns the new/existing space_id, or None on failure / explicit skip.
    """
    def_path = input_dir / "definition.json"
    serialized_path = input_dir / "serialized.json"

    if not def_path.exists() or not serialized_path.exists():
        log.error("Expected definition.json and serialized.json in %s", input_dir)
        return None

    definition = json.loads(def_path.read_text())
    serialized_raw = serialized_path.read_text()
    title = definition.get("title", "")
    description = definition.get("description", "")
    log.info("Resolving genie space '%s'", title)

    # Apply catalog map to all FQ table references in the serialized space:
    # identifiers, per-table descriptions, text instructions, example SQL,
    # and benchmark canonical SQL.
    serialized = None
    if serialized_raw:
        try:
            serialized = json.loads(serialized_raw)
        except json.JSONDecodeError as e:
            log.warning("Failed to parse serialized.json: %s", e)

    if serialized is not None:
        if catalog_rules:
            rewrite_serialized_genie_space(serialized, catalog_rules)
        serialized_raw = json.dumps(serialized)
        preflight_check(w, serialized, catalog_rules, force)

    existing = find_existing_genie_space(w, title)
    if existing is None:
        try:
            space = w.genie.create_space(
                warehouse_id=warehouse_id,
                serialized_space=serialized_raw,
                title=title,
                description=description,
            )
            log.info("Created genie space '%s' (id: %s)", title, space.space_id)
            return space.space_id
        except Exception as e:
            log.error("Failed to create genie space '%s': %s", title, e)
            return None

    # Existing space found: compare via Get (List doesn't include serialized_space)
    space_id = existing.space_id
    try:
        full = w.genie.get_space(space_id, include_serialized_space=True)
    except Exception as e:
        log.error("Failed to fetch genie space '%s' for comparison: %s", title, e)
        return space_id

    diff_lines: list[str] = []
    if (full.title or "") != title:
        diff_lines.append(short_diff("title", full.title or "", title))
    if (full.description or "") != description:
        diff_lines.append(short_diff("description", full.description or "", description))
    if (full.warehouse_id or "") != warehouse_id:
        diff_lines.append(short_diff("warehouse_id", full.warehouse_id or "", warehouse_id))
    # Compare serialized_space by user-authored content, ignoring server-side
    # normalization (pretty-printing, reordered/defaulted configs, etc.).
    if serialized_spaces_differ(full.serialized_space, serialized_raw):
        diff_lines.append("serialized_space: content differs")

    if not diff_lines:
        log.info("Genie space '%s' already matches export (id: %s); reusing.", title, space_id)
        return space_id

    decision = resolve_conflict("Genie space", title, ["Top-level fields:"] + [f"  {d}" for d in diff_lines],
                                yes_update, skip_existing)
    if decision == CONFLICT_SKIP:
        return space_id

    try:
        w.genie.update_space(
            space_id,
            title=title,
            description=description,
            warehouse_id=warehouse_id,
            serialized_space=serialized_raw,
        )
        log.info("Updated genie space '%s' (id: %s)", title, space_id)
    except Exception as e:
        log.error("Failed to update genie space '%s': %s", title, e)

    return space_id


def main():
    parser = argparse.ArgumentParser(
        description="Import a Databricks Genie Space from an exported directory."
    )
    parser.add_argument(
        "--input-dir", required=True,
        help="Path to the exported genie space directory "
             "(containing definition.json and serialized.json)",
    )
    wh_group = parser.add_mutually_exclusive_group(required=True)
    wh_group.add_argument(
        "--warehouse-id",
        help="SQL warehouse ID for the genie space in the target workspace",
    )
    wh_group.add_argument(
        "--warehouse-name",
        help="SQL warehouse name to look up the ID by (alternative to --warehouse-id)",
    )
    parser.add_argument(
        "--catalog-map",
        help="Comma-separated catalog mapping rules: old=new "
             "(e.g. dsl_dlt=new_cat,old.schema=new.schema)",
    )
    parser.add_argument(
        "--yes-update", action="store_true",
        help="Always update an existing space without prompting "
             "(mutually exclusive with --skip-existing)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Never update an existing space, always reuse it "
             "(mutually exclusive with --yes-update)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip pre-flight dependency checks; proceed even if referenced tables are missing",
    )
    args = parser.parse_args()

    if args.yes_update and args.skip_existing:
        log.error("--yes-update and --skip-existing are mutually exclusive")
        sys.exit(2)

    input_dir = Path(args.input_dir)
    if not (input_dir / "definition.json").exists():
        log.error("definition.json not found in %s", input_dir)
        sys.exit(1)

    interactive = not (args.yes_update or args.skip_existing)
    if interactive and not sys.stdin.isatty():
        log.error(
            "stdin is not a terminal and no --yes-update / --skip-existing flag was provided. "
            "Choose one when running non-interactively."
        )
        sys.exit(2)

    try:
        w = WorkspaceClient()
        log.info("Connected to %s", w.config.host)

        catalog_rules = parse_catalog_map(args.catalog_map)
        warehouse_id = resolve_warehouse_id(w, args.warehouse_id, args.warehouse_name)

        space_id = resolve_genie_space(
            w, input_dir,
            warehouse_id, catalog_rules,
            yes_update=args.yes_update,
            skip_existing=args.skip_existing,
            force=args.force,
        )
        if space_id is None:
            log.error("Import failed.")
            sys.exit(1)
        log.info("Import complete. Genie space id: %s", space_id)
    except SystemExit:
        raise
    except Exception as e:
        log.error("Import failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
