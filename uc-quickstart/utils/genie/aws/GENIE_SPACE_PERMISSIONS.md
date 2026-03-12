# Permissions Required for a Genie Space

This document lists everything that must be in place for business users (the groups defined in `abac.auto.tfvars`) to use an AI/BI Genie Space.

## 1. Identity

- **Business groups:** Created at account level (Terraform: `databricks_group` in `main.tf`).
  Groups are defined dynamically in `abac.auto.tfvars` under the `groups` variable.
- **Workspace assignment:** Account-level groups are assigned to the workspace (Terraform: `databricks_mws_permission_assignment` with `USER` in `main.tf`).

## 2. Entitlements (Consumer = Databricks One UI only)

- **Consumer access:** When `workspace_consume` is the **only** entitlement for a user/group, they get the **Databricks One UI** experience (dashboards, Genie spaces, apps) and do **not** get the full workspace UI (clusters, notebooks, etc.).
- **Terraform:** `databricks_entitlements` in `main.tf` sets `workspace_consume = true` for each group. No other entitlements are set so that consumers see One UI only.

## 3. Compute

- **SQL warehouse:** A single SQL warehouse is used for both masking function deployment and the Genie Space. Genie embeds on this warehouse; end users do **not** need explicit **CAN USE** on the warehouse.
- **Terraform:** `warehouse.tf` handles warehouse resolution:
  - `sql_warehouse_id` set in `env.auto.tfvars` -> reuses the existing warehouse (dev)
  - `sql_warehouse_id` empty or omitted -> auto-creates a serverless warehouse (prod)

## 4. Data access

- **Unity Catalog:** At least **SELECT** (and **USE CATALOG** / **USE SCHEMA**) on all UC objects used by the Genie Space. Catalogs are auto-derived from fully-qualified table names in `tag_assignments` and `fgac_policies`. ABAC policies further restrict what each group sees at query time.
- **Terraform:** `uc_grants.tf` grants `USE_CATALOG`, `USE_SCHEMA`, and `SELECT` on all relevant catalogs to all configured groups.

## 5. Genie Space (create + ACLs)

- **Genie Space:** Create a Genie Space with the tables from `uc_tables` (in `env.auto.tfvars`) and grant at least **CAN VIEW** and **CAN RUN** to all groups.
- **Automation:** Terraform manages Genie Space lifecycle via `genie_space.tf`:
  - **`genie_space_id` empty** (greenfield): `terraform apply` auto-creates a Genie Space from `uc_tables`, sets ACLs, and trashes the space on `terraform destroy`.
  - **`genie_space_id` set** (existing): `terraform apply` only applies CAN_RUN ACLs to the existing space.

### Auto-create mode

Set `genie_space_id = ""` in `env.auto.tfvars` and ensure `uc_tables` is non-empty. Terraform runs `genie_space.sh create` automatically during apply. Wildcards (`catalog.schema.*`) are expanded via the UC Tables API.

### Existing space mode

Set `genie_space_id` to your Genie Space ID in `env.auto.tfvars`. Terraform runs `genie_space.sh set-acls` to grant CAN_RUN to all configured groups.

### Manual script usage

The script can also be used independently outside of Terraform:

```bash
# Create
GENIE_GROUPS_CSV=$(terraform output -raw genie_groups_csv) \
GENIE_TABLES_CSV="cat.schema.t1,cat.schema.t2" \
./scripts/genie_space.sh create

# Set ACLs only
GENIE_GROUPS_CSV=$(terraform output -raw genie_groups_csv) \
GENIE_SPACE_OBJECT_ID=<space_id> \
./scripts/genie_space.sh set-acls

# Trash
GENIE_ID_FILE=.genie_space_id ./scripts/genie_space.sh trash
```

## Summary checklist

| Requirement            | Implemented in                                                                 |
|------------------------|--------------------------------------------------------------------------------|
| Groups                 | Terraform: `main.tf` (from `groups` in `abac.auto.tfvars`)                     |
| Workspace assignment   | Terraform: `main.tf`                                                           |
| Consumer (One UI only) | Terraform: `main.tf` (entitlements)                                            |
| Warehouse              | Terraform: `warehouse.tf` (reuses `sql_warehouse_id` or auto-creates)          |
| UC data (SELECT, etc.) | Terraform: `uc_grants.tf` (auto-derived catalogs)                              |
| Genie Space + ACLs     | Terraform: `genie_space.tf` (auto-create or ACLs-only based on `genie_space_id`) |
