# Finance ABAC – Minimal 5-Group Demo (Terraform)

This Terraform module creates **account-level user groups** and **Unity Catalog tag policies** for the minimal finance ABAC demo, assigns groups to a workspace, grants **consumer entitlements**, and optionally adds **demo users** to groups.

## Overview

**5 groups** for 5 scenarios:

| Group | Description |
|-------|-------------|
| `Junior_Analyst` | Masked PII, last-4 card only, rounded transaction amounts |
| `Senior_Analyst` | Unmasked PII, full card number, full transaction details |
| `US_Region_Staff` | Row access limited to `CustomerRegion = 'US'` |
| `EU_Region_Staff` | Row access limited to `CustomerRegion = 'EU'` |
| `Compliance_Officer` | Full unmasked access (all regions, all columns) |

**5 scenarios:** (1) PII masking on Customers, (2) Fraud/card on CreditCards, (3) Fraud/transactions amount rounding, (4) US region row filter, (5) EU region row filter.

## What This Module Creates

- **Account-level groups** (5) via `databricks_group`
- **Workspace assignment** with USER permission via `databricks_mws_permission_assignment`
- **Consumer entitlement** (`workspace_consume = true`) via `databricks_entitlements` so users in these groups can use the workspace
- **Demo user membership** (optional): `kavya.parashar@databricks.com` → Junior_Analyst + US_Region_Staff; `louis.chen@databricks.com` → Senior_Analyst + EU_Region_Staff via `databricks_group_member` when user IDs are set in variables
- **Tag policies** (workspace): `aml_clearance`, `pii_level`, `pci_clearance`, `customer_region`, `data_residency` via `databricks_tag_policy` (if supported by your provider version)

## Usage

### 1. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
databricks_account_id     = "your-account-id"
databricks_client_id      = "your-service-principal-client-id"
databricks_client_secret  = "your-service-principal-secret"
databricks_workspace_id   = "1234567890123456"
databricks_workspace_host = "https://your-workspace.cloud.databricks.com"

# Optional: add demo users to groups (use account-level user IDs from Account Console > Users)
demo_user_junior_us_id = "12345678"   # kavya.parashar@databricks.com -> Junior_Analyst, US_Region_Staff
demo_user_senior_eu_id = "87654321"   # louis.chen@databricks.com -> Senior_Analyst, EU_Region_Staff
```

### 2. Apply

```bash
terraform init
terraform plan
terraform apply
```

### 3. After Terraform

1. **SQL in workspace:** Run in order: `0.1finance_abac_functions.sql` → `0.2finance_database_schema.sql` → `3.ApplyFinanceSetTags.sql` → `4.CreateFinanceABACPolicies.sql` (see `abac/finance/`).
2. **Test:** Run `5.TestFinanceABACPolicies.sql` as different users/groups.

## Outputs

| Output | Description |
|--------|-------------|
| `finance_group_ids` | Map of group names to group IDs |
| `finance_group_names` | List of 5 group names |
| `demo_scenario_groups` | Groups mapped to the 5 ABAC scenarios |
| `workspace_assignments` | Workspace assignment IDs per group |
| `group_entitlements` | Entitlements per group (e.g. workspace_consume) |

## Genie Space – Permissions

See **[GENIE_SPACE_PERMISSIONS.md](GENIE_SPACE_PERMISSIONS.md)** for the full checklist of what must be in place for users to use a Genie Space.

| Requirement | Implemented |
|-------------|-------------|
| **Identity** (groups, workspace assignment) | Terraform: `main.tf` |
| **Consumer (One UI only)** | Terraform: `main.tf` (entitlements) |
| **Compute – CAN USE on warehouse** | Terraform: `warehouse_grants.tf` (set `genie_default_warehouse_id`) |
| **Data – SELECT, USE CATALOG, USE SCHEMA** | Terraform: `uc_grants.tf`; ABAC is configured separately in SQL |
| **Genie Space ACLs (CAN VIEW, CAN RUN)** | Script/API: `scripts/set_genie_space_acls.sh`; migrate to Terraform when the provider supports Genie Space ACLs |

### Variables for Genie

- **`genie_default_warehouse_id`** (optional, default `""`): SQL warehouse ID used by the Genie Space. When set, the five groups receive CAN USE via `warehouse_grants.tf`. Required for consumers to run queries in Genie.
- **`uc_catalog_name`** (optional, default `"fincat"`): Unity Catalog catalog name for Genie data access grants.
- **`uc_schema_name`** (optional, default `"finance"`): Schema name used with `uc_catalog_name` (for reference; catalog-level grants in `uc_grants.tf` cover the catalog).

After creating the Genie Space, run `scripts/set_genie_space_acls.sh` (or follow the runbook in GENIE_SPACE_PERMISSIONS.md) to grant the five groups CAN VIEW and CAN RUN on the space.

## Tag Policies Note

If your Databricks Terraform provider does not support `databricks_tag_policy` (or the resource fails), create the same tag policies via the REST API or run the reduced `abac/finance/2.CreateFinanceTagPolicies.py` script (trimmed to the 5 tag keys: `aml_clearance`, `pii_level`, `pci_clearance`, `customer_region`, `data_residency`).

## Authentication

Requires a **Databricks service principal** with Account Admin (for groups, workspace assignment, group members) and workspace admin (for entitlements and tag policies).
