# GenieRails

Put Genie onboarding on rails — with built-in guardrails. An AI-powered Terraform quickstart that gets business users into Genie quickly and safely — ABAC governance, masking functions, and a fully configured Genie Space with AI-generated sample questions, instructions, benchmarks, SQL filters, measures, and join specs — all from three config files, no `.tf` editing required.

## What This Quickstart Automates

- **AI-generated ABAC config** — Point at your tables, and an LLM analyzes column sensitivity to generate groups, tag policies, tag assignments, FGAC policies, and masking functions automatically.
- **Business groups** — Create account-level groups (access tiers) and optionally manage group membership.
- **Workspace onboarding** — Assign groups to a target workspace with Databricks One consumer entitlements.
- **Data access grants** — Apply minimum Unity Catalog privileges (`USE_CATALOG`, `USE_SCHEMA`, `SELECT`) for data exposed through Genie.
- **ABAC governance** — Create governed tag policies, tag assignments on tables/columns, and FGAC policies (column masks + row filters).
- **Masking functions** — Auto-deploy SQL UDFs to enforce column-level data masking (e.g., mask SSN, redact PII, hash emails).
- **Genie Space** — Auto-create a new Genie Space from your tables, or bring an existing one. New spaces include AI-generated config:
  - **Sample questions** — Conversation starters tailored to your data domain
  - **Instructions** — Domain-specific LLM guidance with business defaults (e.g., "customer" means active by default)
  - **Benchmarks** — Unambiguous ground-truth question + SQL pairs for evaluating Genie accuracy
  - **SQL filters** — Default WHERE clauses (e.g., active customers, completed transactions) that guide Genie's SQL generation
  - **SQL measures & expressions** — Standard metrics (total revenue, avg risk score) and computed dimensions (transaction year)
  - **Join specs** — Table relationships with join conditions so Genie knows how to combine tables
  - **Title & description** — Contextual naming based on your tables and domain
  - For existing spaces, set `genie_space_id` in `env.auto.tfvars` to apply `CAN_RUN` ACLs for all configured business groups
- **SQL warehouse** — Auto-create a serverless warehouse or reuse an existing one.

## How It Works

```
┌───────────────────────────────────────────────────────────────────────┐
│                    YOU PROVIDE (one-time setup)                       │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────┐ ┌───────────────────────────────┐  │
│  │  auth.auto.tfvars             │ │  env.auto.tfvars              │  │
│  │  (secrets — gitignored)       │ │  (environment — checked in)   │  │
│  │                               │ │                               │  │
│  │  databricks_account_id = "..."│ │  uc_tables = ["cat.sch.*"]    │  │
│  │  databricks_client_id  = "..."│ │  sql_warehouse_id = ""        │  │
│  │  databricks_client_secret     │ │  genie_space_id = ""          │  │
│  │  databricks_workspace_host    │ │                               │  │
│  └───────────────┬───────────────┘ └───────────────┬───────────────┘  │
│                  └────────────────┬────────────────┘                  │
└────────────────────────────────────┼──────────────────────────────────┘
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────┐
│                make generate  (generate_abac.py)                      │
│                                                                       │
│  1. Fetches DDLs from Unity Catalog (via Databricks SDK)              │
│  2. Reads ABAC_PROMPT.md + DDLs  ──▶  LLM (Claude Sonnet)             │
│                                                                       │
│  Providers: Databricks FMAPI (default) | Anthropic | OpenAI           │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     generated/  (output folder)                       │
│                                                                       │
│  ┌─────────────────────────┐  ┌───────────────────────────────────┐   │
│  │  masking_functions.sql  │  │  abac.auto.tfvars                 │   │
│  │                         │  │  (ABAC + Genie — no credentials)  │   │
│  │  SQL UDFs:              │  │                                   │   │
│  │  • mask_pii_partial()   │  │  groups        ─ access tiers     │   │
│  │  • mask_ssn()           │  │  tag_policies  ─ sensitivity tags │   │
│  │  • mask_email()         │  │  tag_assignments ─ tags on cols   │   │
│  │  • filter_by_region()   │  │  fgac_policies ─ masks & filters  │   │
│  │  • ...                  │  │  genie_space_title / description  │   │
│  │                         │  │  genie_sample_questions (5–10)    │   │
│  │                         │  │  genie_instructions               │   │
│  │                         │  │  genie_benchmarks (3–5 w/ SQL)    │   │
│  │                         │  │  genie_sql_filters / measures     │   │
│  │                         │  │  genie_sql_expressions            │   │
│  │                         │  │  genie_join_specs                 │   │
│  └────────────┬────────────┘  └─────────────────┬─────────────────┘   │
└───────────────┼─────────────────────────────────┼─────────────────────┘
                │             ▲  TUNE & VALIDATE  │
                │             │  make validate-generated
                │             │  (repeat until PASS)
                ▼                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  make apply  (validate → promote → terraform apply)                   │
│  Loads: auth.auto.tfvars + env.auto.tfvars + abac.auto.tfvars         │
│                                                                       │
│  Creates in Databricks:                                               │
│  ┌────────────────┐  ┌───────────────┐  ┌─────────────────────────┐   │
│  │ Account Groups │  │ Tag Policies  │  │ Tag Assignments         │   │
│  │ Analyst        │  │ pii_level     │  │ Customers.SSN           │   │
│  │ Manager        │  │ phi_level     │  │   → pii_level=masked    │   │
│  │ Compliance     │  │ data_region   │  │ Billing.Amount          │   │
│  │ Admin          │  │               │  │   → pii_level=masked    │   │
│  └────────────────┘  └───────────────┘  └─────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ FGAC Policies (Column Masks + Row Filters)                     │   │
│  │                                                                │   │
│  │ "Analyst sees SSN as ***-**-1234"      ──▶ mask_ssn()          │   │
│  │ "Manager sees notes as [REDACTED]"     ──▶ mask_redact()       │   │
│  │ "US_Staff sees only US rows"           ──▶ filter_by_region()  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │ Masking Functions  │  │ UC Grants      │  │ Genie Space        │   │
│  │ (auto-deploy UDFs) │  │ USE_CATALOG    │  │ • sample questions │   │
│  │                    │  │ USE_SCHEMA     │  │ • instructions     │   │
│  │ + SQL Warehouse    │  │ SELECT         │  │ • benchmarks       │   │
│  │ (auto-created if   │  │                │  │ • sql filters /    │   │
│  │  needed)           │  │                │  │   measures / joins │   │
│  │                    │  │                │  │ • CAN_RUN ACLs     │   │
│  │                    │  │                │  │   for all groups   │   │
│  └────────────────────┘  └────────────────┘  └────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Tables must exist in Unity Catalog before running `make generate`
- A Databricks **service principal** with the following roles:

| Role | Why it's needed |
| ---- | --------------- |
| **Account Admin** | Create account-level groups, assign groups to workspace, manage group membership |
| **Workspace Admin** | Grant entitlements (`workspace_consume`), create/manage Genie Spaces and permissions |
| **Metastore Admin** | Create governed tag policies (`databricks_tag_policy`), and grant itself `USE_CATALOG`, `USE_SCHEMA`, `EXECUTE`, `MANAGE`, `CREATE_FUNCTION` on any catalog to create FGAC policies, assign tags, and deploy masking functions. Without this role, tag policies must be pre-created manually and catalog-level privileges must be granted by a catalog owner |

## Quick Start

```bash
make setup                  # 1. Creates auth.auto.tfvars + env.auto.tfvars from examples
vi auth.auto.tfvars         #    Fill in credentials (gitignored)
vi env.auto.tfvars          #    Fill in uc_tables, sql_warehouse_id (checked in)

make generate               # 2. Fetches DDLs, calls LLM, outputs to generated/

make validate-generated     # 3. (Optional) Tune generated/ files, validate after each edit
make apply                  #    Validates → promotes → terraform apply
```

That's it. `make apply` creates groups, tags, masking functions, FGAC policies, UC grants, and a Genie Space (with AI-generated sample questions, instructions, benchmarks, SQL filters/measures/expressions, and join specs) — all in one command.

To tear everything down: `make destroy`.

## Configuration

Three files, clear separation of concerns:


| File               | What goes here                                                           | Tracked in git? |
| ------------------ | ------------------------------------------------------------------------ | --------------- |
| `auth.auto.tfvars` | Credentials only (account ID, client ID/secret, workspace)               | No (secrets)    |
| `env.auto.tfvars`  | `uc_tables`, `sql_warehouse_id`, `genie_space_id`                        | **Yes**         |
| `abac.auto.tfvars` | Groups, tag policies, tag assignments, FGAC policies, Genie Space config | **Yes**         |


### `auth.auto.tfvars` — credentials (gitignored)

```hcl
databricks_account_id    = "..."
databricks_client_id     = "..."
databricks_client_secret = "..."
databricks_workspace_id  = "..."
databricks_workspace_host = "https://..."
```

### `env.auto.tfvars` — environment config (checked in)

```hcl
uc_tables = ["catalog.schema.table1", "catalog.schema.*"]  # tables for ABAC + Genie
sql_warehouse_id = ""          # set to reuse existing, or leave empty to auto-create
genie_space_id   = ""          # set for existing space, or leave empty to auto-create
```

### `abac.auto.tfvars` — ABAC + Genie config (auto-generated)

Generated by `make generate`. Contains groups, tag policies, tag assignments, FGAC policies, and Genie Space config (title, description, sample questions, instructions, benchmarks). Tune it before applying. See `generated/TUNING.md` for guidance.

## Genie Space

Managed automatically based on `genie_space_id` in `env.auto.tfvars`:


| `genie_space_id` | `uc_tables` | What happens on `make apply`                                                              |
| ---------------- | ----------- | ----------------------------------------------------------------------------------------- |
| Empty            | Non-empty   | Auto-creates a Genie Space from `uc_tables`, sets CAN_RUN ACLs, trashes on `make destroy` |
| Set              | Any         | Applies CAN_RUN ACLs to the existing space                                                |
| Empty            | Empty       | No Genie Space action                                                                     |


When `make generate` creates the ABAC config, it also generates Genie Space config in `abac.auto.tfvars`:


| Variable                  | Purpose                                                                                                    |
| ------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `genie_space_title`       | AI-generated title for the Genie Space (e.g., "Financial Compliance Analytics")                            |
| `genie_space_description` | 1–2 sentence summary of the space's scope and audience                                                     |
| `genie_sample_questions`  | Natural-language questions shown as conversation starters in the Genie UI                                  |
| `genie_instructions`      | Domain-specific guidance including business defaults (e.g., "customer" = active by default)                |
| `genie_benchmarks`        | Unambiguous ground-truth question + SQL pairs for evaluating Genie accuracy                                |
| `genie_sql_filters`       | Default WHERE clauses (e.g., active customers, completed transactions) that guide Genie's SQL generation   |
| `genie_sql_measures`      | Standard aggregate metrics (e.g., total revenue, average risk score)                                       |
| `genie_sql_expressions`   | Computed dimensions (e.g., transaction year, age bucket)                                                   |
| `genie_join_specs`        | Table relationships with join conditions (e.g., accounts to customers on CustomerID)                       |


All nine fields are included in the `serialized_space` when a new Genie Space is created. Review and tune them in `generated/abac.auto.tfvars` alongside the ABAC policies before applying.

## Make Targets


| Target                    | Description                                                      |
| ------------------------- | ---------------------------------------------------------------- |
| `make setup`              | Copy example files, create `ddl/` and `generated/` directories   |
| `make generate`           | Run `generate_abac.py` to produce masking SQL + tfvars           |
| `make validate-generated` | Validate `generated/` files (run after each tuning edit)         |
| `make validate`           | Validate root `abac.auto.tfvars` + `masking_functions.sql`       |
| `make promote`            | Validate `generated/` and copy to module root                    |
| `make plan`               | `terraform init` + `terraform plan`                              |
| `make apply`              | Validate, promote, then `terraform apply`                        |
| `make destroy`            | `terraform destroy` (cleans up everything including Genie Space) |
| `make clean`              | Remove generated files, Terraform state, and `.terraform/`       |


## Importing Existing Resources

If groups, tag policies, or FGAC policies already exist in Databricks, `terraform apply` will fail with "already exists". Import them first:

```bash
./scripts/import_existing.sh              # import all resource types
./scripts/import_existing.sh --dry-run    # preview without importing
./scripts/import_existing.sh --groups-only # import only groups
./scripts/import_existing.sh --tags-only   # import only tag policies
./scripts/import_existing.sh --fgac-only   # import only FGAC policies
```

See `[IMPORT_EXISTING.md](IMPORT_EXISTING.md)` for details.

## Troubleshooting

### "Provider produced inconsistent result after apply" (tag policies)

A known Databricks provider bug — the API reorders tag policy values after creation, causing a state mismatch. **Your tag policies are created correctly**; only the Terraform state comparison fails.

`make apply` prevents this entirely via three mechanisms: `make sync-tags` updates values directly through the Databricks SDK (bypassing Terraform), all tag policies are reimported before apply to sync state with the API's ordering, and `ignore_changes = [values]` in `tag_policies.tf` prevents Terraform from attempting value reordering. You should not see this error when using `make apply`.

If you run `terraform apply` directly (bypassing the Makefile) and hit this error, use `make apply` instead. If you need to recover manually:

```bash
# Remove and reimport all tag policies to sync state
python3 -c "import hcl2,sys; d=hcl2.load(open('abac.auto.tfvars')); [print(tp['key']) for tp in d.get('tag_policies',[])]" | \
  while read key; do
    terraform state rm "databricks_tag_policy.policies[\"$key\"]" 2>/dev/null || true
    terraform import "databricks_tag_policy.policies[\"$key\"]" "$key"
  done
terraform apply -parallelism=1 -auto-approve
```

### "already exists"

Resources (groups, tag policies) already exist in Databricks. Import them so Terraform can manage them:

```bash
./scripts/import_existing.sh
```

## Advanced Usage

### Generation options

```bash
python generate_abac.py --tables "a.b.*" "c.d.e"  # override uc_tables
python generate_abac.py --dry-run                  # preview prompt without calling LLM
```

### Examples

A pre-built finance demo is available in `examples/finance/` — copy the tfvars and SQL files to try without AI generation. Sample healthcare DDLs are in `examples/healthcare/ddl/` for testing `make generate`.

## Roadmap

- Unity Catalog metrics in Genie
- Multi Genie Space support
- Multi data steward / user support
- AI-assisted tuning and troubleshooting
- Auto-detect and import existing policies
- Import existing groups

