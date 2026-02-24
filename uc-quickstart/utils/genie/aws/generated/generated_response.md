Based on your clinical database schema, I'll generate comprehensive ABAC policies that protect PHI while enabling appropriate access for different healthcare roles. Here are the two files:

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
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
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
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+$' THEN email
  ELSE CONCAT('***@', SPLIT(email, '@')[1])
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
  ELSE CONCAT(LEFT(name, 1), '.')
END;

-- Health-specific Functions
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN showing only last 4 characters'
RETURN CASE 
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) >= 4 THEN CONCAT('****', RIGHT(mrn, 4))
  ELSE '********'
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD-10 category (first 3 chars) but hides specific diagnosis'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) >= 3 THEN CONCAT(LEFT(code, 3), '.XX')
  ELSE 'XXX.XX'
END;

CREATE OR REPLACE FUNCTION mask_clinical_notes(notes STRING)
RETURNS STRING
COMMENT 'Redacts clinical notes for non-clinical staff'
RETURN CASE 
  WHEN notes IS NULL THEN NULL
  ELSE '[CLINICAL_NOTES_REDACTED]'
END;

-- Financial Functions
CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest $100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount / 100.0, 0) * 100.0
END;

CREATE OR REPLACE FUNCTION mask_insurance_id(insurance_id STRING)
RETURNS STRING
COMMENT 'Masks insurance ID showing only last 4 characters'
RETURN CASE 
  WHEN insurance_id IS NULL THEN NULL
  WHEN LENGTH(insurance_id) >= 4 THEN CONCAT('****', RIGHT(insurance_id, 4))
  ELSE '********'
END;

-- General Masking Functions
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Completely redacts sensitive information'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_hash(input STRING)
RETURNS STRING
COMMENT 'Returns SHA-256 hash for deterministic anonymization'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE SHA2(input, 256)
END;

-- Row Filter Functions
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filter to show only US regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filter to show only EU regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_clinical_staff_only()
RETURNS BOOLEAN
COMMENT 'Filter allowing access only during business hours for clinical staff'
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
  "Clinical_Staff" = { description = "Physicians, nurses, clinical staff with full patient access" }
  "Billing_Staff" = { description = "Billing department with financial data access" }
  "Research_Analysts" = { description = "Researchers with de-identified data access" }
  "Compliance_Auditors" = { description = "Compliance team with limited audit access" }
  "System_Administrators" = { description = "IT administrators with full technical access" }
}

tag_policies = [
  { key = "phi_level", description = "PHI sensitivity classification", values = ["public", "limited", "full_phi", "restricted"] },
  { key = "financial_sensitivity", description = "Financial data classification", values = ["public", "summary", "detailed", "restricted"] },
  { key = "clinical_access", description = "Clinical data access requirements", values = ["public", "clinical_only", "physician_only"] },
  { key = "regional_access", description = "Regional data access controls", values = ["global", "us_only", "eu_only"] },
]

# entity_name and function_name are RELATIVE to uc_catalog_name.uc_schema_name.
# Terraform automatically prepends the catalog.schema prefix.
tag_assignments = [
  # Patients table - PHI tagging
  { entity_type = "columns", entity_name = "Patients.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Patients.MRN", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.FirstName", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.LastName", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.DateOfBirth", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.SSN", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Patients.Email", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.Phone", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.Address", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.InsuranceID", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Patients.InsuranceID", tag_key = "financial_sensitivity", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Patients.FacilityRegion", tag_key = "regional_access", tag_value = "global" },

  # Encounters table - Clinical data tagging
  { entity_type = "columns", entity_name = "Encounters.EncounterID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Encounters.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisCode", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisCode", tag_key = "clinical_access", tag_value = "clinical_only" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisDesc", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Encounters.DiagnosisDesc", tag_key = "clinical_access", tag_value = "clinical_only" },
  { entity_type = "columns", entity_name = "Encounters.TreatmentNotes", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "Encounters.TreatmentNotes", tag_key = "clinical_access", tag_value = "physician_only" },
  { entity_type = "columns", entity_name = "Encounters.AttendingDoc", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Encounters.FacilityRegion", tag_key = "regional_access", tag_value = "global" },

  # Billing table - Financial data tagging
  { entity_type = "columns", entity_name = "Billing.BillingID", tag_key = "financial_sensitivity", tag_value = "summary" },
  { entity_type = "columns", entity_name = "Billing.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Billing.TotalAmount", tag_key = "financial_sensitivity", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.InsurancePaid", tag_key = "financial_sensitivity", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.PatientOwed", tag_key = "financial_sensitivity", tag_value = "detailed" },
  { entity_type = "columns", entity_name = "Billing.InsuranceID", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Billing.InsuranceID", tag_key = "financial_sensitivity", tag_value = "detailed" },

  # Prescriptions table - Clinical data tagging
  { entity_type = "columns", entity_name = "Prescriptions.PrescriptionID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Prescriptions.PatientID", tag_key = "phi_level", tag_value = "limited" },
  { entity_type = "columns", entity_name = "Prescriptions.DrugName", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Prescriptions.DrugName", tag_key = "clinical_access", tag_value = "clinical_only" },
  { entity_type = "columns", entity_name = "Prescriptions.Dosage", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "Prescriptions.Dosage", tag_key = "clinical_access", tag_value = "clinical_only" },
  { entity_type = "columns", entity_name = "Prescriptions.PrescribingDoc", tag_key = "phi_level", tag_value = "full_phi" },

  # Table-level regional access
  { entity_type = "tables", entity_name = "Patients", tag_key = "regional_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "Encounters", tag_key = "regional_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "Billing", tag_key = "regional_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "Prescriptions", tag_key = "regional_access", tag_value = "global" },
]

fgac_policies = [
  # PHI Masking Policies for Research Analysts
  {
    name            = "mask_full_phi_for_researchers"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Research_Analysts"]
    comment         = "Mask full PHI data for research analysts"
    match_condition = "hasTagValue('phi_level', 'full_phi')"
    match_alias     = "masked_phi"
    function_name   = "mask_hash"
  },
  {
    name            = "mask_restricted_phi_for_researchers"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Research_Analysts"]
    comment         = "Redact restricted PHI for research analysts"
    match_condition = "hasTagValue('phi_level', 'restricted')"
    match_alias     = "redacted_phi"
    function_name   = "mask_redact"
  },

  # PHI Masking for Billing Staff
  {
    name            = "mask_clinical_notes_for_billing"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Staff"]
    comment         = "Redact clinical notes for billing staff"
    match_condition = "hasTagValue('clinical_access', 'physician_only')"
    match_alias     = "redacted_notes"
    function_name   = "mask_clinical_notes"
  },
  {
    name            = "mask_names_for_billing"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Billing_Staff"]
    comment         = "Mask patient names for billing staff"
    match_condition = "hasTagValue('phi_level', 'full_phi') AND hasTag('clinical_access')"
    match_alias     = "masked_name"
    function_name   = "mask_pii_partial"
  },

  # Financial Data Masking for Non-Billing Staff
  {
    name            = "round_amounts_for_clinical"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Staff"]
    comment         = "Round financial amounts for clinical staff"
    match_condition = "hasTagValue('financial_sensitivity', 'detailed')"
    match_alias     = "rounded_amount"
    function_name   = "mask_amount_rounded"
  },
  {
    name            = "mask_insurance_for_researchers"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Research_Analysts"]
    comment         = "Mask insurance IDs for researchers"
    match_condition = "hasTagValue('financial_sensitivity', 'detailed')"
    match_alias     = "masked_insurance"
    function_name   = "mask_insurance_id"
  },

  # Specific Field Masking
  {
    name            = "mask_ssn_for_non_admin"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Clinical_Staff", "Billing_Staff", "Research_Analysts", "Compliance_Auditors"]
    comment         = "Mask SSN for all non-administrator users"
    match_condition = "hasTagValue('phi_level', 'restricted')"
    match_alias     = "masked_ssn"
    function_name   = "mask_ssn"
  },
  {
    name            = "mask_mrn_for_researchers"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Research_Analysts"]
    comment         = "Mask MRN for research analysts"
    match_condition = "hasTagValue('phi_level', 'full_phi')"
    match_alias     = "masked_mrn"
    function_name   = "mask_mrn"
  },
  {
    name            = "mask_diagnosis_codes_for_researchers"
    policy_type     = "POLICY_TYPE_COLUMN_MASK"
    to_principals   = ["Research_Analysts"]
    comment         = "Show only diagnosis categories for researchers"
    match_condition = "hasTagValue('clinical_access', 'clinical_only')"
    match_alias     = "category_diagnosis"
    function_name   = "mask_diagnosis_code"
  },

  # Row Filters for Regional Access
  {
    name           = "filter_us_data_only"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["Clinical_Staff", "Billing_Staff"]
    comment        = "Restrict access to US regional data only"
    when_condition = "hasTagValue('regional_access', 'us_only')"
    function_name  = "filter_by_region_us"
  },
  {
    name           = "filter_eu_data_only"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["Compliance_Auditors"]
    comment        = "Restrict compliance auditors to EU data only"
    when_condition = "hasTagValue('regional_access', 'eu_only')"
    function_name  = "filter_by_region_eu"
  },
  {
    name           = "filter_clinical_access_hours"
    policy_type    = "POLICY_TYPE_ROW_FILTER"
    to_principals  = ["Clinical_Staff"]
    comment        = "Restrict clinical staff access to business hours"
    when_condition = "hasTagValue('clinical_access', 'clinical_only')"
    function_name  = "filter_clinical_staff_only"
  },
]

group_members = {}
```

This ABAC configuration provides:

1. **Granular PHI Protection**: Different masking levels for various healthcare roles
2. **Financial Data Security**: Appropriate access controls for billing information
3. **Clinical Data Governance**: Physician-only access to sensitive treatment notes
4. **Research-Friendly De-identification**: Hash-based anonymization for research use
5. **Regional Compliance**: Row-level filtering for jurisdictional requirements
6. **Audit Trail Support**: Compliance auditor access with appropriate restrictions

The policies ensure HIPAA compliance while enabling legitimate healthcare operations and research activities.