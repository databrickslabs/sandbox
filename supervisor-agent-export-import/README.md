# Databricks Supervisor Agent Replication Tools

Export a Supervisor Agent (with its knowledge assistants, genie rooms, examples, and any of the 14 supported tool types) from one workspace and import it into another.

## Prerequisites

- Python 3.10+
- `databricks-sdk` installed (`pip install databricks-sdk`)
- Authentication configured via environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`) or a `~/.databrickscfg` profile (set `DATABRICKS_CONFIG_PROFILE` to select a profile)

## Export

Exports a supervisor agent and all its supported tools into a portable directory structure.

```bash
python export_supervisor_agent.py --name "My Agent" --output-dir ./export
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--name` | Yes | Display name of the supervisor agent |
| `--output-dir` | No | Output directory (default: `./export`) |
| `--include-volume-contents` | No | For `volume`-type tools, also download the volume's contents into the export directory (default: off) |

### What gets exported

- **Supervisor agent** definition (name, description, instructions)
- **Knowledge assistants** with their knowledge source definitions and downloaded files from UC volumes
- **Genie rooms** with their serialized space payloads
- **Examples** (top-level `examples` array on the agent — `question` + `guidelines`)
- **All 14 tool types** are now exported by recording the type-specific spec:
  - UC objects identified by full name (`catalog.schema.name`): `uc_function`, `uc_table`, `vector_search_index`, `volume`, `schema`, `catalog`
  - For `volume` tools, pass `--include-volume-contents` to also download the volume's files into `<agent_dir>/volumes/<sanitized_name>/`. The import will sync these files to the target volume.
  - Workspace-level singletons identified by name: `serving_endpoint`, `uc_connection`, `app`
  - Resources identified by opaque ID, augmented at export with the resource's `display_name` for cross-workspace lookup at import: `lakeview_dashboard`, `supervisor_agent`
  - Parameter-less: `web_search`
  - Existing managed types: `knowledge_assistant`, `genie_space`

### Output structure

```
<output-dir>/<agent_name>/
    manifest.json
    knowledge_assistants/<ka_name>/
        definition.json
        files/<source_dir>/...
    genie_rooms/<room_name>/
        definition.json
        serialized.json
```

## Import

Recreates the agent in a target workspace using the exported data. The import is **idempotent**: re-running it on the same export reuses existing objects silently, and reconciles their configuration when it differs.

```bash
python import_supervisor_agent.py \
    --input-dir ./export/my-agent \
    --warehouse-id <warehouse_id> \
    --volume-path /Volumes/catalog/schema/volume \
    --catalog-map "old_catalog=new_catalog,old_cat.old_schema=new_cat.new_schema"
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--input-dir` | Yes | Path to the exported agent directory (containing `manifest.json`) |
| `--warehouse-id` | Yes | SQL warehouse ID for genie rooms in the target workspace |
| `--volume-path` | Yes | UC volume base path where knowledge assistant files will be uploaded |
| `--catalog-map` | No | Comma-separated catalog/schema mapping rules for UC objects (see below) |
| `--connection-map` | No | Comma-separated `old=new` rename rules for `uc_connection` tools |
| `--app-map` | No | Comma-separated `old=new` rename rules for `app` tools |
| `--endpoint-map` | No | Comma-separated `old=new` rename rules for `serving_endpoint` tools |
| `--dashboard-map` | No | Comma-separated `old_display_name=new_display_name` rules for `lakeview_dashboard` tools |
| `--agent-map` | No | Comma-separated `old_display_name=new_display_name` rules for `supervisor_agent` tools (sub-agents) |
| `--yes-update` | No | Always update existing objects without prompting (mutually exclusive with `--skip-existing`) |
| `--skip-existing` | No | Never update existing objects, always reuse them (mutually exclusive with `--yes-update`) |
| `--force` | No | Skip pre-flight dependency checks; proceed even if referenced UC/workspace objects are missing |

### Catalog mapping

The `--catalog-map` option rewrites fully-qualified names (`catalog.schema.name`) in:

- Genie room `data_sources.tables[].identifier` (the registered tables)
- Genie room **per-table descriptions** (freeform text references to other tables)
- Genie room **text instructions** content
- Genie room **example SQL queries** (`instructions.example_question_sqls[].sql`)
- Genie room **benchmark canonical SQL** (`benchmarks.questions[].answer[].content`)
- Knowledge source `index` and `file_table` names
- Tool specs of types: `uc_function`, `uc_table`, `vector_search_index`, `volume`, `schema`, `catalog`

For SQL strings and freeform text, the rewriter uses a left word-boundary so it won't match inside longer identifiers (e.g. the rule `old_cat=new` won't change `my_old_cat.something`).

Each rule is `old=new`:

- **Single-level** `old_catalog=new_catalog` -- replaces the catalog, preserves schema and table
- **Two-level** `old_catalog.old_schema=new_catalog.new_schema` -- replaces both catalog and schema, preserves table name

More specific (longer) prefixes are matched first. Names that don't match any rule are left unchanged.

### Name maps

The other map flags accept exact-name renames as `old=new` pairs (comma-separated):

- `--connection-map` — `uc_connection` tools (UC connections, used for external MCP servers)
- `--app-map` — `app` tools (Databricks Apps, used for custom MCP / custom agents)
- `--endpoint-map` — `serving_endpoint` tools

```
--connection-map "old_mcp=new_mcp,sandbox_mcp=prod_mcp"
--app-map "old_app_name=new_app_name"
--endpoint-map "old_endpoint=new_endpoint"
```

### Lookup-by-display-name (dashboards and sub-agents)

For `lakeview_dashboard` and `supervisor_agent` tools, the source workspace's opaque ID is meaningless in the target. Instead:

1. The export captures the resource's `display_name` alongside its ID.
2. At import time, the tool looks up the matching `display_name` in the target workspace and uses the new ID for the tool spec.
3. If the display name has changed, use `--dashboard-map "old_name=new_name"` or `--agent-map "old_name=new_name"` to rewrite the lookup name before the search.
4. If neither lookup nor map resolves the resource, the pre-flight check fails (override with `--force`).

### Pre-flight checks

Before any creation or upload, the import tool validates that all referenced UC and workspace objects exist in the target workspace:

- The UC volume passed via `--volume-path`
- All tables referenced by genie rooms (after catalog mapping)
- All tables referenced by `file_table` knowledge sources (after catalog mapping)
- All vector search indexes referenced by `index` knowledge sources (after catalog mapping)
- All resources referenced by tool specs:
  - `uc_function`, `uc_table`, `vector_search_index`, `volume`, `schema`, `catalog` (after catalog mapping)
  - `uc_connection`, `app`, `serving_endpoint` (after the corresponding name map)
  - `lakeview_dashboard`, `supervisor_agent` (looked up by `display_name`, optionally renamed by `--dashboard-map` / `--agent-map`)
- `web_search` requires no dependency check, but the workspace must have it enabled (workspace-level enablement is enforced by the API at create time).

### Pre-flight checks

Before any creation or upload, the import tool validates that all referenced UC and workspace objects exist in the target workspace:

- The UC volume passed via `--volume-path`
- All tables referenced by genie rooms (after catalog mapping)
- All tables referenced by `file_table` knowledge sources (after catalog mapping)
- All vector search indexes referenced by `index` knowledge sources (after catalog mapping)
- All UC functions referenced by `uc_function` tools (after catalog mapping)
- All UC connections referenced by `connection` tools (after `--connection-map`)
- All Databricks Apps referenced by `app` tools (after `--app-map`)

If any are missing, the tool lists them and exits with a non-zero status. Pass `--force` to skip these checks (the API will fail later if the objects are still missing).

### Idempotency and conflict resolution

For each entity (supervisor agent, knowledge assistant, genie room), the tool first checks if one with the same name already exists in the target workspace:

- **Not found**: created from the export
- **Found, configuration matches**: reused silently, no changes made
- **Found, configuration differs**: depends on flags
  - **Default (interactive)**: prints a diff summary and prompts `Update? [y/N/s(kip)]`
    - `y` — apply all changes (top-level fields and child reconciliation)
    - `n` (default) — abort the entire import
    - `s` — skip this object only (reuse as-is) and continue
  - **`--yes-update`**: applies all changes without prompting
  - **`--skip-existing`**: reuses existing objects as-is without prompting

When updating, child objects are reconciled to match the manifest:

- **Knowledge assistant**: knowledge sources are added, removed, or updated. Sources are matched by `display_name` (which must be unique within the KA — duplicates abort the import). For `files` sources that are added or updated, their files are re-uploaded.
- **Supervisor agent — tools**: tools are added, removed, or updated. Tools are matched by `tool_id`. Tools whose `tool_type` is supported but where the target resource changed (e.g., a function/connection/app name was remapped, or a dashboard/sub-agent now resolves to a different ID) are deleted and recreated, since the Tool API only allows updating `description` in place. Tools of types not in the supported list on the existing agent are left untouched.
- **Supervisor agent — examples**: examples are added, removed, or updated to match the manifest. Examples are matched by their `question` text (which must be unique within the agent — duplicates abort the import). Both `question` and `guidelines` are reconciled.

### Prerequisites in the target workspace

Before running the import, ensure the following objects exist in the target workspace:

- **SQL warehouse** -- the warehouse ID passed via `--warehouse-id` must be an active warehouse
- **UC volume** -- the volume path passed via `--volume-path` must exist (the tool creates subdirectories within it)
- **Tables referenced by genie rooms** and `file_table` knowledge sources (after catalog mapping)
- **Vector search indexes** referenced by `index` knowledge sources or `vector_search_index` tools (after catalog mapping)
- **UC objects** referenced by tool specs (after catalog mapping): functions, tables, volumes, schemas, catalogs
- **UC connections** referenced by `uc_connection` tools (after `--connection-map`)
- **Databricks Apps** referenced by `app` tools (after `--app-map`)
- **Serving endpoints** referenced by `serving_endpoint` tools (after `--endpoint-map`)
- **Lakeview dashboards** referenced by `lakeview_dashboard` tools — looked up by `display_name`
- **Supervisor agents** referenced by `supervisor_agent` (sub-agent) tools — looked up by `display_name`

The import tool uploads knowledge assistant files to the target volume automatically, but it does not migrate tables, indexes, functions, connections, apps, dashboards, sub-agents, or other objects between workspaces. Those must be deployed separately.

### What the import creates / updates

1. Validates dependencies (Phase 0)
2. For each knowledge assistant: uploads files (if needed), then creates or updates the KA and reconciles its knowledge sources
3. For each genie room: creates or updates the room with remapped table identifiers
4. Resolves tool specs for non-managed types (looking up dashboards / sub-agents by `display_name`, applying name and catalog maps)
5. Creates or updates the supervisor agent
6. Reconciles tools on the agent to match the manifest
7. Reconciles examples on the agent to match the manifest

### Non-interactive use

If you run the import in an environment without an attached terminal (e.g., CI), you must pass either `--yes-update` or `--skip-existing`. The tool will refuse to start otherwise.

## Example: full replication workflow

```bash
# 1. Export from source workspace
DATABRICKS_CONFIG_PROFILE=source-workspace \
    python export_supervisor_agent.py --name "threat-analyst" --output-dir ./exports

# 2. Import into target workspace
DATABRICKS_CONFIG_PROFILE=target-workspace \
    python import_supervisor_agent.py \
        --input-dir ./exports/threat-analyst \
        --warehouse-id abc123def456 \
        --volume-path /Volumes/cybersecurity/default/documents \
        --catalog-map "dsl_dlt=new_catalog,sentinel_poc.logs=cyber.sentinel_logs"
```
