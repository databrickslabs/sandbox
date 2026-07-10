"""
Context-aware chat service.

Extracts entity references from user messages (e.g. catalog.schema.table),
resolves them against the asset database, and formats a workspace context
block to inject into the LLM system prompt.
"""

import re
import json
import logging
from typing import List, Dict, Optional

from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)

# Max chars for the injected context block to avoid blowing up the context window
CONTEXT_CHAR_LIMIT = 4000

# --- Entity extraction patterns ---

# Three-level: catalog.schema.table (with optional backtick quoting)
_THREE_LEVEL = re.compile(
    r"`?(\w+)\.(\w+)\.(\w+)`?",
)

# Two-level: schema.table — only if the parts look like identifiers (lowercase/snake)
_TWO_LEVEL = re.compile(
    r"(?<!\w)`?([a-z_]\w*)\.([a-z_]\w*)`?(?!\.\w)",
)

# Natural language references: "table X", "notebook Y", "job Z"
_NL_KEYWORD = re.compile(
    r"\b(table|view|notebook|job|dashboard|pipeline|function|model|volume)\s+[`\"]?(\S+?)[`\"]?(?:\s|$|[.,;!?])",
    re.IGNORECASE,
)

# Workspace path references: /Users/..., /Repos/..., /Workspace/...
_WORKSPACE_PATH = re.compile(
    r"(/(?:Users|Repos|Workspace|Shared)/\S+)",
)


def extract_entities(text: str) -> List[Dict]:
    """
    Extract entity references from user text.

    Returns a list of dicts with keys:
      - match_type: 'three_level' | 'two_level' | 'keyword' | 'path'
      - raw: the matched string
      - catalog, schema_name, name (for catalog assets)
      - asset_type (for keyword matches)
      - path (for workspace path matches)
    """
    entities: List[Dict] = []
    seen = set()

    # Three-level names (highest confidence)
    for m in _THREE_LEVEL.finditer(text):
        full = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        if full not in seen:
            seen.add(full)
            entities.append({
                "match_type": "three_level",
                "raw": full,
                "catalog": m.group(1),
                "schema_name": m.group(2),
                "name": m.group(3),
            })

    # Two-level names (only if not already matched as three-level substring)
    for m in _TWO_LEVEL.finditer(text):
        full = f"{m.group(1)}.{m.group(2)}"
        if full not in seen and not any(full in e["raw"] for e in entities):
            seen.add(full)
            entities.append({
                "match_type": "two_level",
                "raw": full,
                "schema_name": m.group(1),
                "name": m.group(2),
            })

    # Natural language keyword references
    for m in _NL_KEYWORD.finditer(text):
        asset_type = m.group(1).lower()
        name = m.group(2).strip("`\"'")
        key = f"{asset_type}:{name}"
        if key not in seen and name not in seen:
            seen.add(key)
            entities.append({
                "match_type": "keyword",
                "raw": name,
                "asset_type": asset_type,
                "name": name,
            })

    # Workspace paths
    for m in _WORKSPACE_PATH.finditer(text):
        path = m.group(1)
        if path not in seen:
            seen.add(path)
            entities.append({
                "match_type": "path",
                "raw": path,
                "path": path,
            })

    return entities


def resolve_entities(entities: List[Dict]) -> List[Dict]:
    """
    Resolve extracted entities against the CatalogAsset and WorkspaceAsset tables.

    Returns a list of resolved asset metadata dicts, or empty list if nothing found.
    """
    resolved: List[Dict] = []

    for entity in entities:
        match_type = entity.get("match_type")

        if match_type == "three_level":
            full_name = entity["raw"]
            asset = DatabaseAdapter.get_catalog_asset_by_full_name(full_name)
            if asset:
                resolved.append(asset)
                continue

        if match_type == "two_level":
            # Search by schema + name across all catalogs
            schema_name = entity.get("schema_name", "")
            name = entity.get("name", "")
            assets, _ = DatabaseAdapter.list_catalog_assets(
                schema_name=schema_name, search=name, page_size=3
            )
            for a in assets:
                if a not in resolved:
                    resolved.append(a)

        if match_type == "keyword":
            name = entity.get("name", "")
            asset_type = entity.get("asset_type", "")

            # Check catalog assets first
            catalog_types = {"table", "view", "function", "model", "volume"}
            workspace_types = {"notebook", "job", "dashboard", "pipeline"}

            if asset_type in catalog_types:
                assets, _ = DatabaseAdapter.list_catalog_assets(
                    asset_type=asset_type, search=name, page_size=3
                )
                for a in assets:
                    if a not in resolved:
                        resolved.append(a)

            if asset_type in workspace_types:
                assets, _ = DatabaseAdapter.list_workspace_assets(
                    asset_type=asset_type, search=name, page_size=3
                )
                for a in assets:
                    if a not in resolved:
                        resolved.append(a)

            # If type is ambiguous, search both
            if asset_type not in catalog_types and asset_type not in workspace_types:
                cat_assets, _ = DatabaseAdapter.list_catalog_assets(search=name, page_size=2)
                ws_assets, _ = DatabaseAdapter.list_workspace_assets(search=name, page_size=2)
                for a in cat_assets + ws_assets:
                    if a not in resolved:
                        resolved.append(a)

        if match_type == "path":
            path = entity.get("path", "")
            assets, _ = DatabaseAdapter.list_workspace_assets(search=path, page_size=3)
            for a in assets:
                if a not in resolved:
                    resolved.append(a)

    return resolved


def _format_catalog_asset(asset: Dict) -> str:
    """Format a single catalog asset for the context block."""
    parts = [f"**{asset.get('asset_type', 'asset').title()}** `{asset.get('full_name', asset.get('name', '?'))}`"]

    if asset.get("owner"):
        parts.append(f"Owner: {asset['owner']}")

    if asset.get("comment"):
        comment = asset["comment"][:120]
        parts.append(f"Description: {comment}")

    if asset.get("columns_json"):
        try:
            columns = json.loads(asset["columns_json"])
            col_names = [c.get("name", "") for c in columns[:8]]
            col_str = ", ".join(col_names)
            if len(columns) > 8:
                col_str += f", ... ({len(columns)} total)"
            parts.append(f"Columns: {col_str}")
        except (json.JSONDecodeError, TypeError):
            pass

    if asset.get("row_count"):
        parts.append(f"Rows: {asset['row_count']:,}")

    if asset.get("table_type"):
        parts.append(f"Type: {asset['table_type']}")

    return " — ".join(parts)


def _format_workspace_asset(asset: Dict) -> str:
    """Format a single workspace asset for the context block."""
    parts = [f"**{asset.get('asset_type', 'asset').title()}** `{asset.get('path', asset.get('name', '?'))}`"]

    if asset.get("owner"):
        parts.append(f"Owner: {asset['owner']}")

    if asset.get("description"):
        desc = asset["description"][:120]
        parts.append(f"Description: {desc}")

    if asset.get("language"):
        parts.append(f"Language: {asset['language']}")

    return " — ".join(parts)


def format_context_block(resolved: List[Dict]) -> str:
    """
    Format resolved assets into a Markdown context block.

    Caps output at ~CONTEXT_CHAR_LIMIT chars.
    """
    if not resolved:
        return ""

    lines = ["## Workspace Context", "The user is discussing these assets:"]
    total_len = sum(len(l) for l in lines)

    for asset in resolved:
        if "full_name" in asset:
            line = "- " + _format_catalog_asset(asset)
        elif "path" in asset:
            line = "- " + _format_workspace_asset(asset)
        else:
            continue

        if total_len + len(line) > CONTEXT_CHAR_LIMIT:
            lines.append(f"- _(+{len(resolved) - len(lines) + 2} more assets)_")
            break

        lines.append(line)
        total_len += len(line)

    return "\n".join(lines)


def enrich_system_prompt(base_prompt: str, user_message: str) -> str:
    """
    Orchestrator: extract entities from user message, resolve against DB,
    format context block, and append to the base system prompt.
    """
    try:
        entities = extract_entities(user_message)
        if not entities:
            return base_prompt

        resolved = resolve_entities(entities)
        if not resolved:
            return base_prompt

        context_block = format_context_block(resolved)
        if not context_block:
            return base_prompt

        return f"{base_prompt}\n\n{context_block}"
    except Exception as e:
        logger.warning("Context enrichment failed (using base prompt): %s", e)
        return base_prompt
