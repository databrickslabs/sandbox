# ABAC Configuration Generator — AI Prompt Template

Copy everything below the line into ChatGPT, Claude, or Cursor. Paste your table DDL / `DESCRIBE TABLE` output where indicated. The AI will generate:

1. **`masking_functions.sql`** — SQL UDFs for your masking and row-filter requirements
2. **`terraform.tfvars`** — A complete variable file ready for `terraform apply`

---

## Prompt (copy from here)

You are an expert in Databricks Unity Catalog Attribute-Based Access Control (ABAC). I will give you my table schemas. You will analyze the columns for sensitivity (PII, financial, health, etc.), then generate two files:

### What is ABAC?

ABAC uses governed **tags** on tables/columns and **FGAC policies** (column masks + row filters) to control data access based on **group membership**. The flow is:

1. Create **groups** (access tiers like "Junior_Analyst", "Admin")
2. Create **tag policies** (e.g., `sensitivity` with values `public`, `confidential`, `restricted`)
3. Assign **tags** to tables and columns
4. Create **FGAC policies** that match tagged columns/tables and apply masking functions for specific groups

### Available Masking Function Patterns

Use these signatures. Replace `{catalog}.{schema}` with the user's catalog and schema.

**PII:**
- `mask_pii_partial(input STRING) RETURNS STRING` — first + last char visible, middle masked
- `mask_ssn(ssn STRING) RETURNS STRING` — last 4 digits of SSN visible
- `mask_email(email STRING) RETURNS STRING` — masks local part, keeps domain
- `mask_phone(phone STRING) RETURNS STRING` — last 4 digits visible
- `mask_full_name(name STRING) RETURNS STRING` — reduces to initials

**Financial:**
- `mask_credit_card_full(card_number STRING) RETURNS STRING` — all digits hidden
- `mask_credit_card_last4(card_number STRING) RETURNS STRING` — last 4 visible
- `mask_account_number(account_id STRING) RETURNS STRING` — deterministic SHA-256 token
- `mask_amount_rounded(amount DECIMAL(18,2)) RETURNS DECIMAL(18,2)` — round to nearest 10/100
- `mask_iban(iban STRING) RETURNS STRING` — country code + last 4

**Health:**
- `mask_mrn(mrn STRING) RETURNS STRING` — last 4 digits of MRN
- `mask_diagnosis_code(code STRING) RETURNS STRING` — ICD category visible, specifics hidden

**General:**
- `mask_redact(input STRING) RETURNS STRING` — replace with `[REDACTED]`
- `mask_hash(input STRING) RETURNS STRING` — full SHA-256 hash
- `mask_nullify(input STRING) RETURNS STRING` — return NULL

**Row Filters (zero-argument):**
- `filter_by_region_us() RETURNS BOOLEAN` — US regional filter
- `filter_by_region_eu() RETURNS BOOLEAN` — EU regional filter
- `filter_by_region_apac() RETURNS BOOLEAN` — APAC regional filter
- `filter_trading_hours() RETURNS BOOLEAN` — outside NYSE hours only
- `filter_audit_expiry() RETURNS BOOLEAN` — temporary auditor access

If none of these fit, create a new function following the same pattern (NULL-safe CASE expression, COMMENT describing usage).

### Output Format — File 1: `masking_functions.sql`

```sql
USE CATALOG {catalog};
USE SCHEMA {schema};

CREATE OR REPLACE FUNCTION function_name(param TYPE)
RETURNS TYPE
COMMENT 'description'
RETURN CASE ... END;
```

Only include functions the user actually needs. If a library function works as-is, still include it so the user has a self-contained SQL file.

### Output Format — File 2: `terraform.tfvars`

```hcl
# Authentication (user fills in)
databricks_account_id    = ""
databricks_client_id     = ""
databricks_client_secret = ""
databricks_workspace_id  = ""
databricks_workspace_host = ""

uc_catalog_name = "{catalog}"
uc_schema_name  = "{schema}"

groups = {
  "GroupName" = { description = "What this group can see" }
}

tag_policies = [
  { key = "tag_name", description = "...", values = ["val1", "val2"] },
]

# entity_name and function_name are RELATIVE to uc_catalog_name.uc_schema_name.
# Terraform automatically prepends the catalog.schema prefix.
tag_assignments = [
  { entity_type = "columns", entity_name = "Table.Column", tag_key = "tag_name", tag_value = "val1" },
]

fgac_policies = [
  # Column mask:
  {
    name            = "policy_name"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["GroupName"]
    comment         = "Description"
    match_condition = "hasTagValue('tag_name', 'val1')"
    match_alias     = "alias"
    function_name   = "function_name"
  },
  # Row filter:
  {
    name           = "filter_name"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["GroupName"]
    comment        = "Description"
    when_condition = "hasTagValue('tag_name', 'val1')"
    function_name  = "filter_function"
  },
]

group_members = {}
```

### Validation

After generating both files, the user should validate them before running `terraform apply`:

```bash
pip install python-hcl2
python validate_abac.py terraform.tfvars masking_functions.sql
```

This checks cross-references (groups, tags, functions), naming conventions, and structure. Fix any `[FAIL]` errors before proceeding.

### Instructions

1. Use the user's **catalog** and **schema** from the "MY CATALOG AND SCHEMA" section for `USE CATALOG` / `USE SCHEMA` in SQL and `uc_catalog_name` / `uc_schema_name` in tfvars
2. Analyze each column in the user's tables for sensitivity:
   - PII (names, emails, SSN, phone, address)
   - Financial (credit cards, account numbers, amounts, IBAN)
   - Health (MRN, diagnosis codes)
   - Regional/residency (region columns that need row filtering)
3. Propose groups — typically 2-5 access tiers (e.g., restricted, standard, privileged, admin)
4. Design tag policies — one per sensitivity dimension (e.g., `pii_level`, `pci_clearance`)
5. Map tags to the user's specific tables and columns
6. Select masking functions from the library above (or create new ones)
7. Generate both output files using **relative** names (Terraform prepends `uc_catalog_name.uc_schema_name` automatically)

---

### MY CATALOG AND SCHEMA

```
Catalog: ___________    (e.g. prod_healthcare, my_dev_catalog)
Schema:  ___________    (e.g. clinical, finance, public)
```

### MY TABLES (paste below)

```
-- Paste your DESCRIBE TABLE output or CREATE TABLE DDL here.
-- Include all tables you want ABAC policies for.
-- Example:
--   DESCRIBE TABLE my_catalog.my_schema.customers;
--   DESCRIBE TABLE my_catalog.my_schema.orders;
```
