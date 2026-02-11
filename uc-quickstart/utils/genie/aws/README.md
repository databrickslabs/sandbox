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
demo_user_junior_us_ids = ["12345678", "11111111"]   # -> Junior_Analyst, US_Region_Staff
demo_user_senior_eu_ids = ["87654321", "22222222"]   # -> Senior_Analyst, EU_Region_Staff
```

### 2. Apply

```bash
terraform init
terraform plan
terraform apply
```

**If resources already exist**, Terraform will fail with "already exists". To have Terraform **overwrite** them: copy `import_ids.env.example` to `import_ids.env`, fill in the warehouse and group IDs (see [IMPORT_EXISTING.md](IMPORT_EXISTING.md)), then run **`./scripts/import_existing.sh`**. After that, `terraform apply` will manage and update config to match the .tf files.

If you see **"Principal does not exist"** or **"Could not find principal with name …"** on warehouse or catalog grants, the workspace may not have synced the new groups yet. Run **`terraform apply`** again. If you see **"Operation aborted due to concurrent modification"** on a tag policy, run **`terraform apply`** again (tag policies are created in sequence to reduce this).

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
| `genie_warehouse_id` | SQL warehouse ID for Genie (created or existing); pass to `scripts/genie_space.sh create` |
| `genie_space_acls_applied` | Whether Genie Space ACLs were applied via Terraform |
| `genie_space_acls_groups` | Groups granted CAN_RUN on the Genie Space (when ACLs applied) |

## Genie Space – Permissions

See **[GENIE_SPACE_PERMISSIONS.md](GENIE_SPACE_PERMISSIONS.md)** for the full checklist of what must be in place for users to use a Genie Space.

| Requirement | Implemented |
|-------------|-------------|
| **Identity** (groups, workspace assignment) | Terraform: `main.tf` |
| **Consumer (One UI only)** | Terraform: `main.tf` (entitlements) |
| **Compute – warehouse for Genie** | Terraform: `genie_warehouse.tf` (serverless warehouse). Genie embeds on the warehouse; end users do not need explicit CAN_USE. |
| **Data – SELECT, USE CATALOG, USE SCHEMA** | Terraform: `uc_grants.tf`; ABAC is configured separately in SQL |
| **Genie Space** (create + ACLs) | Script: `scripts/genie_space.sh create` (creates space with all finance tables, then sets CAN_RUN for five groups) |

### Genie flow (recommended)

1. **Terraform apply** creates a **serverless SQL warehouse** (or use an existing one via `genie_use_existing_warehouse_id`). Genie embeds on this warehouse; no explicit warehouse grants for end users are needed.
2. After **terraform apply**, run **`scripts/genie_space.sh create`** with the warehouse ID to create the Genie Space with **all tables in the finance schema** and set ACLs for the five groups:
   ```bash
   export GENIE_WAREHOUSE_ID=$(terraform output -raw genie_warehouse_id)
   ./scripts/genie_space.sh create
   ```
   Or pass workspace URL, token, title, and warehouse_id as arguments. To set ACLs on an existing space: `./scripts/genie_space.sh set-acls [workspace_url] [token] [space_id]`.

### Genie Space ACLs via Terraform (optional)

You can also set Genie Space ACLs automatically via Terraform by setting:

```hcl
genie_space_id = "01234567890abcdef"   # From genie_space.sh create output
```

When set, Terraform runs `scripts/genie_space.sh set-acls` using the **same Service Principal OAuth credentials** (`databricks_client_id`/`databricks_client_secret`) to grant CAN_RUN to the five finance groups. No separate PAT is required.

### Variables for Genie

- **`genie_warehouse_name`** (optional, default `"Genie Finance Warehouse"`): Name of the serverless SQL warehouse created when not using an existing one.
- **`genie_use_existing_warehouse_id`** (optional, default `""`): When set, do not create a warehouse; use this ID for `genie_space.sh create`.
- **`genie_default_warehouse_id`** (deprecated): Use `genie_use_existing_warehouse_id` instead. When set, used as the Genie warehouse ID.
- **`uc_catalog_name`** (optional, default `"fincat"`): Unity Catalog catalog name for Genie data access grants.
- **`uc_schema_name`** (optional, default `"finance"`): Schema name used with `uc_catalog_name` (for reference; catalog-level grants in `uc_grants.tf` cover the catalog).
- **`genie_space_id`** (optional, default `""`): Genie Space ID for setting ACLs via Terraform. When set, Terraform runs `set-acls` using the same SP credentials.

If the workspace does not have serverless SQL enabled, the warehouse create may fail; enable it in the workspace or use an existing warehouse ID.

## Tag Policies Note

If your Databricks Terraform provider does not support `databricks_tag_policy` (or the resource fails), create the same tag policies via the REST API or run the reduced `abac/finance/2.CreateFinanceTagPolicies.py` script (trimmed to the 5 tag keys: `aml_clearance`, `pii_level`, `pci_clearance`, `customer_region`, `data_residency`).

## Authentication

Requires a **Databricks service principal** with Account Admin (for groups, workspace assignment, group members) and workspace admin (for entitlements and tag policies).
