# Unity Catalog ABAC — Generic Terraform Module

A data-driven Terraform module for **Attribute-Based Access Control (ABAC)** on Databricks Unity Catalog. All groups, tag policies, tag assignments, and FGAC policies are defined in `terraform.tfvars` — no `.tf` files need editing.

## What This Quickstart Automates

This quickstart is designed to help data teams onboard business stakeholders to **Genie in Databricks One** quickly and securely (PoLP), with repeatable automation for:

- **Business groups**: Create account-level groups (access tiers) and optionally manage group membership.
- **Workspace onboarding**: Assign those groups to a target workspace so they can authenticate and use Genie.
- **Databricks One entitlement**: Enable consumer access so business users can use the **Databricks One UI** (without requiring full workspace UI access).
- **Data access grants**: Apply the minimum required Unity Catalog privileges (e.g., `USE_CATALOG`, `USE_SCHEMA`, `SELECT`) for the data exposed through Genie.
- **ABAC governance**: Create governed tag policies, tag assignments on tables/columns, and fine-grained FGAC policies (column masks + row filters).
- **Genie Space ACLs (optional)**: Grant `CAN_RUN` on an existing Genie Space to the configured business groups.
- **SQL warehouse (optional)**: Create (or reference) a serverless SQL warehouse for Genie.

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      YOU PROVIDE (one-time setup)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────┐    ┌──────────────────────┐   │
│  │  auth.auto.tfvars                    │    │  ddl/*.sql           │   │
│  │  (credentials — write once)          │    │  (your table DDLs)   │   │
│  │                                      │    │                      │   │
│  │  databricks_account_id    = "..."    │    │  CREATE TABLE ...    │   │
│  │  databricks_client_id     = "..."    │    │  CREATE TABLE ...    │   │
│  │  databricks_client_secret = "..."    │    │                      │   │
│  │  databricks_workspace_host = "..."   │    │                      │   │
│  │  uc_catalog_name = "my_catalog"      │    │                      │   │
│  │  uc_schema_name  = "my_schema"       │    │                      │   │
│  └──────────────────┬───────────────────┘    └──────────┬───────────┘   │
│                     │                                   │               │
└─────────────────────┼───────────────────────────────────┼───────────────┘
                      │                                   │
                      │  ┌────────────────────────────────┘
                      │  │
                      ▼  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       generate_abac.py                                  │
│             (or manually via ABAC_PROMPT.md + AI chat)                  │
│                                                                         │
│  Reads auth.auto.tfvars for SDK auth + catalog/schema                   │
│  Reads ddl/*.sql  +  ABAC_PROMPT.md  ──▶  LLM (Claude Sonnet)           │
│                                                                         │
│  Providers: Databricks FMAPI (default) | Anthropic | OpenAI             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     ▼                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       generated/  (output folder)                       │
│                                                                         │
│  ┌──────────────────────────┐  ┌────────────────────────────────────┐   │
│  │  masking_functions.sql   │  │  terraform.tfvars                  │   │
│  │                          │  │  (ABAC config — no credentials)    │   │
│  │  SQL UDFs:               │  │                                    │   │
│  │  • mask_pii_partial()    │  │  groups          ─ access tiers    │   │
│  │  • mask_ssn()            │  │  tag_policies    ─ sensitivity tags│   │
│  │  • mask_email()          │  │  tag_assignments ─ tags on columns │   │
│  │  • filter_by_region()    │  │  fgac_policies   ─ masks & filters │   │
│  │  • ...                   │  │  group_members   ─ user mappings   │   │
│  └────────────┬─────────────┘  └──────────────────┬─────────────────┘   │
└───────────────┼────────────────────────────────────┼────────────────────┘
                │                                    │
                ▼                                    ▼
┌──────────────────────────────┐   ┌──────────────────────────────────────┐
│  Run in Databricks SQL       │   │  validate_abac.py (auto)             │
│  editor to create UDFs       │   │  ✓ structure  ✓ cross-refs  ✓ names  │
│  in your catalog.schema      │   └──────────────────┬───────────────────┘
└──────────────────────────────┘                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  terraform apply                                                        │
│  Loads: auth.auto.tfvars (credentials) + terraform.tfvars (ABAC)        │
│                                                                         │
│  Creates in Databricks:                                                 │
│  ┌──────────────────┐  ┌─────────────────┐  ┌───────────────────────┐   │
│  │  Account Groups  │  │  Tag Policies   │  │  Tag Assignments      │   │
│  │  Nurse           │  │  pii_level      │  │  Patients.SSN         │   │
│  │  Physician       │  │  phi_level      │  │    → pii_level=Full   │   │
│  │  Billing_Clerk   │  │  fin_access     │  │  Billing.TotalAmount  │   │
│  │  Admin           │  │  region         │  │    → fin_access=Full  │   │
│  └──────────────────┘  └─────────────────┘  └───────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  FGAC Policies (Column Masks + Row Filters)                      │   │
│  │                                                                  │   │
│  │  "Nurse sees SSN as ***-**-1234"     ──▶ mask_ssn()              │   │
│  │  "Billing_Clerk sees notes as [REDACTED]" ──▶ mask_redact()      │   │
│  │  "US_East_Staff sees only US_EAST rows"   ──▶ filter_region()    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────┐  ┌────────────────────────────────────────┐   │
│  │  UC Grants           │  │  Workspace Assignments + Entitlements  │   │
│  │  USE_CATALOG         │  │  Groups added to workspace             │   │
│  │  USE_SCHEMA          │  │  Consumer access enabled               │   │
│  │  SELECT              │  │                                        │   │
│  └──────────────────────┘  └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Three-Tier Workflow

| Tier | Who | Workflow |
|------|-----|----------|
| **1. Quick Start** | New users wanting a working demo | Copy `examples/finance/finance.tfvars.example`, run the finance SQL scripts, `terraform apply` |
| **2. Pick and Mix** | Users with their own tables | Pick masking UDFs from `masking_functions_library.sql`, fill in `terraform.tfvars.example` |
| **3. AI-Assisted** | Users who need help designing ABAC | Paste table DDL into `ABAC_PROMPT.md`, let AI generate the masking SQL + tfvars. See [`examples/healthcare/`](examples/healthcare/) for a full worked example |

## First-Time Setup (all tiers)

```bash
# Option A: use make (copies example files, creates directories)
make setup

# Option B: manual
cp auth.auto.tfvars.example auth.auto.tfvars
# Edit auth.auto.tfvars — fill in all fields
# Terraform auto-loads *.auto.tfvars so these are always available.
```

## Quick Start (Tier 1 — Finance Demo)

```bash
# 1. Copy the finance ABAC config
cp examples/finance/finance.tfvars.example terraform.tfvars

# 2. Create the demo tables and masking UDFs in your workspace SQL editor.
#    Both files are in the examples/finance/ folder:
#
#    a) Create masking & filter functions (run first):
#       examples/finance/0.1finance_abac_functions.sql
#
#    b) Create finance demo tables with sample data:
#       examples/finance/0.2finance_database_schema.sql
#
#    IMPORTANT: Edit the USE CATALOG / USE SCHEMA lines at the top of each
#    file to match your uc_catalog_name and uc_schema_name before running.

# 3. Apply (loads auth.auto.tfvars + terraform.tfvars automatically)
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

### Option A — Automated (recommended)

```bash
# 1. Add your DDL files to the ddl/ folder
#    Single file with all tables, or one file per table — both work
cp my_tables.sql ddl/
#    Or use the healthcare example: cp examples/healthcare/ddl/*.sql ddl/

# 2. Install dependencies (one-time)
pip install databricks-sdk python-hcl2

# 3. Generate — reads catalog/schema from auth.auto.tfvars automatically
python generate_abac.py

# 4. Review, copy generated config to module root
cp generated/terraform.tfvars terraform.tfvars
# Run generated/masking_functions.sql in your Databricks SQL editor

# 5. Apply
terraform init && terraform plan && terraform apply
```

You can also override catalog/schema or use different providers:

```bash
# Override catalog/schema
python generate_abac.py --catalog other_catalog --schema other_schema

# Anthropic (direct API)
pip install anthropic
export ANTHROPIC_API_KEY='sk-ant-...'
python generate_abac.py --provider anthropic

# OpenAI
pip install openai
export OPENAI_API_KEY='sk-...'
python generate_abac.py --provider openai

# Custom model
python generate_abac.py --provider databricks --model databricks-meta-llama-3-3-70b-instruct

# Dry run — print the prompt without calling the LLM
python generate_abac.py --dry-run

# Retry up to 5 times on transient LLM failures (default: 3)
python generate_abac.py --max-retries 5
```

The generator automatically runs `validate_abac.py` on the output and substitutes `{catalog}` / `{schema}` placeholders in the generated SQL with values from `auth.auto.tfvars`. If validation fails, fix the errors and re-run.

### Option B — Manual

1. Open `ABAC_PROMPT.md` and copy the prompt into ChatGPT, Claude, or Cursor
2. Paste your `DESCRIBE TABLE` output where indicated
3. The AI generates `masking_functions.sql` and `terraform.tfvars`
4. **Validate** before applying:
   ```bash
   pip install python-hcl2
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

### Authentication (in `auth.auto.tfvars`)

| Variable | Description |
|----------|-------------|
| `databricks_account_id` | Databricks account ID |
| `databricks_client_id` | Service principal client ID |
| `databricks_client_secret` | Service principal client secret |
| `databricks_workspace_id` | Target workspace ID |
| `databricks_workspace_host` | Workspace URL |
| `uc_catalog_name` | Catalog for FGAC policies and UDFs |
| `uc_schema_name` | Schema where masking UDFs are deployed |

### ABAC Config (in `terraform.tfvars`)

| Variable | Description |
|----------|-------------|
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
  auth.auto.tfvars.example       # Credentials + catalog/schema (copy to auth.auto.tfvars)
  terraform.tfvars.example       # ABAC config skeleton (groups, tags, policies)
  masking_functions_library.sql  # Reusable masking UDF library
  ABAC_PROMPT.md                 # AI prompt template for Tier 3
  generate_abac.py               # Automated Tier 3 generator (multi-provider LLM)
  validate_abac.py               # Validation tool for AI-generated configs
  Makefile                       # Workflow shortcuts (make setup/generate/validate/plan/apply)
  test.sh                        # End-to-end validation of example configs
  ddl/                           # INPUT:  Place your table DDL .sql files here
  generated/                     # OUTPUT: AI-generated masking SQL + tfvars go here
  scripts/
    genie_space.sh               # Create Genie Space and set ACLs
    import_existing.sh           # Import pre-existing resources into Terraform state
  examples/
    finance/
      finance.tfvars.example              # Complete finance demo config (Tier 1)
      0.1finance_abac_functions.sql      # Finance masking & filter UDFs
      0.2finance_database_schema.sql     # Finance demo tables + sample data
    healthcare/
      healthcare_walkthrough.md          # End-to-end AI-Assisted walkthrough (Tier 3)
      masking_functions.sql              # Healthcare masking UDFs (example AI output)
      healthcare.tfvars.example          # Healthcare tfvars (example AI output)
      ddl/                               # Healthcare DDL files (copy to ddl/ to use)
        patients.sql                     # Patients table DDL
        encounters.sql                   # Encounters table DDL
        prescriptions.sql                # Prescriptions table DDL
        billing.sql                      # Billing table DDL
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

## Make Targets

A `Makefile` provides shortcuts for common workflows:

| Target | Description |
|--------|-------------|
| `make setup` | Copy example files, create `ddl/` and `generated/` directories |
| `make generate` | Run `generate_abac.py` to produce masking SQL + tfvars |
| `make validate` | Run `validate_abac.py` on `terraform.tfvars` |
| `make plan` | Run `terraform init` + `terraform plan` |
| `make apply` | Run `terraform init` + `terraform apply` |
| `make destroy` | Run `terraform destroy` |
| `make clean` | Remove generated files, Terraform state, and `.terraform/` |

## Importing Existing Resources

If groups, tag policies, or FGAC policies already exist in Databricks, `terraform apply` will fail with "already exists". Use the import script to adopt them into Terraform state:

```bash
./scripts/import_existing.sh              # import all resource types
./scripts/import_existing.sh --dry-run    # preview without importing
./scripts/import_existing.sh --groups-only # import only groups
./scripts/import_existing.sh --tags-only   # import only tag policies
./scripts/import_existing.sh --fgac-only   # import only FGAC policies
```

See [`IMPORT_EXISTING.md`](IMPORT_EXISTING.md) for details.

## Testing

Run `test.sh` to validate all example configs without deploying:

```bash
./test.sh              # validate examples + terraform validate
./test.sh --skip-tf    # skip terraform validate (no init required)
```

The script validates the finance, healthcare, and skeleton examples with `validate_abac.py` and optionally runs `terraform validate` on the HCL.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Could not find principal" | Group not yet synced to workspace | `terraform apply` again (depends_on handles ordering) |
| "User does not have USE SCHEMA" | SP missing catalog/schema access | The module grants MANAGE to the SP automatically |
| "already exists" | Resources created outside Terraform | Use `terraform import` or `scripts/import_existing.sh` |
| "Operation aborted due to concurrent modification" | Tag policy race condition | Re-run with `terraform apply -parallelism=1` to serialize API requests |

## Authentication

Requires a **Databricks service principal** with:
- **Account Admin** for groups, workspace assignments, and group members
- **Workspace Admin** for entitlements, tag policies, and FGAC policies
