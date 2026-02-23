# Unity Catalog ABAC — Generic Terraform Module

A data-driven Terraform module for **Attribute-Based Access Control (ABAC)** on Databricks Unity Catalog. All groups, tag policies, tag assignments, and FGAC policies are defined in `terraform.tfvars` — no `.tf` files need editing.

## Three-Tier Workflow

| Tier | Who | Workflow |
|------|-----|----------|
| **1. Quick Start** | New users wanting a working demo | Copy `examples/finance/finance.tfvars`, run the finance SQL scripts, `terraform apply` |
| **2. Pick and Mix** | Users with their own tables | Pick masking UDFs from `masking_functions_library.sql`, fill in `terraform.tfvars.example` |
| **3. AI-Assisted** | Users who need help designing ABAC | Paste table DDL into `ABAC_PROMPT.md`, let AI generate the masking SQL + tfvars. See [`examples/healthcare/`](examples/healthcare/) for a full worked example |

## Quick Start (Tier 1 — Finance Demo)

New users wanting a working demo should use the included finance SQL scripts to create sample tables and masking functions, then apply the pre-built finance tfvars.

```bash
# 1. Copy the finance example
cp examples/finance/finance.tfvars terraform.tfvars

# 2. Edit terraform.tfvars — fill in authentication + replace MY_CATALOG with your catalog

# 3. Create the demo tables and masking UDFs in your workspace SQL editor.
#    Both files are included in the examples/finance/ folder for convenience:
#
#    a) Create masking & filter functions (run first):
#       examples/finance/0.1finance_abac_functions.sql
#
#    b) Create finance demo tables with sample data:
#       examples/finance/0.2finance_database_schema.sql
#
#    IMPORTANT: Edit the USE CATALOG / USE SCHEMA lines at the top of each
#    file to match your uc_catalog_name and uc_schema_name before running.

# 4. Apply
terraform init
terraform plan
terraform apply
```

## Bring Your Own Tables (Tier 2)

```bash
# 1. Start from the skeleton
cp terraform.tfvars.example terraform.tfvars

# 2. Pick masking functions from masking_functions_library.sql
#    Find-replace {catalog}.{schema} with your catalog and schema
#    Run only the functions you need in your workspace

# 3. Fill in terraform.tfvars with your groups, tags, and policies

# 4. Apply
terraform init && terraform apply
```

## AI-Assisted (Tier 3)

1. Open `ABAC_PROMPT.md` and copy the prompt into ChatGPT, Claude, or Cursor
2. Paste your `DESCRIBE TABLE` output where indicated
3. The AI generates `masking_functions.sql` and `terraform.tfvars`
4. **Validate** before applying:
   ```bash
   pip install python-hcl2     # one-time
   python validate_abac.py terraform.tfvars masking_functions.sql
   ```
5. Fix any `[FAIL]` errors reported, then run the SQL and `terraform apply`

> **Full worked example:** See [`examples/healthcare/`](examples/healthcare/) for an end-to-end healthcare scenario — includes a walkthrough, example masking functions SQL, and a ready-to-use tfvars file.

## What This Module Creates

| Resource | Terraform File | Description |
|----------|---------------|-------------|
| Account-level groups | `main.tf` | One `databricks_group` per entry in `var.groups` |
| Workspace assignments | `main.tf` | Assigns groups to the workspace with USER permission |
| Consumer entitlements | `main.tf` | `workspace_consume = true` for One UI access |
| Tag policies | `tag_policies.tf` | Governed tag keys + allowed values from `var.tag_policies` |
| Tag assignments | `entity_tag_assignments.tf` | Tags on tables/columns from `var.tag_assignments` |
| FGAC policies | `fgac_policies.tf` | Column masks and row filters from `var.fgac_policies` |
| Group members | `group_members.tf` | User-to-group mappings from `var.group_members` |
| UC grants | `uc_grants.tf` | `USE_CATALOG`, `USE_SCHEMA`, `SELECT` for each group |
| SP manage grant | `uc_grants.tf` | `MANAGE` privilege for the Terraform SP to create policies |
| SQL warehouse | `genie_warehouse.tf` | Optional serverless warehouse for Genie |
| Genie ACLs | `genie_space_acls.tf` | Optional CAN_RUN on a Genie Space for all groups |

## Variables Reference

### Required

| Variable | Description |
|----------|-------------|
| `databricks_account_id` | Databricks account ID |
| `databricks_client_id` | Service principal client ID |
| `databricks_client_secret` | Service principal client secret |
| `databricks_workspace_id` | Target workspace ID |
| `databricks_workspace_host` | Workspace URL |
| `uc_catalog_name` | Catalog for FGAC policies and UDFs |
| `uc_schema_name` | Schema where masking UDFs are deployed |
| `groups` | Map of group name to config |

### Data-Driven ABAC

| Variable | Type | Description |
|----------|------|-------------|
| `tag_policies` | list(object) | Tag keys + allowed values |
| `tag_assignments` | list(object) | Tag-to-entity bindings |
| `fgac_policies` | list(object) | Column masks and row filters |
| `group_members` | map(list) | User IDs to add to each group |

### Optional — Genie Space

| Variable | Default | Description |
|----------|---------|-------------|
| `genie_warehouse_name` | `"Genie ABAC Warehouse"` | Name for auto-created warehouse |
| `genie_use_existing_warehouse_id` | `""` | Use an existing warehouse instead |
| `genie_space_id` | `""` | Set to apply CAN_RUN ACLs |

## Outputs

| Output | Description |
|--------|-------------|
| `group_ids` | Map of group names to group IDs |
| `group_names` | List of all created group names |
| `workspace_assignments` | Workspace assignment IDs per group |
| `group_entitlements` | Entitlements per group |
| `genie_warehouse_id` | SQL warehouse ID (created or existing) |
| `genie_space_acls_applied` | Whether Genie Space ACLs were applied |
| `genie_space_acls_groups` | Groups granted CAN_RUN on the Genie Space |

## File Layout

```
aws/
  main.tf                        # Groups, workspace assignments, entitlements
  variables.tf                   # All input variables
  tag_policies.tf                # Tag policy resources (for_each)
  entity_tag_assignments.tf      # Tag-to-entity bindings (for_each)
  fgac_policies.tf               # FGAC column masks + row filters (for_each)
  group_members.tf               # User-to-group memberships (for_each)
  uc_grants.tf                   # UC data access grants
  outputs.tf                     # Module outputs
  provider.tf                    # Databricks provider config
  genie_warehouse.tf             # Optional serverless warehouse
  genie_space_acls.tf            # Optional Genie Space ACLs
  masking_functions_library.sql  # Reusable masking UDF library
  ABAC_PROMPT.md                 # AI prompt template for Tier 3
  validate_abac.py               # Validation tool for AI-generated configs
  terraform.tfvars.example       # Annotated variable skeleton
  examples/
    finance/
      finance.tfvars                     # Complete finance demo config (Tier 1)
      0.1finance_abac_functions.sql      # Finance masking & filter UDFs
      0.2finance_database_schema.sql     # Finance demo tables + sample data
    healthcare/
      healthcare_walkthrough.md          # End-to-end AI-Assisted walkthrough (Tier 3)
      masking_functions.sql              # Healthcare masking UDFs (example AI output)
      healthcare.tfvars                  # Healthcare tfvars (example AI output)
```

## Validation

Run `validate_abac.py` to catch configuration errors **before** `terraform apply`:

```bash
pip install python-hcl2                                     # one-time dependency
python validate_abac.py terraform.tfvars                    # tfvars only
python validate_abac.py terraform.tfvars masking_funcs.sql  # tfvars + SQL cross-check
```

The validator checks:
- **Structure**: required variables, correct types, valid `entity_type` / `policy_type` values
- **Cross-references**: groups in `fgac_policies` exist in `groups`, tag keys/values match `tag_policies`, `group_members` keys match `groups`
- **Naming**: `entity_name` / `function_name` are relative (no catalog.schema prefix)
- **SQL functions**: every `function_name` in `fgac_policies` has a matching `CREATE FUNCTION` in the SQL file
- **Completeness**: warns about unused SQL functions and empty auth fields

## Prerequisites

- Databricks **service principal** with Account Admin (groups, workspace assignment) and workspace admin (entitlements, tag policies, FGAC)
- Masking UDFs deployed in `uc_catalog_name.uc_schema_name` before applying FGAC policies
- Tables must exist before tag assignments can be applied

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Could not find principal" | Group not yet synced to workspace | `terraform apply` again (depends_on handles ordering) |
| "User does not have USE SCHEMA" | SP missing catalog/schema access | The module grants MANAGE to the SP automatically |
| "already exists" | Resources created outside Terraform | Use `terraform import` or `scripts/import_existing.sh` |
| "Operation aborted due to concurrent modification" | Tag policy race condition | `terraform apply` again |

## Authentication

Requires a **Databricks service principal** with:
- **Account Admin** for groups, workspace assignments, and group members
- **Workspace Admin** for entitlements, tag policies, and FGAC policies
