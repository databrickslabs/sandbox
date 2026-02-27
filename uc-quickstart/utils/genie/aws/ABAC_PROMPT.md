# ABAC Configuration Generator — AI Prompt Template

Copy everything below the line into ChatGPT, Claude, or Cursor. Paste your table DDL / `DESCRIBE TABLE` output where indicated. The AI will generate:

1. **`masking_functions.sql`** — SQL UDFs for your masking and row-filter requirements
2. **`abac.auto.tfvars`** — A complete variable file ready for `terraform apply`

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

**Row Filters (zero-argument, must be self-contained):**

Row filter functions take no arguments and return BOOLEAN. They must be **fully
self-contained** — every function they call must either be a Databricks built-in
or must also be defined in the same SQL file (before the caller). Do NOT reference
undefined helper functions like `get_current_user_metadata`.

Common patterns with example implementations:

- `filter_by_region_us() RETURNS BOOLEAN` — placeholder for US region filtering. `RETURN TRUE;`
- `filter_by_region_eu() RETURNS BOOLEAN` — placeholder for EU region filtering. `RETURN TRUE;`
- `filter_by_region_apac() RETURNS BOOLEAN` — placeholder for APAC region filtering. `RETURN TRUE;`
- `filter_trading_hours() RETURNS BOOLEAN` — restrict to non-market hours. `RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16;`
- `filter_audit_expiry() RETURNS BOOLEAN` — time-limited access. `RETURN CURRENT_DATE() <= DATE('2025-12-31');`

Note: The semicolon must be the **last character** on the RETURN line. Do NOT add inline comments after it (e.g., `RETURN TRUE; -- comment` breaks automated deployment).

If a row filter needs user-specific metadata (e.g. the current user's region),
define a helper function in the same SQL file **before** the filter that calls it.
For example, define `get_current_user_metadata(key STRING) RETURNS STRING` that
queries a `user_metadata` table or returns a stub `CAST(NULL AS STRING)`, then
reference it from the filter.

These are common patterns. If the user's data requires masking not covered above (e.g., vehicle VINs, student IDs, device serial numbers, product SKUs), create a new function following the same pattern (NULL-safe CASE expression, COMMENT describing usage).

### Output Format — File 1: `masking_functions.sql`

Group functions by target schema. Only create each function in the schema(s) where
it is referenced by `function_schema` in fgac_policies. If a function is used by
policies targeting multiple schemas, include it in each schema that needs it.

**CRITICAL — SQL formatting rules:**
- Each function MUST end with a semicolon (`;`) as the **last character on that line**
- Do NOT put inline comments after the semicolon (e.g., `RETURN TRUE; -- comment` will break parsing)
- Put comments on separate lines above the function or in the COMMENT clause

```sql
-- === schema_a functions ===
USE CATALOG my_catalog;
USE SCHEMA schema_a;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'description'
RETURN CASE ... END;

-- Row filter — semicolon must be the last char on the RETURN line
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters rows to show only US region data'
RETURN TRUE;

-- === schema_b functions ===
USE CATALOG my_catalog;
USE SCHEMA schema_b;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'description'
RETURN CASE ... END;
```

Only include functions the user actually needs. If a library function works as-is, still include it so the user has a self-contained SQL file.

### Output Format — File 2: `abac.auto.tfvars`

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
python validate_abac.py abac.auto.tfvars masking_functions.sql
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

### CRITICAL — One Mask Per Column Per Group

Each column must be matched by **at most one** column mask policy per principal group. If two policies with the same `to_principals` both match a column, Databricks will reject the query with `MULTIPLE_MASKS`. This means:

1. **No overlapping match conditions**: If two column mask policies target the same group and their `match_condition` values both evaluate to true for any column, you'll get a conflict. For example, `hasTagValue('phi_level', 'masked_phi')` and `hasTagValue('phi_level', 'masked_phi') AND hasTag('phi_level')` are logically identical — the `AND hasTag(...)` is always true when `hasTagValue(...)` already matches — so both policies would apply to the same columns.

2. **One tag value = one masking function**: Every column mask policy has a `match_condition` that selects columns by tag value, and ALL columns matching that value get the SAME masking function. You cannot use `columnName()` to differentiate — it is not supported. Therefore, if columns need different masking functions, they MUST have different tag values, even if they belong to the same sensitivity category.

   **Common mistake (WRONG):** Tagging FirstName, Email, and AccountID all as `pii_level = 'masked'`, then creating three separate policies — `mask_pii_partial`, `mask_email`, and `mask_account_number` — each matching `hasTagValue('pii_level', 'masked')`. This causes all three masks to apply to all three columns.

   **Correct approach:** Use distinct tag values per masking need:
   - FirstName, LastName → `pii_level = 'masked'` → policy uses `mask_pii_partial`
   - Email → `pii_level = 'masked_email'` → policy uses `mask_email`
   - AccountID → `pii_level = 'masked_account'` → policy uses `mask_account_number`

   Remember to add all new tag values to the `tag_policies` `values` list.

3. **Quick check**: For every pair of column mask policies that share any group in `to_principals`, verify that their `match_condition` values cannot both be true for the same column. If they can, either merge the policies or split the tag values. The number of distinct tag values in `tag_policies` should be >= the number of distinct masking functions you want to apply for that tag key.

### CRITICAL — Internal Consistency

Every tag value used in `tag_assignments` and in `match_condition` / `when_condition` MUST be defined in `tag_policies`. Before generating, cross-check:

1. Every `tag_value` in `tag_assignments` must appear in the `values` list of the corresponding `tag_key` in `tag_policies`
2. Every `hasTagValue('key', 'value')` in `match_condition` or `when_condition` must reference a `key` and `value` that exist in `tag_policies`
3. Every `function_name` in `fgac_policies` must have a corresponding `CREATE OR REPLACE FUNCTION` in `masking_functions.sql`
4. Every group in `to_principals` / `except_principals` must be defined in `groups`
5. If any generated function calls another non-built-in function (e.g. a helper like `get_current_user_metadata`), that helper MUST also be defined in `masking_functions.sql` **before** the function that calls it. Never reference undefined functions

Violating any of these causes validation failures. Double-check consistency across all three sections (`tag_policies`, `tag_assignments`, `fgac_policies`) before outputting.

**Common mistake**: Do NOT use a value from one tag policy in a different tag policy. For example, if `pii_level` has value `"masked"` but `compliance_level` does not, you MUST NOT write `tag_key = "compliance_level", tag_value = "masked"`. Each tag assignment and condition must use only the values defined for that specific tag key.

### Instructions

1. Generate `masking_functions.sql` with functions **grouped by target schema**. Use separate `USE CATALOG` / `USE SCHEMA` blocks for each schema. Only deploy each function to the schema(s) where it is referenced by `function_schema` in fgac_policies — do NOT duplicate all functions into every schema. Do NOT include `uc_catalog_name`, `uc_schema_name`, or authentication variables (databricks_account_id, etc.) in the generated abac.auto.tfvars. Every `fgac_policies` entry MUST include `catalog`, `function_catalog`, and `function_schema` — set them to the catalog/schema that each policy's table belongs to.
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
9. Generate Genie Space config — all nine fields below. **Derive everything from the user's actual tables, columns, and domain** — do NOT copy the finance/healthcare examples below if the user's data is from a different industry. Adapt terminology, metrics, filters, and joins to whatever vertical the tables belong to (retail, manufacturing, telecom, education, logistics, etc.):
   - `genie_space_title` — a concise, descriptive title reflecting the user's domain (e.g., finance → "Financial Compliance Analytics", retail → "Retail Sales & Inventory Explorer", telecom → "Network Performance Dashboard")
   - `genie_space_description` — 1–2 sentence summary of what the space covers and who it's for
   - `genie_sample_questions` — 5–10 natural-language questions a business user in that domain would ask (shown as conversation starters in the UI). Must reference the user's actual table/column names.
   - `genie_instructions` — domain-specific guidance for the Genie LLM. **Must include business defaults** — look at status/state columns in the user's tables and define which values are the default filter (e.g., if a table has `OrderStatus` with values like 'Fulfilled'/'Cancelled'/'Pending', instruct: "default to fulfilled orders"). Also cover date conventions, metric calculations, terminology, and masking awareness relevant to the user's domain.
   - `genie_benchmarks` — 3–5 benchmark questions with ground-truth SQL. **Each question must be unambiguous and self-contained** — include explicit qualifiers so the question and SQL agree on scope (e.g., "What is the average risk score for active customers?" not "What is the average customer risk score?"). Avoid questions that could reasonably be interpreted with different WHERE clauses.
   - `genie_sql_filters` — default WHERE clauses derived from the user's status/state columns (e.g., active records, completed transactions, open orders). Each filter has `sql`, `display_name`, `comment`, and `instruction`.
   - `genie_sql_measures` — standard aggregate metrics derived from the user's numeric columns (e.g., sums, averages, counts that are meaningful in the domain). Each measure has `alias`, `sql`, `display_name`, `comment`, and `instruction`.
   - `genie_sql_expressions` — computed dimensions derived from the user's date/category columns (e.g., year extraction, bucketing, status grouping). Each expression has `alias`, `sql`, `display_name`, `comment`, and `instruction`.
   - `genie_join_specs` — relationships between the user's tables based on foreign key columns (look for matching ID columns like `CustomerID`, `OrderID`, `ProductID`). Each join has `left_table`, `left_alias`, `right_table`, `right_alias`, `sql`, `comment`, and `instruction`.

### Output Format — Genie Space Config (in `abac.auto.tfvars`)

Include these variables alongside groups, tag_policies, etc. The example below shows a **finance/healthcare** scenario — adapt all values to match the user's actual tables and industry:

```hcl
genie_space_title       = "Financial & Clinical Analytics"
genie_space_description = "Explore transaction data, patient encounters, and compliance metrics. Designed for analysts, compliance officers, and clinical staff."

genie_sample_questions = [
  "What is the total revenue by region for last quarter?",
  "Show the top 10 active customers by transaction volume",
  "Which accounts have been flagged for AML review?",
  "How many patient encounters occurred last month?",
  "What is the average completed transaction amount by account type?",
]

genie_instructions = "When asked about 'customers' without a status qualifier, default to active customers (CustomerStatus = 'Active'). When asked about 'transactions' without specifying status, default to completed transactions (TransactionStatus = 'Completed'). 'Last month' means the previous calendar month (not last 30 days). Round monetary values to 2 decimal places. Patient names are masked for non-clinical roles — queries about patient counts or encounter dates are always allowed."

genie_benchmarks = [
  {
    question = "What is the total amount of completed transactions?"
    sql      = "SELECT SUM(Amount) as total_amount FROM catalog.schema.transactions WHERE TransactionStatus = 'Completed'"
  },
  {
    question = "How many patient encounters occurred last month?"
    sql      = "SELECT COUNT(*) FROM catalog.schema.encounters WHERE EncounterDate >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND EncounterDate < DATE_TRUNC('month', CURRENT_DATE)"
  },
  {
    question = "What is the average risk score for active customers?"
    sql      = "SELECT AVG(RiskScore) as avg_risk_score FROM catalog.schema.customers WHERE CustomerStatus = 'Active'"
  },
]

genie_sql_filters = [
  {
    sql          = "customers.CustomerStatus = 'Active'"
    display_name = "active customers"
    comment      = "Only include customers with Active status"
    instruction  = "Apply when the user asks about customers without specifying a status"
  },
  {
    sql          = "transactions.TransactionStatus = 'Completed'"
    display_name = "completed transactions"
    comment      = "Only include completed transactions"
    instruction  = "Apply when the user asks about transactions or amounts without specifying a status"
  },
]

genie_sql_measures = [
  {
    alias        = "total_revenue"
    sql          = "SUM(transactions.Amount)"
    display_name = "total revenue"
    comment      = "Sum of all transaction amounts"
    instruction  = "Use for revenue, total amount, or sales calculations"
  },
  {
    alias        = "avg_risk_score"
    sql          = "AVG(customers.RiskScore)"
    display_name = "average risk score"
    comment      = "Average AML risk score across customers"
    instruction  = "Use when asked about risk scores or risk averages"
  },
]

genie_sql_expressions = [
  {
    alias        = "transaction_year"
    sql          = "YEAR(transactions.TransactionDate)"
    display_name = "transaction year"
    comment      = "Extracts year from transaction date"
    instruction  = "Use for year-over-year analysis of transactions"
  },
]

genie_join_specs = [
  {
    left_table  = "catalog.schema.accounts"
    left_alias  = "accounts"
    right_table = "catalog.schema.customers"
    right_alias = "customers"
    sql         = "accounts.CustomerID = customers.CustomerID"
    comment     = "Join accounts to customers on CustomerID"
    instruction = "Use when you need customer details for account queries"
  },
  {
    left_table  = "catalog.schema.transactions"
    left_alias  = "transactions"
    right_table = "catalog.schema.accounts"
    right_alias = "accounts"
    sql         = "transactions.AccountID = accounts.AccountID"
    comment     = "Join transactions to accounts on AccountID"
    instruction = "Use when you need account or customer context for transactions"
  },
]
```

---

### MY TABLES (paste below)

Tables are provided with fully qualified names (catalog.schema.table).
Derive the catalog and schema for each policy from the table's fully qualified name.

```
-- Table DDLs are auto-fetched and pasted here.
-- Each table is fully qualified: my_catalog.my_schema.my_table
```
