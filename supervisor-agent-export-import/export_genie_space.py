#!/usr/bin/env python3
"""Export a single Databricks Genie Space into a directory.

Writes two files into the output directory, in the layout expected by
import_genie_space.py:
  - definition.json   (title, description, warehouse_id)
  - serialized.json    (the full serialized_space payload)

The space can be identified by ID (--space-id) or by exact title (--name).
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def find_space_id_by_title(w: WorkspaceClient, title: str) -> str | None:
    """Return the space_id of the Genie space whose title matches, else None."""
    page_token = None
    while True:
        resp = w.genie.list_spaces(page_token=page_token)
        for space in (resp.spaces or []):
            if space.title == title:
                return space.space_id
        page_token = resp.next_page_token
        if not page_token:
            break
    return None


def export_genie_space(w: WorkspaceClient, space_id: str, output_dir: Path) -> None:
    """Export the given Genie space into output_dir as definition.json + serialized.json."""
    log.info("Exporting genie space %s", space_id)
    space = w.genie.get_space(space_id, include_serialized_space=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    definition = {
        "title": space.title or "",
        "description": space.description or "",
        "warehouse_id": space.warehouse_id or "",
    }
    (output_dir / "definition.json").write_text(json.dumps(definition, indent=2))

    serialized = space.serialized_space or ""
    if not serialized:
        log.warning("Space %s returned an empty serialized_space payload.", space_id)
    (output_dir / "serialized.json").write_text(serialized)

    log.info("Genie space '%s' written to %s", space.title or space_id, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Export a single Databricks Genie Space into a directory."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--space-id",
        help="ID of the Genie Space to export",
    )
    group.add_argument(
        "--name",
        help="Exact title of the Genie Space to export (looked up in the workspace)",
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Directory to write definition.json and serialized.json into",
    )
    args = parser.parse_args()

    try:
        w = WorkspaceClient()
        log.info("Connected to %s", w.config.host)

        space_id = args.space_id
        if space_id is None:
            space_id = find_space_id_by_title(w, args.name)
            if space_id is None:
                log.error("No Genie Space found with title '%s'", args.name)
                sys.exit(1)

        export_genie_space(w, space_id, Path(args.output_dir))
        log.info("Export complete.")
    except SystemExit:
        raise
    except Exception as e:
        log.error("Export failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
