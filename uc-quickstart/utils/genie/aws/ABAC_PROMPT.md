# ABAC Configuration Generator — AI Prompt Template

Copy everything below the line into ChatGPT, Claude, or Cursor. Paste your table DDL / `DESCRIBE TABLE` output where indicated. The AI will generate:

1. **`masking_functions.sql`** — SQL UDFs for your masking and row-filter requirements
2. **`terraform.tfvars`** — A complete variable file ready for `terraform apply`

---

## Prompt (copy from here)

You are an expert in Databricks Unity Catalog Attribute-Based Access Control (ABAC). I will give you my table schemas from any industry or domain. You will analyze the columns for sensitivity (PII, financial, health, compliance, proprietary, etc.), then generate two files:

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

These are common patterns. If the user's data requires masking not covered above (e.g., vehicle VINs, student IDs, device serial numbers, product SKUs), create a new function following the same pattern (NULL-safe CASE expression, COMMENT describing usage).

### Output Format — File 1: `masking_functions.sql`

Group functions by target schema. Only create each function in the schema(s) where
it is referenced by `function_schema` in fgac_policies. If a function is used by
policies targeting multiple schemas, include it in each schema that needs it.

```sql
-- === schema_a functions ===
USE CATALOG my_catalog;
USE SCHEMA schema_a;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'description'
RETURN CASE ... END;

-- === schema_b functions ===
USE CATALOG my_catalog;
USE SCHEMA schema_b;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'description'
RETURN CASE ... END;
```

Only include functions the user actually needs. If a library function works as-is, still include it so the user has a self-contained SQL file.

### Output Format — File 2: `terraform.tfvars`

```hcl
groups = {
  "GroupName" = { description = "What this group can see" }
}

tag_policies = [
  { key = "tag_name", description = "...", values = ["val1", "val2"] },
]

# entity_name: always use fully qualified names (catalog.schema.table for tables,
# catalog.schema.table.column for columns).
tag_assignments = [
  # Table-level tags (optional — scope column masks or row filters to specific tables, or for governance):
  # { entity_type = "tables",  entity_name = "catalog.schema.Table",     tag_key = "tag_name", tag_value = "val1" },
  { entity_type = "columns", entity_name = "catalog.schema.Table.Column", tag_key = "tag_name", tag_value = "val1" },
]

fgac_policies = [
  # Column mask (when_condition is optional — omit to apply to all tables):
  {
    name             = "policy_name"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "my_catalog"
    to_principals    = ["GroupName"]
    comment          = "Description"
    match_condition  = "hasTagValue('tag_name', 'val1')"
    match_alias      = "alias"
    function_name    = "function_name"
    function_catalog = "my_catalog"
    function_schema  = "my_schema"
  },
  # Row filter (when_condition is optional — omit to apply to all tables):
  {
    name             = "filter_name"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "my_catalog"
    to_principals    = ["GroupName"]
    comment          = "Description"
    when_condition   = "hasTagValue('tag_name', 'val1')"
    function_name    = "filter_function"
    function_catalog = "my_catalog"
    function_schema  = "my_schema"
  },
]

# when_condition is OPTIONAL for both column masks and row filters:
# - Column masks: omit when_condition to let match_condition (in match_columns) select
#   columns across ALL tables. Or set when_condition (e.g. "hasTag('tag_name')") to
#   scope the mask to specific tagged tables only.
# - Row filters: omit when_condition to apply to all tables, or provide it to scope
#   to specific tagged tables.
# - If you use when_condition, the referenced tags must be assigned at the TABLE level
#   (entity_type = "tables" in tag_assignments).

group_members = {}
```

### Validation

After generating both files, the user should validate them before running `terraform apply`:

```bash
pip install python-hcl2
python validate_abac.py terraform.tfvars masking_functions.sql
```

This checks cross-references (groups, tags, functions), naming conventions, and structure. Fix any `[FAIL]` errors before proceeding.

### CRITICAL — Valid Condition Syntax

The `match_condition` and `when_condition` fields ONLY support these functions:

- `hasTagValue('tag_key', 'tag_value')` — matches entities with a specific tag value
- `hasTag('tag_key')` — matches entities that have the tag (any value)
- Combine with `AND` / `OR`

**FORBIDDEN** — the following will cause compilation errors:
- `columnName() = '...'` — NOT supported
- `columnName() IN (...)` — NOT supported
- `tableName() = '...'` — NOT supported
- Any comparison operators (`=`, `!=`, `<`, `>`, `IN`)

To target specific columns, use **distinct tag values** assigned to those columns, not `columnName()`. For example, instead of `hasTagValue('phi_level', 'full_phi') AND columnName() = 'MRN'`, create a separate tag value like `phi_level = 'mrn_restricted'` and assign it only to the MRN column.

### CRITICAL — Internal Consistency

Every tag value used in `tag_assignments` and in `match_condition` / `when_condition` MUST be defined in `tag_policies`. Before generating, cross-check:

1. Every `tag_value` in `tag_assignments` must appear in the `values` list of the corresponding `tag_key` in `tag_policies`
2. Every `hasTagValue('key', 'value')` in `match_condition` or `when_condition` must reference a `key` and `value` that exist in `tag_policies`
3. Every `function_name` in `fgac_policies` must have a corresponding `CREATE OR REPLACE FUNCTION` in `masking_functions.sql`
4. Every group in `to_principals` / `except_principals` must be defined in `groups`

Violating any of these causes validation failures. Double-check consistency across all three sections (`tag_policies`, `tag_assignments`, `fgac_policies`) before outputting.

### Instructions

1. Generate `masking_functions.sql` with functions **grouped by target schema**. Use separate `USE CATALOG` / `USE SCHEMA` blocks for each schema. Only deploy each function to the schema(s) where it is referenced by `function_schema` in fgac_policies — do NOT duplicate all functions into every schema. Do NOT include `uc_catalog_name`, `uc_schema_name`, or authentication variables (databricks_account_id, etc.) in the generated terraform.tfvars. Every `fgac_policies` entry MUST include `catalog`, `function_catalog`, and `function_schema` — set them to the catalog/schema that each policy's table belongs to.
2. Analyze each column in the user's tables for sensitivity. Common categories include but are not limited to:
   - PII (names, emails, SSN, phone, address, date of birth, national IDs)
   - Financial (credit cards, account numbers, amounts, IBAN, trading data)
   - Health / PHI (MRN, diagnosis codes, clinical notes, insurance IDs)
   - Regional / residency (region columns that need row filtering)
   - Confidential business data (proprietary scores, internal metrics, trade secrets)
   - Compliance-driven fields (audit logs, access timestamps, regulatory identifiers)
   Adapt to whatever domain the user's tables belong to — retail, manufacturing, education, telecom, government, etc. Do NOT limit analysis to healthcare or finance.
3. Propose groups — typically 2-5 access tiers (e.g., restricted, standard, privileged, admin)
4. Design tag policies — one per sensitivity dimension (e.g., `pii_level`, `pci_clearance`)
5. Map tags to the user's specific columns. **Use distinct tag values to differentiate columns that need different masking** — do NOT use `columnName()` in conditions. Table-level tags (entity_type = "tables") are optional — use them to scope column masks or row filters to specific tables, or for governance. **Always use fully qualified entity names** (e.g. `catalog.schema.Table` for tables, `catalog.schema.Table.Column` for columns)
6. Select masking functions from the library above (or create new ones)
7. Generate both output files. For entity names in tag_assignments, always use **fully qualified** names (`catalog.schema.table` or `catalog.schema.table.column`). For function_name in fgac_policies, use relative names only (e.g. `mask_pii`). Every fgac_policy MUST include `catalog`, `function_catalog`, and `function_schema`. **CRITICAL**: set `function_schema` to the schema where the tagged columns actually live — do NOT default all policies to the first schema. In `masking_functions.sql`, group the `CREATE FUNCTION` statements by schema with separate `USE SCHEMA` blocks. Only create each function in the schema where it is needed
8. Every `match_condition` and `when_condition` MUST only use `hasTagValue()` and/or `hasTag()` — no other functions or operators

---

### MY TABLES (paste below)

Tables are provided with fully qualified names (catalog.schema.table).
Derive the catalog and schema for each policy from the table's fully qualified name.

```
-- Table DDLs are auto-fetched and pasted here.
-- Each table is fully qualified: my_catalog.my_schema.my_table
```
