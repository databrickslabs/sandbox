# Marketplace Provisioning App

## Goal

Provision Genie spaces and AI/BI dashboards for non-technical users on Databricks Free Edition — without requiring them to run a notebook.

## Approach: Marketplace App (ephemeral provisioner)

1. User clicks "Get" on a Marketplace App listing
2. App installs and runs in their workspace
3. App's service principal creates Genie spaces + dashboards via REST API
4. App grants permissions to workspace users
5. User deletes the app (frees up the single Free Edition app slot)

### Why this approach

| Alternative considered | Why it doesn't work |
|---|---|
| Marketplace data product | Only supports data assets (tables, volumes, models) — not Genie spaces or dashboards |
| DABS | Requires CLI installation + auth — not viable for non-technical users |
| "Open in Databricks" | Engineering done but not launched — no timeline |
| Hosted external web app | Major build (OAuth integration), unclear Free Edition support |

### Why a Marketplace App is feasible for us

Marketplace Apps are first-party only (must be in `databricks` or `databricks-labs` GitHub org). This is fine since this is a Databricks-internal project. Requires going through the Marketplace listing SOP with the Marketplace team.

## API Details

### Genie Space Creation

- **Endpoint**: `POST /api/2.0/genie/spaces` (GA since March 2026)
- **Python SDK**: `w.genie.create_space(warehouse_id, serialized_space, title, parent_path)`
- **Key payload**: `serialized_space` JSON string containing tables, instructions, sample questions, example SQL, join specs
- **Limits**: Max 30 tables/space, 100 instructions, 100 example SQL queries
- **Permissions after creation**: Must use `PUT /api/2.0/permissions/genie/spaces/{space_id}` (Genie API has no built-in permissions management)

#### Serialized Space Structure

```json
{
  "version": 1,
  "config": {
    "sample_questions": [{"id": "<32-char-hex>", "question": ["..."]}]
  },
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.table",
        "description": ["..."],
        "column_configs": [{"column_name": "...", "description": ["..."], "synonyms": [...]}]
      }
    ]
  },
  "instructions": {
    "text_instructions": [{"id": "<32-char-hex>", "content": ["..."]}],
    "example_question_sqls": [{"id": "<32-char-hex>", "question": ["..."], "sql": ["..."]}]
  }
}
```

IDs must be 32-character lowercase hex. Collections must be sorted alphabetically by identifier.

### Dashboard Creation + Publishing

- **Create draft**: `POST /api/2.0/lakeview/dashboards`
- **Publish**: `POST /api/2.0/lakeview/dashboards/{dashboard_id}/published`
- **Python SDK**: `w.lakeview.create(dashboard)` then `w.lakeview.publish(dashboard_id, embed_credentials, warehouse_id)`

#### Create Request

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard

w = WorkspaceClient()

dashboard = w.lakeview.create(
    dashboard=Dashboard(
        display_name="My Dashboard",
        serialized_dashboard='{"pages": [...], "datasets": [...]}',
        warehouse_id="<warehouse_id>",
        parent_path="/Users/user@example.com"
    )
)

w.lakeview.publish(
    dashboard_id=dashboard.dashboard_id,
    embed_credentials=True,
    warehouse_id="<warehouse_id>"
)
```

#### Serialized Dashboard Structure

```json
{
  "pages": [
    {
      "name": "<uuid>",
      "displayName": "Page Title",
      "layout": [
        {
          "widget": {"name": "<uuid>", "queries": [...], "spec": {...}},
          "position": {"x": 0, "y": 0, "width": 6, "height": 4}
        }
      ]
    }
  ],
  "datasets": [
    {
      "name": "<uuid>",
      "displayName": "Dataset Name",
      "query": "SELECT * FROM catalog.schema.table"
    }
  ]
}
```

No formal JSON schema exists — reverse-engineer by exporting a prototype dashboard.

#### embed_credentials

- `true` ("Shared data permission"): Viewers query using publisher's credentials. Better performance (shared cache). Publisher must have SELECT on all tables.
- `false` ("Individual data permission"): Each viewer needs their own table access.
- **Known issue**: Delta Sharing tables do NOT work with `embed_credentials: true`.

### Permissions Management

After creating objects, the app must grant access:

- **Dashboards**: `PUT /api/2.0/permissions/dashboards/{workspace_object_id}`
- **Genie spaces**: `PUT /api/2.0/permissions/genie/spaces/{space_id}`

The service principal is the owner by default — other users have no access until explicitly granted.

## Free Edition Constraints

| Constraint | Impact |
|---|---|
| 1 app per account | App must be deleted after provisioning to free the slot |
| Apps auto-stop after 24 hours | Fine — provisioning takes seconds |
| SP creation reported as unreliable | **Biggest risk** — must validate early |
| Serverless SQL warehouse (quota-limited) | Genie + dashboards need a warehouse — should work |
| Genie available on Free Edition | Confirmed via Slack (with some bugs tracked) |
| Dashboards available on Free Edition | Confirmed via docs and blog posts |

## Build Plan

### Step 1: Validate (do this first)

- [ ] Confirm a Marketplace App can install and run its service principal on Free Edition
- [ ] Confirm the SP can create a Genie space on Free Edition
- [ ] Confirm the SP can create + publish a dashboard on Free Edition
- [ ] Confirm the SP can grant permissions to workspace users

### Step 2: Build prototype

- [ ] Create target Genie space + dashboard manually in a dev workspace
- [ ] Export `serialized_space` and `serialized_dashboard` JSON via API
- [ ] Build minimal app (Streamlit/Flask) that provisions from bundled configs
- [ ] App flow: startup -> detect warehouse -> create Genie space -> create + publish dashboard -> grant permissions -> show "Done" screen with links

### Step 3: Marketplace listing

- [ ] Host app in `databricks` or `databricks-labs` GitHub org
- [ ] Go through Marketplace listing SOP
- [ ] Contacts: Jianyu Zhou (Marketplace Apps eng), DJ Sharkey (Marketplace), Tia Chang (Marketplace PM)

### Step 4: Self-cleanup

- [ ] Test whether the app can call `DELETE /api/2.0/apps/{app_name}` on itself
- [ ] Fallback: show "Done — you can delete this app" with instructions

## Key Contacts

| Person | Role | Relevance |
|---|---|---|
| Jianyu Zhou | Marketplace Apps engineer | Marketplace App listing process |
| DJ Sharkey | Marketplace | Listing process |
| Tia Chang | Marketplace PM | Feature requests, listing approval |
| Naim Achahboun | Apps team | Recommended DABS pattern, Apps technical questions |
| Will Valori | Free Edition PM | Free Edition capabilities/limitations |
| Miranda Luna | PM, AI/BI Genie | Genie API, limits, roadmap |
| Hanlin Sun | PM/Eng, AI/BI Genie | Pricing, API limits |

## Relevant Slack Channels

- `#ai-bi-genie` — Genie questions
- `#eng-databricks-apps` — Databricks Apps + Genie resources
- `#free-edition` — Free Edition feature availability
- `#apa-agent-bricks` — Agent Bricks + Genie integration

## Research Sources

- [Genie API reference](https://docs.databricks.com/api/workspace/genie)
- [Genie Space Import/Export guide](https://docs.google.com/document/d/14hsOeDAtylMlSKVkakbYMGBIFr_SihR-Rrij5NCnT4k)
- [Dashboard CRUD API tutorial](https://docs.databricks.com/aws/en/dashboards/tutorials/dashboard-crud-api)
- [Lakeview API reference](https://docs.databricks.com/api/workspace/lakeview/create)
- [Dashboard permissions](https://docs.databricks.com/aws/en/dashboards/tutorials/manage-permissions)
- [Python SDK - Genie](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dashboards/genie.html)
- [Python SDK - Lakeview](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dashboards/lakeview.html)
- [Apps FAQ (go/apps/faq)](https://go/apps/faq)
- [AI/BI FAQ (go/aibi/faq)](https://docs.google.com/document/d/1vjcYSiTilHDRppuas9Kh8uAw_TOFC-62U2-nweRmx_I)
- [Google Doc with full research](https://docs.google.com/document/d/17UNJYk2jk_T21RtTMM7Elky_9Id2wGmmmb6jAi5VE9A/edit)
