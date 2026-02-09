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
- **Terraform:** `warehouse_grants.tf` grants `CAN_USE` to the five groups when `genie_default_warehouse_id` is set. Required for consumers to run queries in Genie.

## 4. Data access

- **Unity Catalog:** At least **SELECT** (and **USE CATALOG** / **USE SCHEMA**) on all UC objects used by the Genie Space (e.g. catalog `fincat`, schema `fincat.finance`). ABAC policies (defined in SQL) further restrict what each group sees at query time.
- **Terraform:** `uc_grants.tf` grants `USE_CATALOG`, `USE_SCHEMA`, and `SELECT` on the finance catalog/schema to the five groups.

## 5. Genie Space ACLs

- **Genie Space:** At least **CAN VIEW** and **CAN RUN** on the Genie Space so that the groups can open and run queries in the space.
- **Automation:** Implemented via the Genie REST API (script in `scripts/` or runbook below). Terraform does not yet support Genie Space ACLs; migrate when the provider adds support.

### Runbook: Set Genie Space ACLs via API

1. Obtain a Databricks workspace token (or OAuth) with permission to manage the Genie Space.
2. Get the Genie Space ID (from the Genie UI or via the list spaces API).
3. Call the permissions/ACL API for the Genie Space to add the five groups (or a single "Genie consumers" group) with at least **CAN VIEW** and **CAN RUN**.  
   See [Genie set-up and ACLs](https://docs.databricks.com/aws/en/genie/set-up) and [REST API for Genie spaces](https://community.databricks.com/t5/generative-ai/databricks-rest-api-to-manage-and-deploy-genie-spaces/td-p/107937) for the exact endpoint and payload.

## Summary checklist

| Requirement           | Implemented in                          |
|-----------------------|-----------------------------------------|
| Groups                | Terraform: `main.tf`                     |
| Workspace assignment  | Terraform: `main.tf`                     |
| Consumer (One UI only)| Terraform: `main.tf` (entitlements)     |
| Warehouse CAN USE     | Terraform: `warehouse_grants.tf`         |
| UC data (SELECT, etc.)| Terraform: `uc_grants.tf`               |
| Genie Space ACLs      | API: `scripts/set_genie_space_acls.sh`  |
