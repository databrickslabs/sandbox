# Databricks Supervisor Agent Replication Tools

Export a Supervisor Agent (with its knowledge assistants, genie rooms, UC functions, and MCP-server tools) from one workspace and import it into another.

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

### What gets exported

- **Supervisor agent** definition (name, description, instructions)
- **Knowledge assistants** with their knowledge source definitions and downloaded files from UC volumes
- **Genie rooms** with their serialized space payloads
- **UC function tools** (`uc_function`) — recorded by full name (`catalog.schema.function_name`)
- **Connection tools** (`connection`, used for external MCP servers) — recorded by name
- **App tools** (`app`, used for custom MCP servers / custom agents) — recorded by name
- The `volume` tool type is currently recorded in the manifest as skipped

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
| `--connection-map` | No | Comma-separated `old=new` rename rules for connection-type tools |
| `--app-map` | No | Comma-separated `old=new` rename rules for app-type tools |
| `--yes-update` | No | Always update existing objects without prompting (mutually exclusive with `--skip-existing`) |
| `--skip-existing` | No | Never update existing objects, always reuse them (mutually exclusive with `--yes-update`) |
| `--force` | No | Skip pre-flight dependency checks; proceed even if referenced tables/indexes/volumes/functions/connections/apps are missing |

### Catalog mapping

The `--catalog-map` option rewrites fully-qualified names (`catalog.schema.name`) in:

- Genie room table references
- Knowledge source `index` and `file_table` names
- UC function tool names

Each rule is `old=new`:

- **Single-level** `old_catalog=new_catalog` -- replaces the catalog, preserves schema and table
- **Two-level** `old_catalog.old_schema=new_catalog.new_schema` -- replaces both catalog and schema, preserves table name

More specific (longer) prefixes are matched first. Names that don't match any rule are left unchanged.

### Connection and app name maps

`--connection-map` and `--app-map` accept exact-name renames as `old=new` pairs (comma-separated). Connections and apps are workspace/UC-level singletons with flat names (no catalog prefix), so they are renamed by exact match. Names that don't appear in the map are left unchanged.

```
--connection-map "old_mcp=new_mcp,sandbox_mcp=prod_mcp"
--app-map "old_app_name=new_app_name"
```

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
- **Supervisor agent**: tools are added, removed, or updated. Tools are matched by `tool_id`. Tools whose `tool_type` is supported but where the target resource changed (e.g., the function/connection/app name was remapped) are deleted and recreated, since the Tool API only allows updating `description` in place. Tools of types that the import tool does not support (currently only `volume`) on the existing agent are left untouched.

### Prerequisites in the target workspace

Before running the import, ensure the following objects exist in the target workspace:

- **SQL warehouse** -- the warehouse ID passed via `--warehouse-id` must be an active warehouse
- **UC volume** -- the volume path passed via `--volume-path` must exist (the tool creates subdirectories within it)
- **Tables referenced by genie rooms** -- all tables in genie room data sources (after catalog mapping is applied) must exist in the target workspace
- **Vector search indexes** -- any indexes referenced by knowledge assistant `index`-type sources (after catalog mapping) must exist
- **Tables for file_table sources** -- any tables referenced by `file_table`-type knowledge sources (after catalog mapping) must exist
- **UC functions** -- any functions referenced by `uc_function` tools (after catalog mapping) must exist
- **UC connections** -- any connections referenced by `connection` tools (after `--connection-map`) must exist
- **Databricks Apps** -- any apps referenced by `app` tools (after `--app-map`) must exist

The import tool uploads knowledge assistant files to the target volume automatically, but it does not migrate tables, indexes, UC functions, connections, apps, or other objects between workspaces. Those must be deployed separately.

### What the import creates / updates

1. Validates dependencies (Phase 0)
2. For each knowledge assistant: uploads files (if needed), then creates or updates the KA and reconciles its knowledge sources
3. For each genie room: creates or updates the room with remapped table identifiers
4. Creates or updates the supervisor agent
5. Reconciles tools on the agent to match the manifest

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
