# Permissions Required for a Genie Space

This document lists everything that must be in place for business users (the five finance groups) to use an AI/BI Genie Space.

## 1. Identity

- **Business groups:** Created at account level (Terraform: `databricks_group` in `main.tf`).  
  Groups: `Junior_Analyst`, `Senior_Analyst`, `US_Region_Staff`, `EU_Region_Staff`, `Compliance_Officer`.
- **Workspace assignment:** Account-level groups are assigned to the workspace (Terraform: `databricks_mws_permission_assignment` with `USER` in `main.tf`).

## 2. Entitlements (Consumer = Databricks One UI only)

- **Consumer access:** When `workspace_consume` is the **only** entitlement for a user/group, they get the **Databricks One UI** experience (dashboards, Genie spaces, apps) and do **not** get the full workspace UI (clusters, notebooks, etc.).
- **Terraform:** `databricks_entitlements` in `main.tf` sets `workspace_consume = true` for each of the five groups. No other entitlements are set so that consumers see One UI only.

## 3. Compute

- **SQL warehouse:** At least **CAN USE** on the SQL warehouse designated for the Genie Space.
- **Terraform:** `genie_warehouse.tf` creates a **serverless SQL warehouse** (or use an existing one via `genie_use_existing_warehouse_id`). `warehouse_grants.tf` grants `CAN_USE` to the five finance groups and the **users** group. Required for consumers to run queries in Genie.

## 4. Data access

- **Unity Catalog:** At least **SELECT** (and **USE CATALOG** / **USE SCHEMA**) on all UC objects used by the Genie Space (e.g. catalog `fincat`, schema `fincat.finance`). ABAC policies (defined in SQL) further restrict what each group sees at query time.
- **Terraform:** `uc_grants.tf` grants `USE_CATALOG`, `USE_SCHEMA`, and `SELECT` on the finance catalog/schema to the five groups.

## 5. Genie Space (create + ACLs)

- **Genie Space:** Create a Genie Space with all tables in the finance schema and grant at least **CAN VIEW** and **CAN RUN** to the five groups.
- **Automation:** Run **`scripts/genie_space.sh create`** after Terraform apply. It creates the Genie Space via the API (with the warehouse from `terraform output -raw genie_warehouse_id` and all finance schema tables) and sets ACLs for the five groups. Terraform does not yet support Genie Space creation or ACLs; migrate when the provider adds support.

### Runbook: Create Genie Space and set ACLs

1. Run **terraform apply** (creates serverless warehouse and grants CAN_USE to five groups + users).
2. Run **`GENIE_WAREHOUSE_ID=$(terraform output -raw genie_warehouse_id) ./scripts/genie_space.sh create`** (creates the space with all finance tables and sets CAN_RUN for the five groups).

### Runbook: Set Genie Space ACLs only (existing space)

1. Obtain a Databricks workspace token (or OAuth) with permission to manage the Genie Space.
2. Get the Genie Space ID (from the Genie UI or via the list spaces API).
3. Run **`./scripts/genie_space.sh set-acls [workspace_url] [token] [space_id]`** (or set `GENIE_SPACE_OBJECT_ID` and run `./scripts/genie_space.sh set-acls`). This grants the five finance groups **CAN_RUN**.  
   Alternatively, call the permissions/ACL API directly; see [Genie set-up and ACLs](https://docs.databricks.com/aws/en/genie/set-up) and [REST API for Genie spaces](https://community.databricks.com/t5/generative-ai/databricks-rest-api-to-manage-and-deploy-genie-spaces/td-p/107937).

## Summary checklist

| Requirement           | Implemented in                          |
|-----------------------|-----------------------------------------|
| Groups                | Terraform: `main.tf`                     |
| Workspace assignment  | Terraform: `main.tf`                     |
| Consumer (One UI only)| Terraform: `main.tf` (entitlements)     |
| Warehouse (create)    | Terraform: `genie_warehouse.tf` (serverless) |
| Warehouse CAN USE     | Terraform: `warehouse_grants.tf` (five groups + users) |
| UC data (SELECT, etc.)| Terraform: `uc_grants.tf`               |
| Genie Space (create + ACLs) | Script: `scripts/genie_space.sh create` (all finance tables + ACLs) |
