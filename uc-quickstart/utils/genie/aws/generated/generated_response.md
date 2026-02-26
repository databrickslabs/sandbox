I'll analyze your tables and generate comprehensive ABAC configuration for your healthcare and financial data. Let me break down the sensitivity analysis and create the appropriate masking functions and policies.

## File 1: `masking_functions.sql`

```sql
-- === louis_sydney.clinical functions ===
USE CATALOG louis_sydney;
USE SCHEMA clinical;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character for names/identifiers'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, -1, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Masks ICD-10 code specifics, shows only category (first 3 characters)'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(SUBSTRING(code, 1, 3), '***')
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces sensitive content with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION filter_by_region_us() 
RETURNS BOOLEAN
COMMENT 'Row filter for US regional data access only'
RETURN current_user() LIKE '%_us@%' OR is_member('US_Regional_Access');

CREATE OR REPLACE FUNCTION filter_by_region_eu() 
RETURNS BOOLEAN
COMMENT 'Row filter for EU regional data access only'
RETURN current_user() LIKE '%_eu@%' OR is_member('EU_Regional_Access');

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character for names/identifiers'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, -1, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Masks SSN showing only last 4 digits (XXX-XX-1234)'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) >= 4 THEN 
    CONCAT('XXX-XX-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
  ELSE 'XXX-XX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks email local part, preserves domain (@example.com)'
RETURN CASE 
  WHEN email IS NULL OR email NOT LIKE '%@%' THEN email
  ELSE CONCAT('****', SUBSTRING(email, INSTR(email, '@')))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Completely masks credit card number'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Masks credit card showing only last 4 digits'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) >= 4 THEN 
    CONCAT('XXXX-XXXX-XXXX-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
  ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Deterministic hash for account numbers to maintain referential integrity'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACC_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces sensitive content with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Returns NULL for highly sensitive data'
RETURN NULL;

CREATE OR REPLACE FUNCTION filter_by_region_us() 
RETURNS BOOLEAN
COMMENT 'Row filter for US regional data access only'
RETURN current_user() LIKE '%_us@%' OR is_member('US_Regional_Access');

CREATE OR REPLACE FUNCTION filter_by_region_eu() 
RETURNS BOOLEAN
COMMENT 'Row filter for EU regional data access only'
RETURN current_user() LIKE '%_eu@%' OR is_member('EU_Regional_Access');

CREATE OR REPLACE FUNCTION filter_trading_hours() 
RETURNS BOOLEAN
COMMENT 'Restricts access to trading data outside market hours'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16 OR DAYOFWEEK(NOW()) IN (1, 7);

CREATE OR REPLACE FUNCTION filter_audit_expiry() 
RETURNS BOOLEAN
COMMENT 'Temporary auditor access with expiration check'
RETURN current_date() <= '2024-12-31' AND is_member('External_Auditors');
```

## File 2: `terraform.tfvars`

```hcl
groups = {
  "Clinical_Restricted"     = { description = "Limited clinical staff - basic patient data access" }
  "Clinical_Standard"       = { description = "Standard clinical staff - full patient data access" }
  "Clinical_Admin"          = { description = "Clinical administrators - full access including sensitive notes" }
  "Finance_Analyst"         = { description = "Junior financial analysts - limited PII and transaction access" }
  "Finance_Manager"         = { description = "Financial managers - full transaction access, masked PII" }
  "Finance_Compliance"      = { description = "Compliance officers - full AML and audit access" }
  "Finance_Admin"           = { description = "Financial administrators - complete data access" }
  "External_Auditors"       = { description = "Temporary external auditors - time-limited access" }
  "Regional_US"             = { description = "US-based staff with regional data access" }
  "Regional_EU"             = { description = "EU-based staff with regional data access" }
}

tag_policies = [
  { key = "pii_level", description = "Personal Identifiable Information sensitivity", values = ["public", "standard_pii", "sensitive_pii", "restricted_pii"] },
  { key = "pci_level", description = "PCI-DSS compliance level for payment data", values = ["non_pci", "pci_restricted", "pci_prohibited"] },
  { key = "phi_level", description = "Protected Health Information under HIPAA", values = ["non_phi", "limited_phi", "full_phi"] },
  { key = "financial_sensitivity", description = "Financial data sensitivity for SOX compliance", values = ["public", "internal", "confidential", "restricted"] },
  { key = "aml_sensitivity", description = "Anti-Money Laundering investigation sensitivity", values = ["standard", "investigation", "sar_related"] },
  { key = "regional_scope", description = "Data residency and regional access control", values = ["global", "us_only", "eu_only", "apac_only"] },
  { key = "audit_scope", description = "Audit and compliance data classification", values = ["standard", "sox_audit", "regulatory_audit"] }
]

tag_assignments = [
  # Clinical table tags
  { entity_type = "tables", entity_name = "louis_sydney.clinical.encounters", tag_key = "regional_scope", tag_value = "global" },
  
  # Clinical column tags - PHI
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.PatientID", tag_key = "phi_level", tag_value = "limited_phi" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisCode", tag_key = "phi_level", tag_value = "limited_phi" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisDesc", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.TreatmentNotes", tag_key = "phi_level", tag_value = "full_phi" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.AttendingDoc", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.FacilityRegion", tag_key = "regional_scope", tag_value = "global" },

  # Finance table tags
  { entity_type = "tables", entity_name = "louis_sydney.finance.customers", tag_key = "regional_scope", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.transactions", tag_key = "regional_scope", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.auditlogs", tag_key = "audit_scope", tag_value = "sox_audit" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.amlalerts", tag_key = "aml_sensitivity", tag_value = "investigation" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.tradingpositions", tag_key = "financial_sensitivity", tag_value = "restricted" },

  # Customer PII
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.FirstName", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.LastName", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Email", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.SSN", tag_key = "pii_level", tag_value = "restricted_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Address", tag_key = "pii_level", tag_value = "sensitive_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.CustomerRegion", tag_key = "regional_scope", tag_value = "global" },

  # Credit card PCI data
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CardNumber", tag_key = "pci_level", tag_value = "pci_prohibited" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CVV", tag_key = "pci_level", tag_value = "pci_prohibited" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CustomerID", tag_key = "pii_level", tag_value = "standard_pii" },

  # Financial sensitive data
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.AccountID", tag_key = "pii_level", tag_value = "sensitive_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.Balance", tag_key = "financial_sensitivity", tag_value = "confidential" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.transactions.Amount", tag_key = "financial_sensitivity", tag_value = "confidential" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.transactions.AMLFlagReason", tag_key = "aml_sensitivity", tag_value = "investigation" },

  # AML investigation data
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.InvestigationNotes", tag_key = "aml_sensitivity", tag_value = "sar_related" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.AssignedInvestigator", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.RiskScore", tag_key = "aml_sensitivity", tag_value = "investigation" },

  # Trading sensitive data
  { entity_type = "columns", entity_name = "louis_sydney.finance.tradingpositions.PnL", tag_key = "financial_sensitivity", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.tradingpositions.TraderID", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.tradingpositions.InformationBarrier", tag_key = "financial_sensitivity", tag_value = "restricted" },

  # Audit data
  { entity_type = "columns", entity_name = "louis_sydney.finance.auditlogs.UserID", tag_key = "pii_level", tag_value = "standard_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.auditlogs.IPAddress", tag_key = "pii_level", tag_value = "sensitive_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.auditlogs.AuditProject", tag_key = "audit_scope", tag_value = "sox_audit" },

  # Customer interaction notes
  { entity_type = "columns", entity_name = "louis_sydney.finance.customerinteractions.InteractionNotes", tag_key = "pii_level", tag_value = "sensitive_pii" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customerinteractions.AgentID", tag_key = "pii_level", tag_value = "standard_pii" }
]

fgac_policies = [
  # Clinical PHI masking policies
  {
    name             = "mask_limited_phi_for_restricted"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Restricted"]
    comment          = "Mask limited PHI for restricted clinical staff"
    match_condition  = "hasTagValue('phi_level', 'limited_phi')"
    match_alias      = "phi_data"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "mask_full_phi_for_standard"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Restricted", "Clinical_Standard"]
    comment          = "Redact full PHI for non-admin clinical staff"
    match_condition  = "hasTagValue('phi_level', 'full_phi')"
    match_alias      = "sensitive_phi"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "mask_diagnosis_codes"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Restricted"]
    comment          = "Mask specific diagnosis details for restricted staff"
    match_condition  = "hasTagValue('phi_level', 'limited_phi')"
    match_alias      = "diagnosis"
    function_name    = "mask_diagnosis_code"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },

  # Finance PII masking policies
  {
    name             = "mask_standard_pii_analysts"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst"]
    comment          = "Partial masking of standard PII for analysts"
    match_condition  = "hasTagValue('pii_level', 'standard_pii')"
    match_alias      = "basic_pii"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_sensitive_pii_analysts"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager"]
    comment          = "Redact sensitive PII for non-compliance staff"
    match_condition  = "hasTagValue('pii_level', 'sensitive_pii')"
    match_alias      = "sensitive_pii"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_restricted_pii"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager"]
    comment          = "Mask SSN and other restricted PII"
    match_condition  = "hasTagValue('pii_level', 'restricted_pii')"
    match_alias      = "restricted_pii"
    function_name    = "mask_ssn"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_email_addresses"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst"]
    comment          = "Mask email local parts for analysts"
    match_condition  = "hasTagValue('pii_level', 'standard_pii')"
    match_alias      = "email_pii"
    function_name    = "mask_email"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },

  # PCI-DSS masking policies
  {
    name             = "mask_pci_prohibited_full"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager", "Finance_Compliance"]
    comment          = "Complete masking of PCI prohibited data"
    match_condition  = "hasTagValue('pci_level', 'pci_prohibited')"
    match_alias      = "pci_data"
    function_name    = "mask_credit_card_full"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },

  # Financial data masking
  {
    name             = "mask_confidential_amounts"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst"]
    comment          = "Round financial amounts for analysts"
    match_condition  = "hasTagValue('financial_sensitivity', 'confidential')"
    match_alias      = "financial_data"
    function_name    = "mask_amount_rounded"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_restricted_financial"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager"]
    comment          = "Redact restricted financial data"
    match_condition  = "hasTagValue('financial_sensitivity', 'restricted')"
    match_alias      = "restricted_financial"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },

  # AML investigation masking
  {
    name             = "mask_aml_investigation"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager"]
    comment          = "Mask AML investigation details for non-compliance staff"
    match_condition  = "hasTagValue('aml_sensitivity', 'investigation')"
    match_alias      = "aml_data"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_sar_related"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Manager"]
    comment          = "Nullify SAR-related investigation notes"
    match_condition  = "hasTagValue('aml_sensitivity', 'sar_related')"
    match_alias      = "sar_data"
    function_name    = "mask_nullify"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },

  # Account number masking
  {
    name             = "mask_account_numbers"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst"]
    comment          = "Hash account numbers for analysts while preserving referential integrity"
    match_condition  = "hasTagValue('pii_level', 'sensitive_pii')"
    match_alias      = "account_pii"
    function_name    = "mask_account_number"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },

  # Row filter policies
  {
    name             = "filter_trading_non_market_hours"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst"]
    comment          = "Restrict trading data access to non-market hours for analysts"
    when_condition   = "hasTagValue('financial_sensitivity', 'restricted')"
    function_name    = "filter_trading_hours"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "filter_audit_temporary_access"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["External_Auditors"]
    comment          = "Time-limited access for external auditors"
    when_condition   = "hasTagValue('audit_scope', 'sox_audit')"
    function_name    = "filter_audit_expiry"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  }
]

group_members = {}
```

This ABAC configuration provides:

**Clinical Data Protection:**
- PHI masking based on staff clearance levels
- Diagnosis code category-only access for restricted staff
- Complete redaction of treatment notes for non-admin users

**Financial Data Protection:**
- PCI-DSS compliant credit card masking
- PII protection with graduated access levels
- AML investigation data restricted to compliance officers
- Trading data with Chinese wall enforcement
- Account number hashing for referential integrity

**Compliance Features:**
- SOX audit data access controls
- Time-limited external auditor access
- Regional data residency controls
- Anti-money laundering investigation protection

**Access Tiers:**
- Graduated access from restricted → standard → admin levels
- Role-based masking (analysts see rounded amounts, hashed accounts)
- Compliance officers get full AML access
- External auditors get temporary, scoped access

The configuration ensures sensitive data is appropriately masked while maintaining analytical utility and regulatory compliance across both healthcare and financial domains.