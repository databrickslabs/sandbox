#!/usr/bin/env python3
"""Export a Databricks Supervisor Agent and its tools to a portable directory structure."""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def sanitize_name(name: str) -> str:
    """Sanitize a display name for use as a directory name.

    Replaces any character that isn't alphanumeric, hyphen, or underscore with '_',
    collapses consecutive underscores, strips leading/trailing underscores, lowercases.
    """
    s = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_").lower()
    return s or "unnamed"


def paginated_get(w: WorkspaceClient, path: str, items_key: str, params: dict | None = None) -> list[dict]:
    """Fetch all pages from a paginated GET endpoint."""
    results = []
    page_token = None
    while True:
        query = dict(params or {})
        if page_token:
            query["page_token"] = page_token
        resp = w.api_client.do("GET", path, query=query)
        results.extend(resp.get(items_key, []))
        page_token = resp.get("next_page_token")
        if not page_token:
            break
    return results


def find_supervisor_agent(w: WorkspaceClient, display_name: str) -> dict:
    """Find a supervisor agent by display_name. Exits if not found."""
    agents = paginated_get(w, "/api/2.1/supervisor-agents", "supervisor_agents")
    for agent in agents:
        if agent.get("display_name") == display_name:
            return agent
    available = [a.get("display_name", "?") for a in agents]
    log.error("Agent '%s' not found. Available agents: %s", display_name, available)
    sys.exit(1)


def get_supervisor_agent(w: WorkspaceClient, agent_id: str) -> dict:
    """Get the full supervisor agent definition."""
    return w.api_client.do("GET", f"/api/2.1/supervisor-agents/{agent_id}")


def list_agent_tools(w: WorkspaceClient, agent_id: str) -> list[dict]:
    """List all tools for a supervisor agent."""
    return paginated_get(
        w, f"/api/2.1/supervisor-agents/{agent_id}/tools", "tools"
    )


def export_tool(w: WorkspaceClient, tool: dict, agent_dir: Path) -> dict:
    """Export a single tool. Returns its manifest entry."""
    tool_type = tool.get("tool_type", "unknown")
    tool_id = tool.get("tool_id", "unknown")
    description = tool.get("description", "")

    entry = {
        "tool_id": tool_id,
        "tool_type": tool_type,
        "description": description,
    }

    if tool_type == "knowledge_assistant":
        ka_config = tool.get("knowledge_assistant", {})
        entry["knowledge_assistant"] = ka_config
        export_dir = export_knowledge_assistant(w, ka_config, agent_dir)
        entry["export_dir"] = export_dir
    elif tool_type == "genie_space":
        gs_config = tool.get("genie_space", {})
        entry["genie_space"] = gs_config
        export_dir = export_genie_room(w, gs_config, agent_dir)
        entry["export_dir"] = export_dir
    elif tool_type == "uc_function":
        entry["uc_function"] = tool.get("uc_function", {})
    elif tool_type == "connection":
        entry["connection"] = tool.get("connection", {})
    elif tool_type == "app":
        entry["app"] = tool.get("app", {})
    else:
        log.info("Skipping tool '%s' (type: %s)", tool_id, tool_type)
        entry["skipped"] = True
        entry["skip_reason"] = "tool type not supported for export"

    return entry


def download_volume_path(w: WorkspaceClient, volume_path: str, local_dir: Path):
    """Recursively download all files from a UC volume path into local_dir."""
    local_dir.mkdir(parents=True, exist_ok=True)
    try:
        entries = list(w.files.list_directory_contents(volume_path))
    except Exception as e:
        log.warning("Failed to list volume path '%s': %s", volume_path, e)
        return

    if not entries:
        log.info("Volume path '%s' is empty", volume_path)
        return

    for entry in entries:
        entry_path = entry.path
        entry_name = entry_path.rstrip("/").rsplit("/", 1)[-1]
        local_path = local_dir / entry_name

        if entry.is_directory:
            download_volume_path(w, entry_path, local_path)
        else:
            try:
                resp = w.files.download(entry_path)
                local_path.write_bytes(resp.contents.read())
                log.info("Downloaded %s", entry_path)
            except Exception as e:
                log.warning("Failed to download '%s': %s", entry_path, e)


def export_knowledge_assistant(w: WorkspaceClient, ka_config: dict, agent_dir: Path) -> str:
    """Export a knowledge assistant and its sources. Returns relative export dir."""
    ka_id = ka_config["knowledge_assistant_id"]
    log.info("Exporting knowledge assistant %s", ka_id)

    # Get KA definition
    ka = w.api_client.do("GET", f"/api/2.1/knowledge-assistants/{ka_id}")

    # Get knowledge sources
    sources = paginated_get(
        w, f"/api/2.1/knowledge-assistants/{ka_id}/knowledge-sources", "knowledge_sources"
    )

    # Build definition
    ka_name = sanitize_name(ka.get("display_name", ka_id))
    ka_dir = agent_dir / "knowledge_assistants" / ka_name
    ka_dir.mkdir(parents=True, exist_ok=True)

    definition = {
        "display_name": ka.get("display_name", ""),
        "description": ka.get("description", ""),
        "instructions": ka.get("instructions", ""),
        "knowledge_sources": [],
    }

    for source in sources:
        source_entry = {
            "display_name": source.get("display_name", ""),
            "description": source.get("description", ""),
        }

        source_type = source.get("source_type", "unknown")
        source_entry["source_type"] = source_type

        if source_type == "files":
            source_entry["files"] = source.get("files", {})
            volume_path = source_entry["files"].get("path", "")
            # Derive a local subdir name from the volume path's last segment
            dir_name = volume_path.rstrip("/").rsplit("/", 1)[-1] if volume_path else "files"
            local_subdir = f"files/{sanitize_name(dir_name)}"
            source_entry["local_dir"] = local_subdir
            download_volume_path(w, volume_path, ka_dir / local_subdir)
        elif source_type == "index":
            source_entry["index"] = source.get("index", {})
        elif source_type == "file_table":
            source_entry["file_table"] = source.get("file_table", {})
        else:
            log.warning("Unknown source type in KA %s: %s", ka_id, source)

        definition["knowledge_sources"].append(source_entry)

    # Write definition
    def_path = ka_dir / "definition.json"
    def_path.write_text(json.dumps(definition, indent=2))
    log.info("KA definition written to %s", def_path)

    return str(Path("knowledge_assistants") / ka_name)


def export_genie_room(w: WorkspaceClient, gs_config: dict, agent_dir: Path) -> str:
    """Export a genie room. Returns relative export dir."""
    space_id = gs_config["id"]
    log.info("Exporting genie room %s", space_id)

    space = w.genie.get_space(space_id, include_serialized_space=True)

    room_name = sanitize_name(space.title or space_id)
    room_dir = agent_dir / "genie_rooms" / room_name
    room_dir.mkdir(parents=True, exist_ok=True)

    # Write definition (metadata)
    definition = {
        "title": space.title or "",
        "description": space.description or "",
        "warehouse_id": space.warehouse_id or "",
    }
    def_path = room_dir / "definition.json"
    def_path.write_text(json.dumps(definition, indent=2))

    # Write serialized payload
    serialized_path = room_dir / "serialized.json"
    serialized_path.write_text(space.serialized_space or "")
    log.info("Genie room written to %s", room_dir)

    return str(Path("genie_rooms") / room_name)


def export_agent(w: WorkspaceClient, agent_name: str, output_dir: Path):
    """Export a supervisor agent and all its tools."""
    log.info("Exporting agent '%s' to %s", agent_name, output_dir)

    # Find and retrieve the agent
    agent_summary = find_supervisor_agent(w, agent_name)
    agent_id = agent_summary["supervisor_agent_id"]
    log.info("Found agent '%s' (id: %s)", agent_name, agent_id)

    agent = get_supervisor_agent(w, agent_id)

    # Create output directory
    agent_dir = output_dir / sanitize_name(agent_name)
    agent_dir.mkdir(parents=True, exist_ok=True)

    # List tools
    tools = list_agent_tools(w, agent_id)
    log.info("Agent has %d tools", len(tools))

    # Build manifest
    manifest = {
        "supervisor_agent": {
            "display_name": agent.get("display_name", ""),
            "description": agent.get("description", ""),
            "instructions": agent.get("instructions", ""),
        },
        "tools": [],
    }

    for tool in tools:
        tool_entry = export_tool(w, tool, agent_dir)
        manifest["tools"].append(tool_entry)

    # Write manifest
    manifest_path = agent_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("Manifest written to %s", manifest_path)


def main():
    parser = argparse.ArgumentParser(
        description="Export a Databricks Supervisor Agent and its tools."
    )
    parser.add_argument(
        "--name", required=True, help="Display name of the supervisor agent to export"
    )
    parser.add_argument(
        "--output-dir",
        default="./export",
        help="Root directory for the export output (default: ./export)",
    )
    args = parser.parse_args()

    try:
        w = WorkspaceClient()
        log.info("Connected to %s", w.config.host)
        export_agent(w, args.name, Path(args.output_dir))
        log.info("Export complete.")
    except SystemExit:
        raise
    except Exception as e:
        log.error("Export failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
