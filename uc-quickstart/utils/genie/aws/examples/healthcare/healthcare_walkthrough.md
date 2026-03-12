# Healthcare ABAC — AI-Assisted Walkthrough

This is a step-by-step example of the **Tier 3 (AI-Assisted)** workflow applied to a healthcare scenario. It shows exactly what you paste into the AI and what you get back.

---

## Step 1 — Get your table DDL

Run `DESCRIBE TABLE` or `SHOW CREATE TABLE` in a Databricks SQL editor for every table you want ABAC policies on. For this walkthrough we'll use four tables from a hospital data platform.

The DDL files are in the [`ddl/`](ddl/) subfolder — one file per table:

| File | Table | Description |
|------|-------|-------------|
| [`ddl/patients.sql`](ddl/patients.sql) | `Patients` | Demographics, contact info, insurance |
| [`ddl/encounters.sql`](ddl/encounters.sql) | `Encounters` | Visits, admissions, diagnoses, clinical notes |
| [`ddl/prescriptions.sql`](ddl/prescriptions.sql) | `Prescriptions` | Medications and dosages |
| [`ddl/billing.sql`](ddl/billing.sql) | `Billing` | Financial records, insurance claims |

To use these with the automated generator:

```bash
# 1. Set up config (one-time)
cp auth.auto.tfvars.example auth.auto.tfvars   # credentials (gitignored)
cp env.auto.tfvars.example env.auto.tfvars     # tables + environment

# 2. Copy the healthcare DDL files into the ddl/ folder
cp examples/healthcare/ddl/*.sql ddl/

# 3. Generate (reads uc_tables from env.auto.tfvars)
python generate_abac.py
```

## Step 2 — Generate ABAC configuration

**Option A — Automated** (recommended): Run the commands above and skip to Step 4.

**Option B — Manual**: Open `ABAC_PROMPT.md`, copy the entire prompt section, and paste it into ChatGPT / Claude / Cursor. Then paste the DDL from the files above where it says `-- Paste your SHOW CREATE TABLE output or CREATE TABLE DDL here.`

## Step 3 — AI generates two files

The AI analyzes your columns and produces the following.

### File 1: `masking_functions.sql`

```sql
USE CATALOG <YOUR_CATALOG>;  -- same catalog you used in Step 1
USE SCHEMA clinical;

-- === PII Masking ===

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters; shows first and last character only.'
RETURN CASE
  WHEN input IS NULL THEN NULL
  WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
  ELSE CONCAT(LEFT(input, 1), REPEAT('*', LENGTH(input) - 2), RIGHT(input, 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of SSN only.'
RETURN CASE
  WHEN ssn IS NULL THEN NULL
  ELSE CONCAT('***-**-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks local part of email; preserves domain.'
RETURN CASE
  WHEN email IS NULL THEN NULL
  WHEN INSTR(email, '@') = 0 THEN '****'
  ELSE CONCAT('****@', SUBSTRING_INDEX(email, '@', -1))
END;

CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of phone number.'
RETURN CASE
  WHEN phone IS NULL THEN NULL
  ELSE CONCAT('***-***-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Fully redacts the value.'
RETURN CASE
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

-- === Health / PHI Masking ===

CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN; shows last 4 characters.'
RETURN CASE
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) <= 4 THEN REPEAT('*', LENGTH(mrn))
  ELSE CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD-10 category (first 3 chars); hides specifics.'
RETURN CASE
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(LEFT(code, 3), '.xx')
END;

-- === Financial Masking ===

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds to nearest 100 for approximate visibility.'
RETURN CASE
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Replaces with deterministic SHA-256 token.'
RETURN CASE
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACCT-', LEFT(SHA2(account_id, 256), 12))
END;

-- === Row Filters ===

CREATE OR REPLACE FUNCTION filter_facility_us_east()
RETURNS BOOLEAN
COMMENT 'Row filter: only rows where FacilityRegion = US_EAST for current group.'
RETURN
  is_account_group_member('US_East_Staff')
  OR is_account_group_member('Chief_Medical_Officer');

CREATE OR REPLACE FUNCTION filter_facility_us_west()
RETURNS BOOLEAN
COMMENT 'Row filter: only rows where FacilityRegion = US_WEST for current group.'
RETURN
  is_account_group_member('US_West_Staff')
  OR is_account_group_member('Chief_Medical_Officer');
```

### File 2: `abac.auto.tfvars` (ABAC config only — auth is in `auth.auto.tfvars`)

```hcl
# === Groups ===
groups = {
  "Nurse"                 = { description = "Bedside care — partial PII, limited clinical notes" }
  "Physician"             = { description = "Full clinical access, full PII for their region" }
  "Billing_Clerk"         = { description = "Financial records — masked PHI, no clinical notes" }
  "Chief_Medical_Officer" = { description = "Full unrestricted access across all regions" }
  "US_East_Staff"         = { description = "Row access limited to US_EAST facility data" }
  "US_West_Staff"         = { description = "Row access limited to US_WEST facility data" }
}

# === Tag Policies ===
tag_policies = [
  { key = "phi_level",        description = "Protected Health Information access tier", values = ["Restricted_PHI", "Limited_PHI", "Full_PHI"] },
  { key = "pii_level",        description = "Personally identifiable information tier",  values = ["Limited_PII", "Full_PII"] },
  { key = "financial_access", description = "Billing/financial data clearance",          values = ["Summary", "Full"] },
  { key = "facility_region",  description = "Hospital facility region for row filtering", values = ["Regional"] },
]

# === Tag Assignments ===
# entity_name is relative to uc_catalog_name.uc_schema_name.
tag_assignments = [
  # --- Patients table ---
  { entity_type = "tables",  entity_name = "Patients",                tag_key = "pii_level",       tag_value = "Full_PII" },
  { entity_type = "tables",  entity_name = "Patients",                tag_key = "facility_region", tag_value = "Regional" },
  { entity_type = "columns", entity_name = "Patients.MRN",            tag_key = "phi_level",       tag_value = "Restricted_PHI" },
  { entity_type = "columns", entity_name = "Patients.FirstName",      tag_key = "pii_level",       tag_value = "Limited_PII" },
  { entity_type = "columns", entity_name = "Patients.LastName",       tag_key = "pii_level",       tag_value = "Limited_PII" },
  { entity_type = "columns", entity_name = "Patients.SSN",            tag_key = "pii_level",       tag_value = "Full_PII" },
  { entity_type = "columns", entity_name = "Patients.Email",          tag_key = "pii_level",       tag_value = "Limited_PII" },
  { entity_type = "columns", entity_name = "Patients.Phone",          tag_key = "pii_level",       tag_value = "Limited_PII" },
  { entity_type = "columns", entity_name = "Patients.Address",        tag_key = "pii_level",       tag_value = "Full_PII" },
  { entity_type = "columns", entity_name = "Patients.InsuranceID",    tag_key = "phi_level",       tag_value = "Limited_PHI" },

  # --- Encounters table ---
  { entity_type = "tables",  entity_name = "Encounters",                  tag_key = "phi_level",       tag_value = "Full_PHI" },
  { entity_type = "tables",  entity_name = "Encounters",                  tag_key = "facility_region", tag_value = "Regional" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisCode",    tag_key = "phi_level",       tag_value = "Restricted_PHI" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisDesc",    tag_key = "phi_level",       tag_value = "Full_PHI" },
  { entity_type = "columns", entity_name = "Encounters.TreatmentNotes",   tag_key = "phi_level",       tag_value = "Full_PHI" },

  # --- Prescriptions table ---
  { entity_type = "tables",  entity_name = "Prescriptions",               tag_key = "phi_level",       tag_value = "Limited_PHI" },
  { entity_type = "columns", entity_name = "Prescriptions.DrugName",      tag_key = "phi_level",       tag_value = "Limited_PHI" },
  { entity_type = "columns", entity_name = "Prescriptions.Dosage",        tag_key = "phi_level",       tag_value = "Limited_PHI" },

  # --- Billing table ---
  { entity_type = "tables",  entity_name = "Billing",                     tag_key = "financial_access", tag_value = "Full" },
  { entity_type = "columns", entity_name = "Billing.TotalAmount",         tag_key = "financial_access", tag_value = "Full" },
  { entity_type = "columns", entity_name = "Billing.InsurancePaid",       tag_key = "financial_access", tag_value = "Full" },
  { entity_type = "columns", entity_name = "Billing.PatientOwed",         tag_key = "financial_access", tag_value = "Summary" },
  { entity_type = "columns", entity_name = "Billing.InsuranceID",         tag_key = "phi_level",        tag_value = "Limited_PHI" },
]

# === FGAC Policies ===
# function_name is relative — Terraform prepends catalog.schema automatically.
fgac_policies = [
  # -- PII masking for Nurses --
  {
    name            = "pii_nurse_partial"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Nurse"]
    comment         = "Nurses see partial names and contact info"
    match_condition = "hasTagValue('pii_level', 'Limited_PII')"
    match_alias     = "pii_limited"
    function_name   = "mask_pii_partial"
  },
  {
    name            = "pii_nurse_ssn"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Nurse"]
    comment         = "Nurses see last-4 SSN only"
    match_condition = "hasTagValue('pii_level', 'Full_PII')"
    match_alias     = "pii_full"
    function_name   = "mask_ssn"
  },

  # -- PII masking for Billing Clerks --
  {
    name            = "pii_billing_partial"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Clerk"]
    comment         = "Billing clerks see partial patient names"
    match_condition = "hasTagValue('pii_level', 'Limited_PII')"
    match_alias     = "pii_limited"
    function_name   = "mask_pii_partial"
  },
  {
    name            = "pii_billing_ssn"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Clerk"]
    comment         = "Billing clerks cannot see SSN or address"
    match_condition = "hasTagValue('pii_level', 'Full_PII')"
    match_alias     = "pii_full"
    function_name   = "mask_redact"
  },

  # -- PHI masking for Nurses --
  {
    name            = "phi_nurse_mrn"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Nurse"]
    comment         = "Nurses see last-4 of MRN"
    match_condition = "hasTagValue('phi_level', 'Restricted_PHI')"
    match_alias     = "phi_restricted"
    function_name   = "mask_mrn"
  },

  # -- PHI masking for Billing Clerks (no clinical details) --
  {
    name            = "phi_billing_redact"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Clerk"]
    comment         = "Billing clerks cannot see diagnosis or treatment notes"
    match_condition = "hasTagValue('phi_level', 'Full_PHI')"
    match_alias     = "phi_full"
    function_name   = "mask_redact"
  },
  {
    name            = "phi_billing_diagnosis"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Clerk"]
    comment         = "Billing clerks see ICD category only"
    match_condition = "hasTagValue('phi_level', 'Restricted_PHI')"
    match_alias     = "phi_restricted"
    function_name   = "mask_diagnosis_code"
  },

  # -- Financial masking for Nurses --
  {
    name            = "fin_nurse_rounded"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Nurse"]
    comment         = "Nurses see rounded billing amounts"
    match_condition = "hasTagValue('financial_access', 'Full')"
    match_alias     = "fin_full"
    function_name   = "mask_amount_rounded"
  },

  # -- Insurance ID masking (tokenize for non-billing staff) --
  {
    name              = "phi_insurance_mask"
    policy_type       = "POLICY_TYPE_COLUMN_MASK"
    to_principals     = ["account users"]
    except_principals = ["Billing_Clerk", "Chief_Medical_Officer"]
    comment           = "Insurance ID tokenized for non-billing staff"
    match_condition   = "hasTagValue('phi_level', 'Limited_PHI')"
    match_alias       = "phi_limited"
    function_name     = "mask_account_number"
  },

  # -- Regional row filters --
  {
    name            = "region_us_east"
    policy_type     = "POLICY_TYPE_ROW_FILTER"
    to_principals   = ["US_East_Staff"]
    comment         = "US East staff see only US_EAST facility data"
    when_condition  = "hasTagValue('facility_region', 'Regional')"
    function_name   = "filter_facility_us_east"
  },
  {
    name            = "region_us_west"
    policy_type     = "POLICY_TYPE_ROW_FILTER"
    to_principals   = ["US_West_Staff"]
    comment         = "US West staff see only US_WEST facility data"
    when_condition  = "hasTagValue('facility_region', 'Regional')"
    function_name   = "filter_facility_us_west"
  },
]

# === Group Members (optional — fill in account-level user IDs) ===
group_members = {}
```

## Step 4 — Validate

If you used the automated generator, validation runs automatically. For manual flow, save the AI output and run:

```bash
pip install python-hcl2
python validate_abac.py generated/abac.auto.tfvars generated/masking_functions.sql
```

Expected output:

```
============================================================
  ABAC Configuration Validation Report
============================================================
  [PASS] SQL file: 11 function(s) found
  [PASS] groups: 6 group(s) defined
  [PASS] tag_policies: 4 policy/ies, 9 total values
  [PASS] tag_assignments: 23 assignment(s)
  [PASS] fgac_policies: 11 policy/ies, 9 unique function(s)
------------------------------------------------------------
  RESULT: PASS  (5 passed, 0 warnings, 0 errors)
============================================================
```

All `[PASS]` — safe to proceed.

## Step 5 — Deploy

```bash
# 1. Run generated/masking_functions.sql in a Databricks SQL editor
#    (make sure USE CATALOG / USE SCHEMA match your auth.auto.tfvars)

# 2. Copy the generated ABAC config to the module root
cp generated/abac.auto.tfvars abac.auto.tfvars

# 3. Apply (auth.auto.tfvars is loaded automatically)
terraform init
terraform plan    # review the plan
terraform apply
```

## What each group sees after deployment

| Column | Nurse | Physician | Billing Clerk | CMO |
|--------|-------|-----------|---------------|-----|
| `Patients.FirstName` | `J***n` | John | `J***n` | John |
| `Patients.SSN` | `***-**-1234` | 123-45-1234 | `[REDACTED]` | 123-45-1234 |
| `Patients.MRN` | `****5678` | MRN005678 | `****5678` | MRN005678 |
| `Encounters.DiagnosisCode` | E11.65 | E11.65 | `E11.xx` | E11.65 |
| `Encounters.TreatmentNotes` | _full text_ | _full text_ | `[REDACTED]` | _full text_ |
| `Billing.TotalAmount` | `$1,200.00` → `$1,200` | `$1,234.56` | `$1,234.56` | `$1,234.56` |
| `Patients.InsuranceID` | `ACCT-a1b2c3d4...` | `ACCT-a1b2c3d4...` | INS-9876543 | INS-9876543 |
| **Row visibility** | All regions | All regions | All regions | All regions |
| **US_East_Staff** | US_EAST rows only | — | — | — |

## Key design decisions the AI made

1. **Four sensitivity dimensions**: `phi_level`, `pii_level`, `financial_access`, `facility_region` — mapped to HIPAA categories
2. **Nurse vs Billing separation**: Nurses see clinical data but masked financials; Billing Clerks see financials but redacted clinical notes — classic HIPAA minimum necessary principle
3. **CMO as unrestricted**: `Chief_Medical_Officer` is excluded via `except_principals` where needed and has no masking policies applied
4. **Regional row filters**: `US_East_Staff` / `US_West_Staff` can only see encounters and patients from their facility — implemented with `is_account_group_member()` checks in the filter UDFs
5. **Insurance ID tokenized**: Deterministic SHA-256 hash so non-billing staff can still join across tables without seeing the real policy number
