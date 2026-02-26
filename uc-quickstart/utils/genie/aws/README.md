# OneReady — Genie Onboarding Quickstart

Get your workspace **OneReady** for Genie in Databricks One. A data-driven Terraform quickstart that automates business-user onboarding — groups, entitlements, data access, ABAC governance, and Genie Space ACLs — all defined in `terraform.tfvars`, no `.tf` files need editing.

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
│  │  uc_tables = ["catalog.schema.tbl"]  │    │                      │   │
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
│  └────────────┬─────────────┘  └───────────────────┬────────────────┘   │
└───────────────┼────────────────────────────────────┼────────────────────┘
                │                                    │
                ▼                                    ▼
┌──────────────────────────────┐   ┌──────────────────────────────────────┐
│  masking_functions.sql       │   │  validate_abac.py (auto)             │
│  (copied to module root)     │   │  ✓ structure  ✓ cross-refs  ✓ names  │
│                              │   └──────────────────┬───────────────────┘
│  Auto-deployed by Terraform  │                      │
│  when sql_warehouse_id is    │                      │
│  set, or run manually.       │                      │
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

## Recommended Workflow (AI‑Assisted)

Use the AI‑Assisted workflow to generate a strong first draft of masking functions and ABAC policies, then iterate quickly before applying.

**Generate → Review/Tune → Apply**

## First-Time Setup

```bash
# One-time: set up your credentials and tables
cp auth.auto.tfvars.example auth.auto.tfvars
# Edit auth.auto.tfvars — fill in credentials and uc_tables:
#   uc_tables = ["prod.sales.customers", "prod.sales.orders", "prod.finance.*"]
# Each table's catalog/schema comes from its fully-qualified name.
# Each policy in the generated terraform.tfvars specifies its own catalog/function_catalog/function_schema.
```

## AI‑Assisted (Recommended)

```bash
# 1. Generate (dependencies are auto-installed on first run)
python generate_abac.py

# 2. Review + tune (see generated/TUNING.md)
#    - Edit generated/terraform.tfvars and generated/masking_functions.sql as needed
#    - Validate after each change:
make validate-generated

# 3. Apply (validates, promotes generated/ to root, runs terraform apply)
make apply
```

Or skip tuning and apply directly:

```bash
python generate_abac.py --promote   # generate + validate + copy to root
make apply                          # terraform apply
```

You can also override tables via CLI, use local DDL files, or change providers:

```bash
# Override tables from CLI (takes precedence over uc_tables in config)
python generate_abac.py --tables "prod.sales.*" "prod.finance.*"

# Use local DDL files (legacy — requires --catalog and --schema)
cp my_tables.sql ddl/
python generate_abac.py --catalog my_catalog --schema my_schema

# Dry run — print the prompt without calling the LLM
python generate_abac.py --dry-run

# Retry on transient LLM failures (default: 3)
python generate_abac.py --max-retries 5
```

### Review & Tune (Before Apply)

Tuning is expected. Start with the checklist in `generated/TUNING.md`, then iterate until validation passes and stakeholders are comfortable with the policy outcomes.

Quick checklist:
- **Groups and personas**: Do the group names represent the real business roles you need?
- **Sensitive columns**: Are the right columns tagged (PII/PHI/financial/etc.)?
- **Masking behavior**: Are you using the right mask type (partial, redact, hash) per sensitivity and use case?
- **Row filters and exceptions**: Are filters too broad/strict? Are “break-glass” or admin exceptions intentional and minimal?
- **Validate after each change**: Run `make validate-generated` to catch mismatches early. You can run this as many times as needed while tuning.

## Appendix: Alternatives & Tuning Toolkit

If you want a faster demo or prefer manual control, use these as building blocks:

- **Tier 1 (Demo / confidence builder)**: Finance example config + SQL in [`examples/finance/`](examples/finance/).  
  Start with `examples/finance/finance.tfvars.example` and the `0.1*` / `0.2*` SQL scripts.
- **Tier 2 (Manual tuning)**: Use `terraform.tfvars.example` + pick masking functions from `masking_functions_library.sql`.
- **Manual prompt**: If you prefer chatting with an AI directly, use `ABAC_PROMPT.md` and validate the result with `validate_abac.py`.
- **Worked example**: See [`examples/healthcare/`](examples/healthcare/) for an end-to-end AI‑Assisted walkthrough.

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
| Masking functions | `masking_functions.tf` | Optional auto-deployment of UDFs via Statement Execution API (when `sql_warehouse_id` is set) |
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
| `uc_tables` | Tables to generate ABAC for (only used by `generate_abac.py`, not Terraform) |
| `sql_warehouse_id` | SQL warehouse ID for auto-deploying masking functions during `terraform apply`. When empty (default), deploy SQL manually. |

### ABAC Config (in `terraform.tfvars` — auto-generated)

| Variable | Description |
|----------|-------------|
| `groups` | Map of group name to config |

### Data-Driven ABAC

| Variable | Type | Description |
|----------|------|-------------|
| `tag_policies` | list(object) | Tag keys + allowed values |
| `tag_assignments` | list(object) | Tag-to-entity bindings (fully-qualified entity names: `catalog.schema.table`) |
| `fgac_policies` | list(object) | Column masks and row filters (`catalog` per policy for multi-catalog scoping) |
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
  masking_functions.tf            # Optional auto-deploy of masking UDFs
  genie_warehouse.tf             # Optional serverless warehouse
  genie_space_acls.tf            # Optional Genie Space ACLs
  deploy_masking_functions.py    # Helper: executes SQL via Statement Execution API
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
- **Naming**: `entity_name` must be fully qualified (`catalog.schema.table`), `function_name` is relative (no catalog.schema prefix)
- **SQL functions**: every `function_name` in `fgac_policies` has a matching `CREATE FUNCTION` in the SQL file
- **Completeness**: warns about unused SQL functions and empty auth fields

## Prerequisites

- Databricks **service principal** with Account Admin (groups, workspace assignment) and workspace admin (entitlements, tag policies, FGAC)
- Masking UDFs deployed in each policy's `function_catalog.function_schema` before applying FGAC policies (auto-deployed when `sql_warehouse_id` is set, or run the SQL manually)
- Tables must exist before tag assignments can be applied

## Make Targets

A `Makefile` provides shortcuts for common workflows:

| Target | Description |
|--------|-------------|
| `make setup` | Copy example files, create `ddl/` and `generated/` directories |
| `make generate` | Run `generate_abac.py` to produce masking SQL + tfvars |
| `make validate-generated` | Validate `generated/` files before copying to root |
| `make validate` | Validate root `terraform.tfvars` + `masking_functions.sql` |
| `make promote` | Validate `generated/` and copy to module root |
| `make plan` | Run `terraform init` + `terraform plan` |
| `make apply` | Validate, promote `generated/` to root, then `terraform apply -parallelism=1` |
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

## Roadmap

- [ ] **Multi Genie Space support** — Configure and apply ACLs for multiple Genie Spaces in a single apply (currently supports one `genie_space_id`)
- [ ] **Multi data steward / user support** — Allow multiple data steward personas with independent policy scoping and approval workflows, not just a single SP-driven config
- [ ] **AI-assisted tuning and troubleshooting** — Use the LLM to interactively refine generated configs, diagnose policy mismatches, suggest fixes for failed applies, and validate masking behavior against sample data
- [ ] **Import existing policies** — Auto-detect and import pre-existing FGAC policies, tag policies, and tag assignments into Terraform state so `terraform apply` doesn't conflict with manually created resources
