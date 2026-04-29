#!/usr/bin/env python3
"""Import a Databricks Supervisor Agent and its tools from an exported directory."""

import argparse
import json
import logging
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

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


def parse_name_map(raw: str | None) -> dict[str, str]:
    """Parse a comma-separated 'old=new' name map into a dict.

    Skips entries without '=' (logs a warning).
    """
    if not raw:
        return {}
    out: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if "=" not in entry:
            log.warning("Skipping invalid name-map entry (no '='): '%s'", entry)
            continue
        old, new = entry.split("=", 1)
        out[old.strip()] = new.strip()
    return out


def apply_name_map(name: str, mapping: dict[str, str]) -> str:
    """Return mapping[name] if present, else name unchanged."""
    return mapping.get(name, name)


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


def parse_volume_path(volume_path: str) -> str:
    """Parse a volume path like '/Volumes/cat/schema/vol' into a 3-part name 'cat.schema.vol'."""
    parts = volume_path.strip("/").split("/")
    if len(parts) < 4 or parts[0] != "Volumes":
        raise ValueError(f"Invalid volume path: {volume_path!r} (expected /Volumes/cat/schema/vol)")
    return f"{parts[1]}.{parts[2]}.{parts[3]}"


def preflight_check(w: WorkspaceClient, manifest: dict, input_dir: Path,
                    volume_path: str, catalog_rules: list[tuple[str, str]],
                    connection_map: dict[str, str], app_map: dict[str, str],
                    force: bool) -> None:
    """Validate that all referenced UC objects exist before starting the import.

    Collects all missing references and reports them together. Exits non-zero
    unless --force is set.
    """
    log.info("Running pre-flight checks...")
    missing_volumes: list[str] = []
    missing_tables: list[str] = []
    missing_indexes: list[str] = []
    missing_functions: list[str] = []
    missing_connections: list[str] = []
    missing_apps: list[str] = []
    skipped_index_checks: list[str] = []

    # Volume
    try:
        vol_full = parse_volume_path(volume_path)
        try:
            w.volumes.read(vol_full)
        except NotFound:
            missing_volumes.append(vol_full)
        except Exception as e:
            log.warning("Could not verify volume '%s': %s; treating as missing", vol_full, e)
            missing_volumes.append(vol_full)
    except ValueError as e:
        log.error("%s", e)
        sys.exit(2)

    # Walk tools
    for tool in manifest.get("tools", []):
        if tool.get("skipped"):
            continue
        tool_type = tool.get("tool_type")

        if tool_type == "genie_space":
            export_dir = input_dir / tool["export_dir"]
            serialized_path = export_dir / "serialized.json"
            if not serialized_path.exists():
                continue
            try:
                serialized = json.loads(serialized_path.read_text())
            except json.JSONDecodeError:
                continue
            for table in serialized.get("data_sources", {}).get("tables", []):
                old_id = table.get("identifier", "")
                if not old_id:
                    continue
                new_id = apply_catalog_map(old_id, catalog_rules)
                try:
                    resp = w.tables.exists(new_id)
                    if not getattr(resp, "table_exists", False):
                        missing_tables.append(new_id)
                except Exception as e:
                    log.warning("Could not verify table '%s': %s; treating as missing", new_id, e)
                    missing_tables.append(new_id)

        elif tool_type == "knowledge_assistant":
            export_dir = input_dir / tool["export_dir"]
            def_path = export_dir / "definition.json"
            if not def_path.exists():
                continue
            try:
                definition = json.loads(def_path.read_text())
            except json.JSONDecodeError:
                continue
            for source in definition.get("knowledge_sources", []):
                stype = source.get("source_type")
                if stype == "file_table":
                    name = apply_catalog_map(source.get("file_table", {}).get("table_name", ""), catalog_rules)
                    if not name:
                        continue
                    try:
                        resp = w.tables.exists(name)
                        if not getattr(resp, "table_exists", False):
                            missing_tables.append(name)
                    except Exception as e:
                        log.warning("Could not verify table '%s': %s; treating as missing", name, e)
                        missing_tables.append(name)
                elif stype == "index":
                    name = apply_catalog_map(source.get("index", {}).get("index_name", ""), catalog_rules)
                    if not name:
                        continue
                    try:
                        w.vector_search_indexes.get_index(name)
                    except NotFound:
                        missing_indexes.append(name)
                    except AttributeError:
                        skipped_index_checks.append(name)
                    except Exception as e:
                        log.warning("Could not verify vector index '%s': %s; treating as missing", name, e)
                        missing_indexes.append(name)

        elif tool_type == "uc_function":
            name = apply_catalog_map(tool.get("uc_function", {}).get("name", ""), catalog_rules)
            if not name:
                continue
            try:
                w.functions.get(name)
            except NotFound:
                missing_functions.append(name)
            except Exception as e:
                log.warning("Could not verify UC function '%s': %s; treating as missing", name, e)
                missing_functions.append(name)
        elif tool_type == "connection":
            name = apply_name_map(tool.get("connection", {}).get("name", ""), connection_map)
            if not name:
                continue
            try:
                w.connections.get(name)
            except NotFound:
                missing_connections.append(name)
            except Exception as e:
                log.warning("Could not verify connection '%s': %s; treating as missing", name, e)
                missing_connections.append(name)
        elif tool_type == "app":
            name = apply_name_map(tool.get("app", {}).get("name", ""), app_map)
            if not name:
                continue
            try:
                w.apps.get(name)
            except NotFound:
                missing_apps.append(name)
            except Exception as e:
                log.warning("Could not verify app '%s': %s; treating as missing", name, e)
                missing_apps.append(name)

    if skipped_index_checks:
        log.warning("Vector search index existence check unavailable; not verified: %s", skipped_index_checks)

    any_missing = (missing_volumes or missing_tables or missing_indexes
                   or missing_functions or missing_connections or missing_apps)
    if any_missing:
        log.error("Pre-flight check failed. Missing dependencies in target workspace:")
        if missing_volumes:
            log.error("  Volumes:")
            for v in missing_volumes:
                log.error("    - %s", v)
        if missing_tables:
            log.error("  Tables:")
            for t in missing_tables:
                log.error("    - %s", t)
        if missing_indexes:
            log.error("  Vector search indexes:")
            for i in missing_indexes:
                log.error("    - %s", i)
        if missing_functions:
            log.error("  UC functions:")
            for f in missing_functions:
                log.error("    - %s", f)
        if missing_connections:
            log.error("  Connections:")
            for c in missing_connections:
                log.error("    - %s", c)
        if missing_apps:
            log.error("  Apps:")
            for a in missing_apps:
                log.error("    - %s", a)
        if not force:
            log.error("Re-run with --force to proceed despite missing dependencies, or create the missing objects first.")
            sys.exit(1)
        log.warning("--force set; proceeding despite missing dependencies.")
    else:
        log.info("Pre-flight checks passed.")


def list_supervisor_agents(w: WorkspaceClient) -> list[dict]:
    """List all supervisor agents (paginated)."""
    results = []
    page_token = None
    while True:
        query = {}
        if page_token:
            query["page_token"] = page_token
        resp = w.api_client.do("GET", "/api/2.1/supervisor-agents", query=query)
        results.extend(resp.get("supervisor_agents", []))
        page_token = resp.get("next_page_token")
        if not page_token:
            break
    return results


def find_existing_supervisor_agent(w: WorkspaceClient, display_name: str) -> dict | None:
    """Return the existing supervisor agent dict if one matches by display_name, else None."""
    for agent in list_supervisor_agents(w):
        if agent.get("display_name") == display_name:
            return agent
    return None


def list_knowledge_assistants(w: WorkspaceClient) -> list[dict]:
    """List all knowledge assistants (paginated)."""
    results = []
    page_token = None
    while True:
        query = {}
        if page_token:
            query["page_token"] = page_token
        resp = w.api_client.do("GET", "/api/2.1/knowledge-assistants", query=query)
        results.extend(resp.get("knowledge_assistants", []))
        page_token = resp.get("next_page_token")
        if not page_token:
            break
    return results


def find_existing_knowledge_assistant(w: WorkspaceClient, display_name: str) -> dict | None:
    """Return the existing KA dict if one matches by display_name, else None."""
    for ka in list_knowledge_assistants(w):
        if ka.get("display_name") == display_name:
            return ka
    return None


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


def list_knowledge_sources(w: WorkspaceClient, ka_id: str) -> list[dict]:
    """List all knowledge sources for a KA (paginated)."""
    results = []
    page_token = None
    while True:
        query = {}
        if page_token:
            query["page_token"] = page_token
        resp = w.api_client.do(
            "GET", f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources", query=query
        )
        results.extend(resp.get("knowledge_sources", []))
        page_token = resp.get("next_page_token")
        if not page_token:
            break
    return results


def list_agent_tools(w: WorkspaceClient, agent_id: str) -> list[dict]:
    """List all tools for a supervisor agent (paginated)."""
    results = []
    page_token = None
    while True:
        query = {}
        if page_token:
            query["page_token"] = page_token
        resp = w.api_client.do(
            "GET", f"/api/2.1/supervisor-agents/{agent_id}/tools", query=query
        )
        results.extend(resp.get("tools", []))
        page_token = resp.get("next_page_token")
        if not page_token:
            break
    return results


def build_expected_source(source: dict, tool_id: str, volume_path: str,
                          catalog_rules: list[tuple[str, str]]) -> dict:
    """Build the expected target-workspace source body from an exported source dict.

    Returns a dict with keys: display_name, description, source_type, and the
    type-specific spec (files | index | file_table). The 'files.path' is
    rewritten to the target volume path for comparison purposes.
    """
    stype = source.get("source_type", "unknown")
    body = {
        "display_name": source.get("display_name", ""),
        "description": source.get("description", ""),
        "source_type": stype,
    }
    if stype == "files":
        local_dir_rel = source.get("local_dir", "")
        dir_basename = Path(local_dir_rel).name
        body["files"] = {"path": f"{volume_path}/{tool_id}/{dir_basename}"}
    elif stype == "index":
        idx = source.get("index", {})
        body["index"] = {
            "index_name": apply_catalog_map(idx.get("index_name", ""), catalog_rules),
            "text_col": idx.get("text_col", ""),
            "doc_uri_col": idx.get("doc_uri_col", ""),
        }
    elif stype == "file_table":
        ft = source.get("file_table", {})
        body["file_table"] = {
            "table_name": apply_catalog_map(ft.get("table_name", ""), catalog_rules),
            "file_col": ft.get("file_col", ""),
        }
    return body


def normalize_existing_source(source: dict) -> dict:
    """Project an existing-on-target source dict to the same shape as build_expected_source."""
    stype = source.get("source_type", "unknown")
    body = {
        "display_name": source.get("display_name", ""),
        "description": source.get("description", ""),
        "source_type": stype,
    }
    if stype == "files":
        body["files"] = {"path": source.get("files", {}).get("path", "")}
    elif stype == "index":
        idx = source.get("index", {})
        body["index"] = {
            "index_name": idx.get("index_name", ""),
            "text_col": idx.get("text_col", ""),
            "doc_uri_col": idx.get("doc_uri_col", ""),
        }
    elif stype == "file_table":
        ft = source.get("file_table", {})
        body["file_table"] = {
            "table_name": ft.get("table_name", ""),
            "file_col": ft.get("file_col", ""),
        }
    return body


def diff_knowledge_sources(expected: list[dict], existing: list[dict]) -> dict:
    """Compute the source-level diff between expected and existing KA sources.

    Both lists are projected dicts (from build_expected_source / normalize_existing_source).
    Match by display_name. Aborts on duplicate display_names within either list.

    Returns dict with keys: to_add, to_remove, to_update (each a list).
    to_update items are dicts: {"existing": existing_dict, "expected": expected_dict}
    """
    def index_by_name(items: list[dict], side: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for it in items:
            name = it.get("display_name", "")
            if name in out:
                log.error("Duplicate knowledge source display_name on %s side: '%s'", side, name)
                sys.exit(1)
            out[name] = it
        return out

    exp_idx = index_by_name(expected, "expected")
    cur_idx = index_by_name(existing, "existing")

    to_add = [exp_idx[n] for n in exp_idx if n not in cur_idx]
    to_remove = [cur_idx[n] for n in cur_idx if n not in exp_idx]
    to_update = []
    for n in exp_idx:
        if n in cur_idx and exp_idx[n] != cur_idx[n]:
            to_update.append({"existing": cur_idx[n], "expected": exp_idx[n]})
    return {"to_add": to_add, "to_remove": to_remove, "to_update": to_update}


def _delete_remote_recursive(w: WorkspaceClient, remote_dir: str) -> None:
    """Recursively delete a remote directory's contents and the directory itself.

    UC volume directory deletes require the directory to be empty, so we
    first delete contents (recursively) before deleting the directory.
    """
    try:
        entries = list(w.files.list_directory_contents(remote_dir))
    except Exception as e:
        log.warning("Failed to list remote directory '%s' for deletion: %s", remote_dir, e)
        return

    for entry in entries:
        entry_path = entry.path
        if getattr(entry, "is_directory", False):
            _delete_remote_recursive(w, entry_path)
        else:
            try:
                w.files.delete(entry_path)
                log.info("Deleted (no longer in export): %s", entry_path)
            except Exception as e:
                log.warning("Failed to delete remote file '%s': %s", entry_path, e)

    try:
        w.files.delete_directory(remote_dir)
        log.info("Deleted directory (no longer in export): %s", remote_dir)
    except Exception as e:
        log.warning("Failed to delete remote directory '%s': %s", remote_dir, e)


def sync_directory(w: WorkspaceClient, local_dir: Path, remote_dir: str) -> None:
    """Reconcile a local directory tree to a UC volume path.

    - Skips files whose remote size matches the local size (no upload).
    - Uploads missing files and files whose size differs.
    - Deletes remote files that no longer exist locally.
    - Deletes remote subdirectories that no longer exist locally.
    - Recurses into subdirectories.
    """
    if not local_dir.exists():
        log.warning("Local directory does not exist: %s", local_dir)
        return

    # Ensure remote directory exists (mkdir -p semantics)
    try:
        w.files.create_directory(remote_dir)
    except Exception as e:
        log.warning("Failed to create remote directory '%s': %s", remote_dir, e)

    # Index local entries
    local_files: dict[str, Path] = {}
    local_subdirs: dict[str, Path] = {}
    for item in sorted(local_dir.iterdir()):
        if item.is_dir():
            local_subdirs[item.name] = item
        else:
            local_files[item.name] = item

    # Index remote entries
    remote_files: dict[str, dict] = {}  # name -> {"path": ..., "size": ...}
    remote_subdirs: dict[str, str] = {}  # name -> path
    try:
        for entry in w.files.list_directory_contents(remote_dir):
            entry_name = (entry.name or entry.path.rstrip("/").rsplit("/", 1)[-1])
            if getattr(entry, "is_directory", False):
                remote_subdirs[entry_name] = entry.path
            else:
                remote_files[entry_name] = {
                    "path": entry.path,
                    "size": getattr(entry, "file_size", None),
                }
    except Exception as e:
        log.warning("Failed to list remote directory '%s': %s", remote_dir, e)

    # Reconcile files
    for name, local_path in local_files.items():
        remote_path = f"{remote_dir}/{name}"
        local_size = local_path.stat().st_size

        if name in remote_files:
            remote_size = remote_files[name]["size"]
            if remote_size == local_size:
                log.info("Unchanged (size match): %s (%d bytes)", remote_path, local_size)
                continue
            try:
                with open(local_path, "rb") as f:
                    w.files.upload(remote_path, f, overwrite=True)
                log.info("Uploaded (size changed): %s (%s -> %d bytes)",
                         remote_path, remote_size, local_size)
            except Exception as e:
                log.warning("Failed to upload '%s': %s", remote_path, e)
        else:
            try:
                with open(local_path, "rb") as f:
                    w.files.upload(remote_path, f, overwrite=True)
                log.info("Uploaded (new): %s (%d bytes)", remote_path, local_size)
            except Exception as e:
                log.warning("Failed to upload '%s': %s", remote_path, e)

    # Delete remote files not in local
    for name, info in remote_files.items():
        if name in local_files:
            continue
        try:
            w.files.delete(info["path"])
            log.info("Deleted (no longer in export): %s", info["path"])
        except Exception as e:
            log.warning("Failed to delete remote file '%s': %s", info["path"], e)

    # Recurse into local subdirectories
    for name, local_subdir in local_subdirs.items():
        sync_directory(w, local_subdir, f"{remote_dir}/{name}")

    # Delete remote subdirectories not in local
    for name, sub_remote_path in remote_subdirs.items():
        if name in local_subdirs:
            continue
        _delete_remote_recursive(w, sub_remote_path)


def resolve_knowledge_assistant(w: WorkspaceClient, tool_entry: dict, input_dir: Path,
                                volume_path: str,
                                catalog_rules: list[tuple[str, str]],
                                yes_update: bool, skip_existing: bool) -> str | None:
    """Resolve a knowledge assistant by creating, reusing, or updating an existing one.

    Returns the knowledge_assistant_id, or None on failure / explicit skip.
    """
    export_dir = input_dir / tool_entry["export_dir"]
    def_path = export_dir / "definition.json"
    if not def_path.exists():
        log.error("KA definition not found: %s", def_path)
        return None

    definition = json.loads(def_path.read_text())
    tool_id = tool_entry["tool_id"]
    display_name = definition["display_name"]
    log.info("Resolving knowledge assistant '%s' (tool_id: %s)", display_name, tool_id)

    expected_top = {
        "display_name": display_name,
        "description": definition.get("description", ""),
        "instructions": definition.get("instructions", ""),
    }
    expected_sources = [
        build_expected_source(s, tool_id, volume_path, catalog_rules)
        for s in definition.get("knowledge_sources", [])
    ]

    existing = find_existing_knowledge_assistant(w, display_name)

    if existing is None:
        return _create_knowledge_assistant(w, expected_top, expected_sources, definition, tool_id,
                                           input_dir, export_dir, volume_path)

    # Existing KA found: compute diff
    ka_id = existing["id"]
    existing_top = {
        "display_name": existing.get("display_name", ""),
        "description": existing.get("description", ""),
        "instructions": existing.get("instructions", ""),
    }
    existing_sources_raw = list_knowledge_sources(w, ka_id)
    existing_sources = [normalize_existing_source(s) for s in existing_sources_raw]

    top_diffs: list[str] = []
    for k in ("display_name", "description", "instructions"):
        if expected_top[k] != existing_top[k]:
            top_diffs.append(short_diff(k, existing_top[k], expected_top[k]))

    src_diff = diff_knowledge_sources(expected_sources, existing_sources)

    has_diff = bool(top_diffs or src_diff["to_add"] or src_diff["to_remove"] or src_diff["to_update"])
    if not has_diff:
        log.info("Knowledge assistant '%s' already matches export (id: %s); reusing.", display_name, ka_id)
        return ka_id

    diff_lines: list[str] = []
    if top_diffs:
        diff_lines.append("Top-level fields:")
        for line in top_diffs:
            diff_lines.append(f"  {line}")
    if src_diff["to_add"] or src_diff["to_remove"] or src_diff["to_update"]:
        diff_lines.append("Knowledge sources:")
        for s in src_diff["to_add"]:
            diff_lines.append(f"  + Add: \"{s['display_name']}\" ({s['source_type']})")
        for s in src_diff["to_remove"]:
            diff_lines.append(f"  - Remove: \"{s['display_name']}\" ({s['source_type']})")
        for u in src_diff["to_update"]:
            diff_lines.append(f"  ~ Update: \"{u['expected']['display_name']}\"")

    decision = resolve_conflict("Knowledge assistant", display_name, diff_lines, yes_update, skip_existing)
    if decision == CONFLICT_SKIP:
        return ka_id

    # Apply updates
    if top_diffs:
        update_mask = ",".join(k for k in ("display_name", "description", "instructions")
                                if expected_top[k] != existing_top[k])
        try:
            w.api_client.do("PATCH", f"/api/2.1/knowledge-assistants/{ka_id}",
                           query={"update_mask": update_mask}, body=expected_top)
            log.info("Updated KA '%s' top-level fields", display_name)
        except Exception as e:
            log.error("Failed to update KA '%s' top-level fields: %s", display_name, e)

    # Reconcile sources: deletes first, then adds, then updates
    name_to_existing_id = {s.get("display_name", ""): s.get("id") for s in existing_sources_raw}
    for s in src_diff["to_remove"]:
        sid = name_to_existing_id.get(s["display_name"])
        if not sid:
            continue
        try:
            w.api_client.do(
                "DELETE", f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources/{sid}"
            )
            log.info("Deleted knowledge source '%s'", s["display_name"])
        except Exception as e:
            log.error("Failed to delete knowledge source '%s': %s", s["display_name"], e)

    # Compute uploads needed for added/updated 'files' sources, keyed by source name
    files_needed_by_name: dict[str, dict] = {}
    for s in definition.get("knowledge_sources", []):
        name = s.get("display_name", "")
        if s.get("source_type") != "files":
            continue
        added = any(a["display_name"] == name for a in src_diff["to_add"])
        updated = any(u["expected"]["display_name"] == name for u in src_diff["to_update"])
        if added or updated:
            files_needed_by_name[name] = s

    for name, src in files_needed_by_name.items():
        local_dir_rel = src.get("local_dir", "")
        local_dir_abs = export_dir / local_dir_rel
        dir_basename = Path(local_dir_rel).name
        remote = f"{volume_path}/{tool_id}/{dir_basename}"
        log.info("Uploading files for source '%s': %s -> %s", name, local_dir_abs, remote)
        sync_directory(w, local_dir_abs, remote)

    for s in src_diff["to_add"]:
        try:
            w.api_client.do(
                "POST", f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources",
                body=s,
            )
            log.info("Added knowledge source '%s'", s["display_name"])
        except Exception as e:
            log.error("Failed to add knowledge source '%s': %s", s["display_name"], e)

    for u in src_diff["to_update"]:
        sid = name_to_existing_id.get(u["existing"]["display_name"])
        if not sid:
            continue
        # Build update_mask of changed fields
        diffs = []
        for k in ("display_name", "description", "source_type"):
            if u["existing"].get(k) != u["expected"].get(k):
                diffs.append(k)
        for spec_key in ("files", "index", "file_table"):
            if u["existing"].get(spec_key) != u["expected"].get(spec_key):
                diffs.append(spec_key)
        if not diffs:
            continue
        try:
            w.api_client.do(
                "PATCH", f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources/{sid}",
                query={"update_mask": ",".join(diffs)},
                body=u["expected"],
            )
            log.info("Updated knowledge source '%s'", u["expected"]["display_name"])
        except Exception as e:
            log.error("Failed to update knowledge source '%s': %s", u["expected"]["display_name"], e)

    return ka_id


def _create_knowledge_assistant(w: WorkspaceClient, expected_top: dict, expected_sources: list[dict],
                                definition: dict, tool_id: str, input_dir: Path,
                                export_dir: Path, volume_path: str) -> str | None:
    """Create a new KA (with file uploads + source creation). Returns new KA id."""
    # Phase 1: Upload files for each 'files' source before creating the KA
    source_upload_paths: dict[int, str] = {}
    for i, source in enumerate(definition.get("knowledge_sources", [])):
        if source.get("source_type") == "files":
            local_dir_rel = source.get("local_dir", "")
            local_dir_abs = export_dir / local_dir_rel
            dir_basename = Path(local_dir_rel).name
            remote_upload_path = f"{volume_path}/{tool_id}/{dir_basename}"
            log.info("Uploading files: %s -> %s", local_dir_abs, remote_upload_path)
            sync_directory(w, local_dir_abs, remote_upload_path)
            source_upload_paths[i] = remote_upload_path

    # Phase 2: Create the KA
    try:
        ka_resp = w.api_client.do("POST", "/api/2.1/knowledge-assistants", body=expected_top)
    except Exception as e:
        log.error("Failed to create knowledge assistant '%s': %s", expected_top["display_name"], e)
        return None

    ka_id = ka_resp["id"]
    log.info("Created knowledge assistant %s (id: %s)", expected_top["display_name"], ka_id)

    # Phase 3: Create knowledge sources (using already-built expected_sources)
    for i, source_body in enumerate(expected_sources):
        if source_body["source_type"] not in ("files", "index", "file_table"):
            log.warning("Skipping unknown source type '%s' in KA %s", source_body["source_type"], ka_id)
            continue
        try:
            w.api_client.do(
                "POST", f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources",
                body=source_body,
            )
            log.info("Created knowledge source '%s' (type: %s)",
                     source_body["display_name"], source_body["source_type"])
        except Exception as e:
            log.error("Failed to create knowledge source '%s': %s", source_body["display_name"], e)

    return ka_id


def resolve_genie_room(w: WorkspaceClient, tool_entry: dict, input_dir: Path,
                      warehouse_id: str,
                      catalog_rules: list[tuple[str, str]],
                      yes_update: bool, skip_existing: bool) -> str | None:
    """Resolve a genie room by creating, reusing, or updating an existing one.

    Returns the new/existing space_id, or None on failure / explicit skip.
    """
    export_dir = input_dir / tool_entry["export_dir"]
    def_path = export_dir / "definition.json"
    serialized_path = export_dir / "serialized.json"

    if not def_path.exists() or not serialized_path.exists():
        log.error("Genie room files not found in %s", export_dir)
        return None

    definition = json.loads(def_path.read_text())
    serialized_raw = serialized_path.read_text()
    title = definition.get("title", "")
    description = definition.get("description", "")
    log.info("Resolving genie room '%s'", title)

    # Apply catalog map to table identifiers in serialized JSON
    if catalog_rules and serialized_raw:
        try:
            serialized = json.loads(serialized_raw)
            tables = serialized.get("data_sources", {}).get("tables", [])
            for table in tables:
                old_id = table.get("identifier", "")
                new_id = apply_catalog_map(old_id, catalog_rules)
                if new_id != old_id:
                    log.info("  Table mapping: %s -> %s", old_id, new_id)
                    table["identifier"] = new_id
            serialized_raw = json.dumps(serialized)
        except json.JSONDecodeError as e:
            log.warning("Failed to parse serialized.json for catalog mapping: %s", e)

    existing = find_existing_genie_space(w, title)
    if existing is None:
        try:
            space = w.genie.create_space(
                warehouse_id=warehouse_id,
                serialized_space=serialized_raw,
                title=title,
                description=description,
            )
            log.info("Created genie room '%s' (id: %s)", title, space.space_id)
            return space.space_id
        except Exception as e:
            log.error("Failed to create genie room '%s': %s", title, e)
            return None

    # Existing room found: compare via Get (List doesn't include serialized_space)
    space_id = existing.space_id
    try:
        full = w.genie.get_space(space_id, include_serialized_space=True)
    except Exception as e:
        log.error("Failed to fetch genie room '%s' for comparison: %s", title, e)
        return space_id

    diff_lines: list[str] = []
    if (full.title or "") != title:
        diff_lines.append(short_diff("title", full.title or "", title))
    if (full.description or "") != description:
        diff_lines.append(short_diff("description", full.description or "", description))
    if (full.warehouse_id or "") != warehouse_id:
        diff_lines.append(short_diff("warehouse_id", full.warehouse_id or "", warehouse_id))
    # Compare serialized_space structurally (not byte-wise) to ignore whitespace/format differences
    serialized_changed = False
    try:
        existing_obj = json.loads(full.serialized_space) if full.serialized_space else None
        expected_obj = json.loads(serialized_raw) if serialized_raw else None
        serialized_changed = existing_obj != expected_obj
    except json.JSONDecodeError:
        serialized_changed = (full.serialized_space or "") != serialized_raw
    if serialized_changed:
        diff_lines.append(short_diff("serialized_space", full.serialized_space or "", serialized_raw))

    if not diff_lines:
        log.info("Genie room '%s' already matches export (id: %s); reusing.", title, space_id)
        return space_id

    decision = resolve_conflict("Genie room", title, ["Top-level fields:"] + [f"  {d}" for d in diff_lines],
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
        log.info("Updated genie room '%s' (id: %s)", title, space_id)
    except Exception as e:
        log.error("Failed to update genie room '%s': %s", title, e)

    return space_id


def build_expected_tool(tool_entry: dict, resolved_id: str | None,
                        catalog_rules: list[tuple[str, str]],
                        connection_map: dict[str, str],
                        app_map: dict[str, str]) -> dict:
    """Build the expected target-workspace tool body from a manifest tool entry.

    For `knowledge_assistant` and `genie_space`, `resolved_id` is the new resource id
    created/found in this run. For other types, the name comes from the manifest with
    the appropriate mapping applied.
    """
    tool_type = tool_entry["tool_type"]
    body = {
        "description": tool_entry.get("description", ""),
        "tool_type": tool_type,
    }
    if tool_type == "knowledge_assistant":
        body["knowledge_assistant"] = {"knowledge_assistant_id": resolved_id}
    elif tool_type == "genie_space":
        body["genie_space"] = {"id": resolved_id}
    elif tool_type == "uc_function":
        original = tool_entry.get("uc_function", {}).get("name", "")
        body["uc_function"] = {"name": apply_catalog_map(original, catalog_rules)}
    elif tool_type == "connection":
        original = tool_entry.get("connection", {}).get("name", "")
        body["connection"] = {"name": apply_name_map(original, connection_map)}
    elif tool_type == "app":
        original = tool_entry.get("app", {}).get("name", "")
        body["app"] = {"name": apply_name_map(original, app_map)}
    return body


def normalize_existing_tool(tool: dict) -> dict:
    """Project an existing-on-target tool dict to the same shape as build_expected_tool."""
    tool_type = tool.get("tool_type", "")
    body = {
        "description": tool.get("description", ""),
        "tool_type": tool_type,
    }
    if tool_type == "knowledge_assistant":
        body["knowledge_assistant"] = {
            "knowledge_assistant_id": tool.get("knowledge_assistant", {}).get("knowledge_assistant_id", "")
        }
    elif tool_type == "genie_space":
        body["genie_space"] = {"id": tool.get("genie_space", {}).get("id", "")}
    elif tool_type == "uc_function":
        body["uc_function"] = {"name": tool.get("uc_function", {}).get("name", "")}
    elif tool_type == "connection":
        body["connection"] = {"name": tool.get("connection", {}).get("name", "")}
    elif tool_type == "app":
        body["app"] = {"name": tool.get("app", {}).get("name", "")}
    return body


SUPPORTED_TOOL_TYPES = ("knowledge_assistant", "genie_space", "uc_function", "connection", "app")


def resolve_supervisor_agent(w: WorkspaceClient, agent_def: dict,
                             yes_update: bool, skip_existing: bool) -> str:
    """Resolve the supervisor agent (create, reuse, or update). Returns its id.

    Aborts the import if creation fails (no agent => nothing to attach tools to).
    """
    expected_top = {
        "display_name": agent_def["display_name"],
        "description": agent_def.get("description", ""),
        "instructions": agent_def.get("instructions", ""),
    }
    existing = find_existing_supervisor_agent(w, expected_top["display_name"])

    if existing is None:
        try:
            resp = w.api_client.do("POST", "/api/2.1/supervisor-agents", body=expected_top)
        except Exception as e:
            log.error("Failed to create supervisor agent: %s", e)
            sys.exit(1)
        agent_id = resp["supervisor_agent_id"]
        log.info("Created supervisor agent '%s' (id: %s)", expected_top["display_name"], agent_id)
        return agent_id

    agent_id = existing.get("supervisor_agent_id") or existing.get("id")
    existing_top = {
        "display_name": existing.get("display_name", ""),
        "description": existing.get("description", ""),
        "instructions": existing.get("instructions", ""),
    }
    diffs: list[str] = []
    for k in ("display_name", "description", "instructions"):
        if expected_top[k] != existing_top[k]:
            diffs.append(short_diff(k, existing_top[k], expected_top[k]))

    if not diffs:
        log.info("Supervisor agent '%s' already matches export (id: %s); reusing.",
                 expected_top["display_name"], agent_id)
        return agent_id

    decision = resolve_conflict(
        "Supervisor agent", expected_top["display_name"],
        ["Top-level fields:"] + [f"  {d}" for d in diffs],
        yes_update, skip_existing,
    )
    if decision == CONFLICT_SKIP:
        return agent_id

    update_mask = ",".join(k for k in ("display_name", "description", "instructions")
                            if expected_top[k] != existing_top[k])
    try:
        w.api_client.do(
            "PATCH", f"/api/2.1/supervisor-agents/{agent_id}",
            query={"update_mask": update_mask}, body=expected_top,
        )
        log.info("Updated supervisor agent '%s' top-level fields", expected_top["display_name"])
    except Exception as e:
        log.error("Failed to update supervisor agent '%s': %s", expected_top["display_name"], e)

    return agent_id


def reconcile_tools(w: WorkspaceClient, agent_id: str,
                    manifest_tools: list[dict], resolved_ids: dict[str, str | None],
                    catalog_rules: list[tuple[str, str]],
                    connection_map: dict[str, str],
                    app_map: dict[str, str],
                    yes_update: bool, skip_existing: bool) -> tuple[int, int, int]:
    """Reconcile tools on the supervisor agent against the manifest.

    `resolved_ids` maps tool_id -> resolved KA/genie id (or None if resolution failed).

    Returns (added_or_updated, deleted, failed) counts.
    """
    existing_tools_raw = list_agent_tools(w, agent_id)
    existing_by_id = {t.get("tool_id", ""): t for t in existing_tools_raw}

    # Build expected tool bodies, keyed by tool_id, only for supported types with resolved ids
    expected_by_id: dict[str, dict] = {}
    for entry in manifest_tools:
        if entry.get("skipped"):
            continue
        if entry.get("tool_type") not in SUPPORTED_TOOL_TYPES:
            continue
        rid = resolved_ids.get(entry["tool_id"])
        if rid is None:
            continue
        expected_by_id[entry["tool_id"]] = build_expected_tool(entry, rid, catalog_rules, connection_map, app_map)

    added_or_updated = 0
    deleted = 0
    failed = 0

    # Adds and updates
    for tid, expected in expected_by_id.items():
        if tid not in existing_by_id:
            try:
                w.api_client.do(
                    "POST", f"/api/2.1/supervisor-agents/{agent_id}/tools",
                    query={"tool_id": tid}, body=expected,
                )
                log.info("Created tool '%s' (type: %s)", tid, expected["tool_type"])
                added_or_updated += 1
            except Exception as e:
                log.error("Failed to create tool '%s': %s", tid, e)
                failed += 1
        else:
            existing_norm = normalize_existing_tool(existing_by_id[tid])
            if existing_norm == expected:
                continue

            # The Tool API only supports updating `description` via PATCH. If anything
            # else differs (tool_type or the target resource ID), we must delete + recreate.
            description_changed = existing_norm.get("description") != expected.get("description")
            other_changed = (
                existing_norm.get("tool_type") != expected.get("tool_type")
                or existing_norm.get("knowledge_assistant") != expected.get("knowledge_assistant")
                or existing_norm.get("genie_space") != expected.get("genie_space")
                or existing_norm.get("uc_function") != expected.get("uc_function")
                or existing_norm.get("connection") != expected.get("connection")
                or existing_norm.get("app") != expected.get("app")
            )

            if other_changed:
                try:
                    w.api_client.do(
                        "DELETE", f"/api/2.1/supervisor-agents/{agent_id}/tools/{tid}",
                    )
                    w.api_client.do(
                        "POST", f"/api/2.1/supervisor-agents/{agent_id}/tools",
                        query={"tool_id": tid}, body=expected,
                    )
                    log.info("Recreated tool '%s' (type: %s)", tid, expected["tool_type"])
                    added_or_updated += 1
                except Exception as e:
                    log.error("Failed to recreate tool '%s': %s", tid, e)
                    failed += 1
            elif description_changed:
                try:
                    w.api_client.do(
                        "PATCH", f"/api/2.1/supervisor-agents/{agent_id}/tools/{tid}",
                        query={"update_mask": "description"}, body=expected,
                    )
                    log.info("Updated tool '%s' description", tid)
                    added_or_updated += 1
                except Exception as e:
                    log.error("Failed to update tool '%s': %s", tid, e)
                    failed += 1

    # Deletions: existing tools of supported types that aren't in the manifest
    for tid, et in existing_by_id.items():
        if et.get("tool_type") not in SUPPORTED_TOOL_TYPES:
            continue  # leave alone — out of our authority
        if tid in expected_by_id:
            continue
        # Check if this tool_id appears in manifest as skipped — if so, leave alone
        skipped_in_manifest = any(
            mt.get("tool_id") == tid and mt.get("skipped") for mt in manifest_tools
        )
        if skipped_in_manifest:
            continue
        try:
            w.api_client.do(
                "DELETE", f"/api/2.1/supervisor-agents/{agent_id}/tools/{tid}",
            )
            log.info("Deleted tool '%s'", tid)
            deleted += 1
        except Exception as e:
            log.error("Failed to delete tool '%s': %s", tid, e)
            failed += 1

    return (added_or_updated, deleted, failed)


def import_agent(w: WorkspaceClient, manifest: dict, input_dir: Path,
                 warehouse_id: str, volume_path: str,
                 catalog_rules: list[tuple[str, str]],
                 connection_map: dict[str, str] | None = None,
                 app_map: dict[str, str] | None = None,
                 yes_update: bool = False, skip_existing: bool = False,
                 force: bool = False):
    """Import a supervisor agent and all its tools (with reconciliation)."""
    agent_def = manifest["supervisor_agent"]
    connection_map = connection_map or {}
    app_map = app_map or {}
    log.info("Importing agent '%s'", agent_def["display_name"])

    # Phase 0: Pre-flight validation
    preflight_check(w, manifest, input_dir, volume_path, catalog_rules,
                    connection_map, app_map, force)

    # Phase 1 + 2: Resolve KAs and genie rooms (each may create/update existing)
    resolved_ids: dict[str, str | None] = {}  # tool_id -> KA id or genie space id
    for tool_entry in manifest.get("tools", []):
        if tool_entry.get("skipped"):
            log.info("Skipping tool '%s' (%s)",
                     tool_entry["tool_id"], tool_entry.get("skip_reason", ""))
            resolved_ids[tool_entry["tool_id"]] = None
            continue

        ttype = tool_entry["tool_type"]
        if ttype == "knowledge_assistant":
            resolved_ids[tool_entry["tool_id"]] = resolve_knowledge_assistant(
                w, tool_entry, input_dir, volume_path, catalog_rules,
                yes_update, skip_existing,
            )
        elif ttype == "genie_space":
            resolved_ids[tool_entry["tool_id"]] = resolve_genie_room(
                w, tool_entry, input_dir, warehouse_id, catalog_rules,
                yes_update, skip_existing,
            )
        elif ttype in ("uc_function", "connection", "app"):
            # No separate resource to resolve; the tool body is built directly from the manifest.
            # We only need a truthy placeholder so reconcile_tools includes this entry.
            resolved_ids[tool_entry["tool_id"]] = "<no-resource>"
        else:
            log.info("Skipping unsupported tool type '%s'", ttype)
            resolved_ids[tool_entry["tool_id"]] = None

    # Phase 3: Resolve supervisor agent
    agent_id = resolve_supervisor_agent(w, agent_def, yes_update, skip_existing)

    # Phase 4: Reconcile tools
    added_or_updated, deleted, failed = reconcile_tools(
        w, agent_id, manifest.get("tools", []), resolved_ids,
        catalog_rules, connection_map, app_map,
        yes_update, skip_existing,
    )

    # Summary
    log.info("--- Import Summary ---")
    log.info("Agent: %s (id: %s)", agent_def["display_name"], agent_id)
    log.info("Tools added/updated: %d, deleted: %d, failed: %d",
             added_or_updated, deleted, failed)


def main():
    parser = argparse.ArgumentParser(
        description="Import a Databricks Supervisor Agent from an exported directory."
    )
    parser.add_argument(
        "--input-dir", required=True,
        help="Path to the exported agent directory (containing manifest.json)",
    )
    parser.add_argument(
        "--warehouse-id", required=True,
        help="SQL warehouse ID for genie rooms in the target workspace",
    )
    parser.add_argument(
        "--volume-path", required=True,
        help="UC volume base path for uploading KA files (e.g. /Volumes/catalog/schema/volume)",
    )
    parser.add_argument(
        "--catalog-map",
        help="Comma-separated catalog mapping rules: old=new (e.g. dsl_dlt=new_cat,old.schema=new.schema)",
    )
    parser.add_argument(
        "--connection-map",
        help="Comma-separated connection-name renames: old_name=new_name (for connection-type tools)",
    )
    parser.add_argument(
        "--app-map",
        help="Comma-separated app-name renames: old_name=new_name (for app-type tools)",
    )
    parser.add_argument(
        "--yes-update", action="store_true",
        help="Always update existing objects without prompting (mutually exclusive with --skip-existing)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Never update existing objects, always reuse them (mutually exclusive with --yes-update)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Skip pre-flight dependency checks; proceed even if referenced tables/indexes/volumes are missing",
    )
    args = parser.parse_args()

    if args.yes_update and args.skip_existing:
        log.error("--yes-update and --skip-existing are mutually exclusive")
        sys.exit(2)

    input_dir = Path(args.input_dir)
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        log.error("manifest.json not found in %s", input_dir)
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

        manifest = json.loads(manifest_path.read_text())
        catalog_rules = parse_catalog_map(args.catalog_map)
        connection_map = parse_name_map(args.connection_map)
        app_map = parse_name_map(args.app_map)

        import_agent(
            w, manifest, input_dir,
            args.warehouse_id, args.volume_path, catalog_rules,
            connection_map=connection_map,
            app_map=app_map,
            yes_update=args.yes_update,
            skip_existing=args.skip_existing,
            force=args.force,
        )
        log.info("Import complete.")
    except SystemExit:
        raise
    except Exception as e:
        log.error("Import failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
