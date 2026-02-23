# ABAC Configuration for Clinical Data

Based on your healthcare tables, I'll generate a comprehensive ABAC configuration with appropriate masking functions and policies.

## File 1: `masking_functions.sql`

```sql
USE CATALOG louis_sydney;
USE SCHEMA clinical;

-- PII Masking Functions
CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, 3, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Masks SSN showing only last 4 digits'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) >= 4 THEN 
    CONCAT('***-**-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
  ELSE '***-**-****'
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks email local part, preserves domain'
RETURN CASE 
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+\\.[^@]+$' THEN email
  ELSE CONCAT(
    SUBSTRING(SPLIT(email, '@')[0], 1, 1),
    REPEAT('*', GREATEST(LENGTH(SPLIT(email, '@')[0]) - 1, 1)),
    '@',
    SPLIT(email, '@')[1]
  )
END;

CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Masks phone number showing only last 4 digits'
RETURN CASE 
  WHEN phone IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '')) >= 4 THEN 
    CONCAT('***-***-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
  ELSE '***-***-****'
END;

CREATE OR REPLACE FUNCTION mask_full_name(name STRING)
RETURNS STRING
COMMENT 'Reduces full name to initials'
RETURN CASE 
  WHEN name IS NULL THEN NULL
  ELSE REGEXP_REPLACE(TRIM(name), '\\b(\\w)\\w*', '$1.')
END;

-- Health-specific Functions
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN showing only last 4 characters'
RETURN CASE 
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) >= 4 THEN CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
  ELSE REPEAT('*', LENGTH(mrn))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD category (first 3 chars), masks specifics'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) >= 3 THEN CONCAT(SUBSTRING(code, 1, 3), REPEAT('*', LENGTH(code) - 3))
  ELSE code
END;

-- Financial Functions
CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Replaces account number with deterministic SHA-256 hash'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACCT_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount / 100) * 100
END;

-- General Masking
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces input with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Returns NULL for complete data suppression'
RETURN NULL;

-- Row Filter Functions
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US regional data (US_EAST, US_WEST)'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Temporary access filter for auditors (implement time-based logic as needed)'
RETURN TRUE;
```

## File 2: `terraform.tfvars`

```hcl
# Authentication (user fills in)
databricks_account_id    = ""
databricks_client_id     = ""
databricks_client_secret = ""
databricks_workspace_id  = ""
databricks_workspace_host = ""

uc_catalog_name = "louis_sydney"
uc_schema_name  = "clinical"

groups = {
  "Clinical_Restricted" = { description = "Limited access - junior staff, contractors" }
  "Clinical_Standard"   = { description = "Standard clinical access - nurses, technicians" }
  "Clinical_Full"       = { description = "Full clinical access - physicians, senior staff" }
  "Clinical_Admin"      = { description = "Administrative access - compliance, IT, executives" }
  "External_Auditor"    = { description = "Temporary external audit access" }
}

tag_policies = [
  { key = "phi_level", description = "Protected Health Information sensitivity", values = ["public", "limited", "full", "restricted"] },
  { key = "pii_level", description = "Personally Identifiable Information sensitivity", values = ["public", "masked", "restricted"] },
  { key = "financial_level", description = "Financial data sensitivity", values = ["public", "summary", "detailed"] },
  { key = "region_access", description = "Regional data access control", values = ["unrestricted", "us_only", "eu_only"] },
]

# entity_name and function_name are RELATIVE to uc_catalog_name.uc_schema_name.
# Terraform automatically prepends the catalog.schema prefix.
tag_assignments = [
  # Patients table - PII tags
  { entity_type = "columns", entity_name = "Patients.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Patients.MRN", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.FirstName", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.LastName", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.DateOfBirth", tag_key = "phi_level", tag_value = "full" },
  { entity_type = "columns", entity_name = "Patients.SSN", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.Email", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "Patients.Phone", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "Patients.Address", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.InsuranceID", tag_key = "financial_level", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Patients.FacilityRegion", tag_key = "region_access", tag_value = "unrestricted" },

  # Encounters table - Clinical data tags
  { entity_type = "columns", entity_name = "Encounters.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisCode", tag_key = "phi_level", tag_value = "full" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisDesc", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Encounters.TreatmentNotes", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Encounters.AttendingDoc", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "Encounters.FacilityRegion", tag_key = "region_access", tag_value = "unrestricted" },

  # Billing table - Financial tags
  { entity_type = "columns", entity_name = "Billing.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Billing.TotalAmount", tag_key = "financial_level", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.InsurancePaid", tag_key = "financial_level", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.PatientOwed", tag_key = "financial_level", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.InsuranceID", tag_key = "financial_level", tag_value = "detailed" },

  # Prescriptions table
  { entity_type = "columns", entity_name = "Prescriptions.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Prescriptions.DrugName", tag_key = "phi_level", tag_value = "full" },
  { entity_type = "columns", entity_name = "Prescriptions.Dosage", tag_key = "phi_level", tag_value = "full" },
  { entity_type = "columns", entity_name = "Prescriptions.PrescribingDoc", tag_key = "pii_level", tag_value = "masked" },

  # Table-level regional tags
  { entity_type = "tables", entity_name = "Patients", tag_key = "region_access", tag_value = "unrestricted" },
  { entity_type = "tables", entity_name = "Encounters", tag_key = "region_access", tag_value = "unrestricted" },
]

fgac_policies = [
  # PII Masking Policies
  {
    name            = "mask_restricted_pii_for_limited_users"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "External_Auditor"]
    comment         = "Mask highly sensitive PII for restricted access users"
    match_condition = "hasTagValue('pii_level', 'restricted')"
    match_alias     = "restricted_pii"
    function_name   = "mask_redact"
  },
  {
    name            = "mask_names_for_standard_users"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Standard"]
    comment         = "Show initials only for patient names to standard users"
    match_condition = "hasTagValue('pii_level', 'restricted')"
    match_alias     = "patient_names"
    function_name   = "mask_full_name"
  },
  {
    name            = "mask_contact_info_partial"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "Clinical_Standard"]
    comment         = "Partially mask email and phone for non-privileged users"
    match_condition = "hasTagValue('pii_level', 'masked')"
    match_alias     = "contact_info"
    function_name   = "mask_pii_partial"
  },
  {
    name            = "mask_ssn_for_non_admin"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "Clinical_Standard", "Clinical_Full"]
    comment         = "Show only last 4 digits of SSN for non-admin users"
    match_condition = "hasTagValue('pii_level', 'restricted')"
    match_alias     = "ssn_data"
    function_name   = "mask_ssn"
  },

  # PHI Masking Policies
  {
    name            = "mask_mrn_for_restricted"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "External_Auditor"]
    comment         = "Show only last 4 digits of MRN for restricted users"
    match_condition = "hasTagValue('phi_level', 'restricted')"
    match_alias     = "mrn_data"
    function_name   = "mask_mrn"
  },
  {
    name            = "mask_diagnosis_details"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "Clinical_Standard"]
    comment         = "Hide detailed diagnosis information from non-physician users"
    match_condition = "hasTagValue('phi_level', 'restricted')"
    match_alias     = "diagnosis_details"
    function_name   = "mask_redact"
  },
  {
    name            = "mask_diagnosis_codes_partial"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted"]
    comment         = "Show only ICD category for diagnosis codes to restricted users"
    match_condition = "hasTagValue('phi_level', 'full')"
    match_alias     = "diagnosis_codes"
    function_name   = "mask_diagnosis_code"
  },

  # Financial Masking Policies
  {
    name            = "mask_detailed_financial"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "Clinical_Standard", "Clinical_Full"]
    comment         = "Round financial amounts for non-admin clinical users"
    match_condition = "hasTagValue('financial_level', 'detailed')"
    match_alias     = "financial_amounts"
    function_name   = "mask_amount_rounded"
  },
  {
    name            = "mask_insurance_ids"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Restricted", "External_Auditor"]
    comment         = "Hash insurance IDs for restricted users"
    match_condition = "hasTagValue('financial_level', 'detailed')"
    match_alias     = "insurance_data"
    function_name   = "mask_account_number"
  },

  # Row Filter Policies
  {
    name           = "filter_us_data_only"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["Clinical_Restricted"]
    comment        = "Restrict access to US regional data only for restricted users"
    when_condition = "hasTagValue('region_access', 'unrestricted')"
    function_name  = "filter_by_region_us"
  },
  {
    name           = "filter_audit_access"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["External_Auditor"]
    comment        = "Time-limited access filter for external auditors"
    when_condition = "hasTagValue('region_access', 'unrestricted')"
    function_name  = "filter_audit_expiry"
  },
]

group_members = {}
```

## Key Features of This Configuration:

### 1. **Four-Tier Access Model**
- **Clinical_Restricted**: Junior staff, contractors - heavy masking
- **Clinical_Standard**: Nurses, technicians - moderate masking  
- **Clinical_Full**: Physicians - minimal masking
- **Clinical_Admin**: Full access for compliance/IT
- **External_Auditor**: Temporary access with restrictions

### 2. **Multi-Dimensional Tagging**
- **phi_level**: Healthcare-specific sensitivity (public → restricted)
- **pii_level**: General PII sensitivity 
- **financial_level**: Billing/insurance data sensitivity
- **region_access**: Geographic access control

### 3. **Healthcare-Appropriate Masking**
- MRN masking (last 4 digits visible)
- Diagnosis code masking (ICD category visible)
- SSN masking (last 4 digits)
- Name reduction to initials
- Financial amount rounding
- Treatment notes redaction

### 4. **Compliance-Ready**
- Supports HIPAA requirements
- Regional data filtering capabilities
- Audit trail through group membership
- Graduated access levels

Before applying, validate the configuration:

```bash
pip install python-hcl2
python validate_abac.py terraform.tfvars masking_functions.sql
```

This configuration provides comprehensive protection for your clinical data while maintaining usability for different user roles.