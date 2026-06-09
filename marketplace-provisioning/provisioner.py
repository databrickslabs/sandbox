"""
Genie space + data provisioning module.

Provisions a complete scenario into a Databricks workspace:
  1. Create Unity Catalog catalog + schema
  2. Upload CSV data files to a UC volume
  3. Create tables from the CSVs
  4. Grant access to all workspace users
  5. Create a Genie space with full configuration
  6. Grant Genie space access to all workspace users

Ported from workspace-setup/deploy_lobs.py with adaptations for
running inside a Databricks App (service principal auth via SDK).
"""

import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger("provisioner")

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PATH_IDENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _check_ident(name: str, kind: str) -> str:
    """Reject identifiers that aren't safe to interpolate into SQL.

    Inputs come from trusted JSON config under scenarios/, but we validate
    anyway so a bad config file cannot become a SQL injection vector.
    """
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise ValueError(f"Invalid {kind} identifier: {name!r}")
    return name


def _check_path_ident(name: str, kind: str) -> str:
    """Reject path components that aren't safe to use as filesystem/lock keys.

    Allows hyphens (unlike SQL identifiers) but still rejects path traversal,
    spaces, and other unsafe characters.
    """
    if not isinstance(name, str) or not _PATH_IDENT_RE.match(name):
        raise ValueError(f"Invalid {kind}: {name!r}")
    return name

# Per-scenario locks to prevent duplicate concurrent provisioning
_provisioning_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(scenario_key: str) -> threading.Lock:
    with _locks_lock:
        if scenario_key not in _provisioning_locks:
            _provisioning_locks[scenario_key] = threading.Lock()
        return _provisioning_locks[scenario_key]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_auth() -> tuple[str, dict[str, str]]:
    """Get host and auth headers using the Databricks SDK default auth chain.

    Inside a Databricks App this resolves to the app's service principal
    credentials (OAuth). No PAT env var fallback — the app must never
    prompt for, read, or store a user PAT.
    """
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    host = (w.config.host or "").rstrip("/")
    auth_header = w.config.authenticate().get("Authorization", "")
    if not host or not auth_header:
        raise RuntimeError("No Databricks credentials available from SDK")

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }
    return host, headers


# ---------------------------------------------------------------------------
# HTTP helper with retry
# ---------------------------------------------------------------------------

DEFAULT_REQUEST_TIMEOUT = 60  # seconds


def api_request(method: str, url: str, headers: dict, max_retries: int = 5, **kwargs) -> requests.Response:
    """Make an API request with exponential backoff retry on 429/5xx.

    A default timeout is applied so a stalled network can't hang provisioning
    threads indefinitely. Callers can override via kwargs.
    """
    kwargs.setdefault("timeout", DEFAULT_REQUEST_TIMEOUT)
    for attempt in range(max_retries):
        resp = requests.request(method, url, headers=headers, **kwargs)
        if resp.status_code in (200, 201, 204):
            return resp
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = min(1.0 * (2 ** attempt), 16.0)
            log.warning(f"Retry {attempt+1} after {resp.status_code}, waiting {delay}s...")
            time.sleep(delay)
            continue
        log.error(f"API error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
    raise RuntimeError(f"Max retries exceeded for {url}")


# ---------------------------------------------------------------------------
# Warehouse discovery
# ---------------------------------------------------------------------------

def get_warehouse_id(host: str, headers: dict) -> tuple[str, str]:
    """Find the first available SQL warehouse. Prefer running ones."""
    resp = api_request("GET", f"{host}/api/2.0/sql/warehouses", headers=headers)
    warehouses = resp.json().get("warehouses", [])
    if not warehouses:
        raise RuntimeError("No SQL warehouses found in this workspace")
    running = [w for w in warehouses if w.get("state") == "RUNNING"]
    choice = running[0] if running else warehouses[0]
    return choice["id"], choice["name"]


# ---------------------------------------------------------------------------
# SQL execution
# ---------------------------------------------------------------------------

def execute_sql(host: str, headers: dict, warehouse_id: str, sql: str,
                 parameters: Optional[list] = None, timeout: int = 300) -> dict:
    """Execute SQL via the Statement API with polling."""
    payload = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": "50s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }
    if parameters:
        payload["parameters"] = parameters
    resp = api_request("POST", f"{host}/api/2.0/sql/statements", headers=headers, json=payload)
    result = resp.json()
    status = result.get("status", {}).get("state", "")

    if status == "SUCCEEDED":
        return result
    if status == "FAILED":
        error = result.get("status", {}).get("error", {}).get("message", "Unknown error")
        raise RuntimeError(f"SQL failed: {error}\nQuery: {sql[:200]}")

    # Poll for completion
    stmt_id = result["statement_id"]
    elapsed = 0
    while elapsed < timeout:
        time.sleep(3)
        elapsed += 3
        poll = api_request("GET", f"{host}/api/2.0/sql/statements/{stmt_id}", headers=headers)
        poll_result = poll.json()
        state = poll_result.get("status", {}).get("state", "")
        if state == "SUCCEEDED":
            return poll_result
        if state == "FAILED":
            error = poll_result.get("status", {}).get("error", {}).get("message", "Unknown")
            raise RuntimeError(f"SQL failed: {error}")
    raise RuntimeError(f"SQL timed out after {timeout}s")


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

def upload_file_to_volume(host: str, headers: dict, local_path: str, volume_path: str):
    """Upload a file to a UC volume via the Files API."""
    url = f"{host}/api/2.0/fs/files{volume_path}"
    with open(local_path, "rb") as f:
        content = f.read()
    resp = requests.put(
        url,
        headers={"Authorization": headers["Authorization"]},
        data=content,
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    if resp.status_code not in (200, 201, 204):
        resp = requests.put(
            url,
            headers={"Authorization": headers["Authorization"], "Overwrite": "true"},
            data=content,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Upload failed ({resp.status_code}): {resp.text[:300]}")


# ---------------------------------------------------------------------------
# Genie space serialization
# ---------------------------------------------------------------------------

def build_serialized_space(config: dict) -> dict:
    """Convert flat genie_space.json config into serialized_space format for the API.

    Joins are handled via PK/FK constraints on the tables themselves, which Genie
    auto-detects. Column descriptions and exclude flags go inside column_configs
    as arrays.
    """
    def hex_id():
        return uuid.uuid4().hex

    sample_questions = sorted(
        [{"id": hex_id(), "question": [q]} for q in config["sample_questions"]],
        key=lambda x: x["id"],
    )

    tables = []
    for t in sorted(config["tables"], key=lambda t: t["identifier"]):
        entry = {"identifier": t["identifier"]}
        if "column_configs" in t:
            clean_cols = []
            for cc in sorted(t["column_configs"], key=lambda c: c["column_name"]):
                clean_cc = {
                    "column_name": cc["column_name"],
                    "enable_format_assistance": cc.get("enable_format_assistance", True),
                    "enable_entity_matching": cc.get("enable_entity_matching", False),
                }
                if "description" in cc:
                    clean_cc["description"] = [cc["description"]]
                if cc.get("hidden"):
                    clean_cc["exclude"] = True
                clean_cols.append(clean_cc)
            entry["column_configs"] = clean_cols
        tables.append(entry)

    # text_instructions must be exactly ONE item with all lines in the content array
    text_instructions = [
        {"id": hex_id(), "content": [line + "\n" for line in config.get("text_instructions", [])]}
    ]

    example_question_sqls = sorted(
        [
            {
                "id": hex_id(),
                "question": [eq["question"]],
                "sql": [line + "\n" for line in eq["sql"].split("\n")],
            }
            for eq in config.get("example_question_sqls", [])
        ],
        key=lambda x: x["id"],
    )

    sql_snippets = {}
    if "sql_snippets" in config:
        for category, items in config["sql_snippets"].items():
            sql_snippets[category] = sorted(
                [{"id": hex_id(), "sql": [s["sql"]], "display_name": s["display_name"]} for s in items],
                key=lambda x: x["id"],
            )

    space = {
        "version": 2,
        "config": {"sample_questions": sample_questions},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": text_instructions,
            "example_question_sqls": example_question_sqls,
        },
    }
    if sql_snippets:
        space["instructions"]["sql_snippets"] = sql_snippets

    return space


def _check_dotted_ident(name: str, kind: str) -> str:
    for part in name.split("."):
        _check_ident(part, f"{kind} part")
    return name


def add_table_constraints(host: str, headers: dict, warehouse_id: str,
                          genie_config: dict):
    """Add PK/FK constraints to tables so Genie auto-detects join relationships.

    Reads table_joins from the genie_space.json config and derives PK/FK
    constraints. Silently skips if constraints already exist.
    """
    table_joins = genie_config.get("table_joins", [])
    if not table_joins:
        return

    # Validate every identifier from config before any SQL interpolation.
    for tj in table_joins:
        _check_dotted_ident(tj["left_table_identifier"], "left_table_identifier")
        _check_dotted_ident(tj["right_table_identifier"], "right_table_identifier")
        for jc in tj["join_columns"]:
            _check_ident(jc["left_column"], "left_column")
            _check_ident(jc["right_column"], "right_column")

    # Collect all PK columns: any column that appears as a join target
    pk_columns: dict[str, str] = {}  # table_identifier -> column_name
    for tj in table_joins:
        right_table = tj["right_table_identifier"]
        for jc in tj["join_columns"]:
            pk_columns[right_table] = jc["right_column"]
        left_table = tj["left_table_identifier"]
        for jc in tj["join_columns"]:
            if left_table not in pk_columns:
                pk_columns[left_table] = jc["left_column"]

    # Step 1: SET NOT NULL on PK columns
    for table_id, col in pk_columns.items():
        try:
            execute_sql(host, headers, warehouse_id,
                        f"ALTER TABLE {table_id} ALTER COLUMN {col} SET NOT NULL")
        except Exception:
            pass  # already NOT NULL or other issue

    # Step 2: Add PRIMARY KEY constraints
    for table_id, col in pk_columns.items():
        table_short = table_id.split(".")[-1]
        try:
            execute_sql(host, headers, warehouse_id,
                        f"ALTER TABLE {table_id} ADD CONSTRAINT pk_{table_short} "
                        f"PRIMARY KEY ({col}) NOT ENFORCED")
        except Exception:
            pass  # already exists

    # Step 3: Add FOREIGN KEY constraints
    for tj in table_joins:
        left_table = tj["left_table_identifier"]
        right_table = tj["right_table_identifier"]
        for jc in tj["join_columns"]:
            fk_table = left_table
            fk_col = jc["left_column"]
            ref_table = right_table
            ref_col = jc["right_column"]
            fk_short = fk_table.split(".")[-1]
            cname = f"fk_{fk_short}_{fk_col}"
            try:
                execute_sql(host, headers, warehouse_id,
                            f"ALTER TABLE {fk_table} ADD CONSTRAINT {cname} "
                            f"FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col}) NOT ENFORCED")
            except Exception:
                pass  # already exists


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------

def find_existing_genie_space(host: str, headers: dict, space_title: str) -> Optional[str]:
    """Search for an existing Genie space by title. Returns space_id or None."""
    try:
        resp = api_request("GET", f"{host}/api/2.0/genie/spaces",
                           headers=headers, params={"page_size": 100})
        spaces = resp.json().get("spaces", [])
        for s in spaces:
            if s.get("title") == space_title:
                return s["space_id"]
    except Exception as e:
        log.warning(f"Failed to list Genie spaces: {e}")
    return None


def check_catalog_exists(host: str, headers: dict, warehouse_id: str, catalog_name: str) -> bool:
    """Check if a catalog already has tables."""
    try:
        result = execute_sql(host, headers, warehouse_id,
                             f"SHOW TABLES IN {catalog_name}.`default`")
        data = result.get("result", {}).get("data_array", [])
        return len(data) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main provisioning function
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[str, str, int, int], None]


def provision_scenario(
    scenario_key: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> dict:
    """
    Provision a complete scenario into the current workspace.

    Args:
        scenario_key: Directory name under scenarios/ (e.g., "HR", "marketing")
        progress_callback: Called with (step, message, progress, total) for each step

    Returns:
        {"genie_space_id": ..., "genie_url": ..., "catalog_name": ...}
    """
    total_steps = 8

    def report(step: str, message: str, progress: int):
        log.info(f"[{scenario_key}] Step {progress}/{total_steps}: {message}")
        if progress_callback:
            progress_callback(step, message, progress, total_steps)

    _check_path_ident(scenario_key, "scenario_key")

    lock = _get_lock(scenario_key)
    with lock:
        # Load scenario config
        scenario_dir = SCENARIOS_DIR / scenario_key
        genie_config = json.loads((scenario_dir / "genie_space.json").read_text())
        catalog_name = _check_ident(genie_config["catalog_name"], "catalog_name")
        space_title = genie_config["space_title"]
        space_description = genie_config["space_description"]
        data_dir = scenario_dir / "data"

        # Authenticate
        report("auth", "Connecting to workspace...", 1)
        host, headers = get_auth()

        # Find warehouse
        report("warehouse", "Finding SQL warehouse...", 2)
        warehouse_id, warehouse_name = get_warehouse_id(host, headers)
        log.info(f"[{scenario_key}] Using warehouse: {warehouse_name} ({warehouse_id})")

        # Idempotency check
        existing_space_id = find_existing_genie_space(host, headers, space_title)
        if existing_space_id and check_catalog_exists(host, headers, warehouse_id, catalog_name):
            # Ensure PK/FK constraints exist for join auto-detection
            report("constraints", "Verifying table relationships...", 3)
            add_table_constraints(host, headers, warehouse_id, genie_config)
            # Update the Genie space config in case it changed
            report("genie", "Updating investigation room...", 7)
            serialized_space = build_serialized_space(genie_config)
            serialized_space_json = json.dumps(serialized_space)
            patch_body = {
                "title": space_title,
                "description": space_description,
                "serialized_space": serialized_space_json,
            }
            api_request("PATCH", f"{host}/api/2.0/genie/spaces/{existing_space_id}",
                        headers=headers, json=patch_body)
            genie_url = f"{host}/genie/rooms/{existing_space_id}?isDbOne=true&utm_source=databricks-one"
            report("done", "Already provisioned!", total_steps)
            return {
                "genie_space_id": existing_space_id,
                "genie_url": genie_url,
                "catalog_name": catalog_name,
            }

        # Create catalog and schema
        report("catalog", "Setting up the evidence locker...", 3)
        execute_sql(host, headers, warehouse_id, f"CREATE CATALOG IF NOT EXISTS {catalog_name}")
        execute_sql(host, headers, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.`default`")

        # Create volume and upload CSVs
        report("upload", "Loading the evidence files...", 4)
        volume_name = "data_upload"
        execute_sql(host, headers, warehouse_id,
                    f"CREATE VOLUME IF NOT EXISTS {catalog_name}.`default`.{volume_name}")

        csv_files = sorted(data_dir.glob("*.csv"))
        for csv_file in csv_files:
            volume_path = f"/Volumes/{catalog_name}/default/{volume_name}/{csv_file.name}"
            log.info(f"[{scenario_key}] Uploading {csv_file.name}...")
            upload_file_to_volume(host, headers, str(csv_file), volume_path)

        # Create tables from CSVs
        report("tables", "Cataloging the evidence...", 5)
        for csv_file in csv_files:
            table_name = _check_ident(csv_file.stem.lower().replace("-", "_"), "table_name")
            file_path = f"/Volumes/{catalog_name}/default/{volume_name}/{csv_file.name}"
            log.info(f"[{scenario_key}] Creating table: {catalog_name}.default.{table_name}")
            execute_sql(host, headers, warehouse_id, f"""
                CREATE OR REPLACE TABLE {catalog_name}.`default`.{table_name}
                AS SELECT * FROM read_files(
                    '{file_path}',
                    format => 'csv',
                    header => 'true',
                    inferSchema => 'true'
                )
            """)

        # Grant access on catalog and default schema
        report("grants", "Securing access...", 6)
        execute_sql(host, headers, warehouse_id,
                    f"GRANT USE CATALOG ON CATALOG {catalog_name} TO `account users`")
        execute_sql(host, headers, warehouse_id,
                    f"GRANT USE SCHEMA ON SCHEMA {catalog_name}.`default` TO `account users`")
        execute_sql(host, headers, warehouse_id,
                    f"GRANT SELECT ON SCHEMA {catalog_name}.`default` TO `account users`")

        # Add PK/FK constraints so Genie auto-detects joins
        report("constraints", "Setting up table relationships...", 7)
        add_table_constraints(host, headers, warehouse_id, genie_config)

        # Create or update Genie space
        report("genie", "Opening the investigation room...", 8)
        serialized_space = build_serialized_space(genie_config)
        serialized_space_json = json.dumps(serialized_space)

        if existing_space_id:
            # Update existing (tables were missing, now re-created)
            patch_body = {
                "title": space_title,
                "description": space_description,
                "serialized_space": serialized_space_json,
            }
            api_request("PATCH", f"{host}/api/2.0/genie/spaces/{existing_space_id}",
                        headers=headers, json=patch_body)
            space_id = existing_space_id
        else:
            create_body = {
                "title": space_title,
                "description": space_description,
                "warehouse_id": warehouse_id,
                "serialized_space": serialized_space_json,
            }
            resp = api_request("POST", f"{host}/api/2.0/genie/spaces",
                               headers=headers, json=create_body)
            space_id = resp.json()["space_id"]

        # Grant CAN_RUN on Genie space
        api_request("PUT", f"{host}/api/2.0/permissions/genie/{space_id}",
                    headers=headers,
                    json={
                        "access_control_list": [
                            {"group_name": "users", "permission_level": "CAN_RUN"}
                        ]
                    })

        genie_url = f"{host}/genie/rooms/{space_id}?isDbOne=true&utm_source=databricks-one"
        report("done", "Your case is ready!", total_steps)

        return {
            "genie_space_id": space_id,
            "genie_url": genie_url,
            "catalog_name": catalog_name,
        }
