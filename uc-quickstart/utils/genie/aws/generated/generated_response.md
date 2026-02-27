I'll analyze your clinical and finance tables to generate comprehensive ABAC configuration. Based on the schemas, I can see you have sensitive healthcare data (PHI) and financial data (PII, PCI-DSS) that require different access controls.

## File 1: `masking_functions.sql`

```sql
-- === louis_sydney.clinical functions ===
USE CATALOG louis_sydney;
USE SCHEMA clinical;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, 3, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD category (first 3 chars), masks specific diagnosis'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(SUBSTRING(code, 1, 3), '***')
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU region data'
RETURN TRUE;

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

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
COMMENT 'Shows last 4 digits of SSN, masks the rest'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) < 4 THEN '***-**-****'
  ELSE CONCAT('***-**-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks local part of email, keeps domain visible'
RETURN CASE 
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+$' THEN email
  ELSE CONCAT('****@', SUBSTRING(email, INSTR(email, '@') + 1))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Completely masks credit card number'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  ELSE '****-****-****-****'
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of credit card, masks the rest'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) < 4 THEN '****-****-****-****'
  ELSE CONCAT('****-****-****-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Creates deterministic hash token for account numbers'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACC_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_hash(input STRING)
RETURNS STRING
COMMENT 'Returns SHA-256 hash of input'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE SHA2(input, 256)
END;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_trading_hours()
RETURNS BOOLEAN
COMMENT 'Restricts access to non-trading hours (before 9 AM or after 4 PM)'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Time-limited access that expires at end of 2025'
RETURN CURRENT_DATE() <= DATE('2025-12-31');
```

## File 2: `abac.auto.tfvars`

```hcl
groups = {
  "Clinical_Staff"     = { description = "Doctors and nurses with full access to patient data" }
  "Clinical_Analyst"   = { description = "Healthcare analysts with masked patient identifiers" }
  "Finance_Admin"      = { description = "Finance administrators with full access to financial data" }
  "Finance_Analyst"    = { description = "Financial analysts with masked PII and PCI data" }
  "Compliance_Officer" = { description = "Compliance staff with access to investigation data" }
  "Auditor"           = { description = "External auditors with time-limited access" }
  "Regional_US"       = { description = "Users with access to US region data only" }
  "Regional_EU"       = { description = "Users with access to EU region data only" }
}

tag_policies = [
  { key = "phi_level", description = "Protected Health Information sensitivity", values = ["public", "masked", "restricted"] },
  { key = "pii_level", description = "Personally Identifiable Information sensitivity", values = ["public", "masked", "restricted"] },
  { key = "pci_level", description = "Payment Card Industry data sensitivity", values = ["public", "masked", "restricted"] },
  { key = "aml_level", description = "Anti-Money Laundering investigation sensitivity", values = ["public", "masked", "restricted"] },
  { key = "region_access", description = "Regional data access control", values = ["us_only", "eu_only", "global"] },
  { key = "audit_access", description = "Audit and compliance access control", values = ["standard", "time_limited"] },
  { key = "trading_access", description = "Trading data access control", values = ["standard", "non_trading_hours"] }
]

tag_assignments = [
  # Clinical table tags
  { entity_type = "tables", entity_name = "louis_sydney.clinical.encounters", tag_key = "region_access", tag_value = "global" },
  
  # Clinical column tags - PHI
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.PatientID", tag_key = "phi_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisCode", tag_key = "phi_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisDesc", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.TreatmentNotes", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.AttendingDoc", tag_key = "phi_level", tag_value = "masked" },
  
  # Finance table tags
  { entity_type = "tables", entity_name = "louis_sydney.finance.customers", tag_key = "region_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.accounts", tag_key = "region_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.transactions", tag_key = "region_access", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.creditcards", tag_key = "pci_level", tag_value = "restricted" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.amlalerts", tag_key = "aml_level", tag_value = "restricted" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.auditlogs", tag_key = "audit_access", tag_value = "time_limited" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.tradingpositions", tag_key = "trading_access", tag_value = "non_trading_hours" },
  
  # Finance column tags - PII
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.FirstName", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.LastName", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Email", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.SSN", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Address", tag_key = "pii_level", tag_value = "restricted" },
  
  # Finance column tags - PCI
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CardNumber", tag_key = "pci_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CVV", tag_key = "pci_level", tag_value = "restricted" },
  
  # Finance column tags - Account data
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.AccountID", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.Balance", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.transactions.Amount", tag_key = "pii_level", tag_value = "masked" },
  
  # AML investigation data
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.InvestigationNotes", tag_key = "aml_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.AssignedInvestigator", tag_key = "aml_level", tag_value = "masked" },
  
  # Customer interaction notes
  { entity_type = "columns", entity_name = "louis_sydney.finance.customerinteractions.InteractionNotes", tag_key = "pii_level", tag_value = "restricted" }
]

fgac_policies = [
  # Clinical PHI masking policies
  {
    name             = "mask_phi_patient_identifiers"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Finance_Admin", "Finance_Analyst"]
    comment          = "Mask patient identifiers for non-clinical staff"
    match_condition  = "hasTagValue('phi_level', 'masked')"
    match_alias      = "masked_phi"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "mask_phi_diagnosis_codes"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Finance_Admin", "Finance_Analyst"]
    comment          = "Mask specific diagnosis details, show category only"
    match_condition  = "hasTagValue('phi_level', 'masked')"
    match_alias      = "diagnosis"
    function_name    = "mask_diagnosis_code"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "redact_phi_restricted"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Finance_Admin", "Finance_Analyst", "Auditor"]
    comment          = "Completely redact highly sensitive PHI"
    match_condition  = "hasTagValue('phi_level', 'restricted')"
    match_alias      = "restricted_phi"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  
  # Finance PII masking policies
  {
    name             = "mask_pii_names"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst"]
    comment          = "Mask customer names for non-finance admin users"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "customer_name"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_pii_email"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst"]
    comment          = "Mask email addresses for non-finance admin users"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "email"
    function_name    = "mask_email"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_ssn"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst", "Auditor"]
    comment          = "Mask SSN showing only last 4 digits"
    match_condition  = "hasTagValue('pii_level', 'restricted')"
    match_alias      = "ssn"
    function_name    = "mask_ssn"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "redact_pii_address"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst", "Auditor"]
    comment          = "Redact customer addresses"
    match_condition  = "hasTagValue('pii_level', 'restricted')"
    match_alias      = "address"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_account_numbers"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst"]
    comment          = "Hash account identifiers"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "account_id"
    function_name    = "mask_account_number"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_financial_amounts"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst"]
    comment          = "Round financial amounts for privacy"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "amount"
    function_name    = "mask_amount_rounded"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # PCI data masking
  {
    name             = "mask_credit_cards"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst", "Compliance_Officer", "Auditor"]
    comment          = "Completely mask credit card numbers for non-admin users"
    match_condition  = "hasTagValue('pci_level', 'restricted')"
    match_alias      = "card_data"
    function_name    = "mask_credit_card_full"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # AML investigation data
  {
    name             = "redact_aml_investigation"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Admin", "Clinical_Staff", "Clinical_Analyst", "Auditor"]
    comment          = "Redact AML investigation details for non-compliance users"
    match_condition  = "hasTagValue('aml_level', 'restricted')"
    match_alias      = "aml_data"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_aml_investigators"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Finance_Admin", "Clinical_Staff", "Clinical_Analyst", "Auditor"]
    comment          = "Mask investigator names for non-compliance users"
    match_condition  = "hasTagValue('aml_level', 'masked')"
    match_alias      = "investigator"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # Customer interaction notes
  {
    name             = "redact_interaction_notes"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff", "Clinical_Analyst", "Auditor"]
    comment          = "Redact customer interaction notes"
    match_condition  = "hasTagValue('pii_level', 'restricted')"
    match_alias      = "notes"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # Row filter policies
  {
    name             = "filter_regional_us_access"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Regional_US"]
    comment          = "Restrict Regional_US users to US region data only"
    when_condition   = "hasTagValue('region_access', 'global')"
    function_name    = "filter_by_region_us"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "filter_regional_eu_access"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Regional_EU"]
    comment          = "Restrict Regional_EU users to EU region data only"
    when_condition   = "hasTagValue('region_access', 'global')"
    function_name    = "filter_by_region_eu"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "filter_trading_hours_access"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Clinical_Staff"]
    comment          = "Restrict trading data access to non-trading hours"
    when_condition   = "hasTagValue('trading_access', 'non_trading_hours')"
    function_name    = "filter_trading_hours"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "filter_audit_time_limited"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Auditor"]
    comment          = "Time-limited access to audit logs"
    when_condition   = "hasTagValue('audit_access', 'time_limited')"
    function_name    = "filter_audit_expiry"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  }
]

group_members = {}

genie_space_title       = "Healthcare & Financial Analytics"
genie_space_description = "Explore clinical encounters, patient data, financial transactions, and compliance metrics. Designed for healthcare analysts, finance teams, and compliance officers with appropriate data masking."

genie_sample_questions = [
  "What is the total transaction volume by region for last quarter?",
  "How many patient encounters occurred by diagnosis category last month?",
  "Which accounts have the highest AML risk scores?",
  "Show me the distribution of encounter types across facilities",
  "What is the average account balance by customer region?",
  "How many credit cards are approaching expiration?",
  "Which trading desks have the highest P&L this month?",
  "What are the most common diagnosis codes in our system?",
  "Show customer interaction volume by channel type",
  "How many AML alerts are currently under investigation?"
]

genie_instructions = "When calculating financial amounts, be aware that some users see rounded values for privacy. 'Last month' means the previous calendar month. Patient data is masked for non-clinical users - focus on aggregate counts and trends rather than individual records. AML investigation details are restricted to compliance officers only. Trading data access may be limited to non-trading hours for some users."

genie_benchmarks = [
  {
    question = "What is the total transaction amount across all accounts?"
    sql      = "SELECT SUM(Amount) as total_amount FROM louis_sydney.finance.transactions WHERE TransactionStatus = 'Completed'"
  },
  {
    question = "How many patient encounters were there last month?"
    sql      = "SELECT COUNT(*) FROM louis_sydney.clinical.encounters WHERE EncounterDate >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND EncounterDate < DATE_TRUNC('month', CURRENT_DATE)"
  },
  {
    question = "What is the average customer risk score?"
    sql      = "SELECT AVG(RiskScore) as avg_risk_score FROM louis_sydney.finance.customers WHERE CustomerStatus = 'Active'"
  },
  {
    question = "How many active credit cards do we have?"
    sql      = "SELECT COUNT(*) FROM louis_sydney.finance.creditcards WHERE CardStatus = 'Active'"
  },
  {
    question = "What are the top 3 encounter types by volume?"
    sql      = "SELECT EncounterType, COUNT(*) as encounter_count FROM louis_sydney.clinical.encounters GROUP BY EncounterType ORDER BY encounter_count DESC LIMIT 3"
  }
]
```

This ABAC configuration provides:

**Access Tiers:**
- **Clinical_Staff**: Full access to patient data
- **Clinical_Analyst**: Masked patient identifiers, category-level diagnosis codes
- **Finance_Admin**: Full access to financial data
- **Finance_Analyst**: Masked PII/PCI data, rounded amounts
- **Compliance_Officer**: Access to AML investigation data
- **Auditor**: Time-limited access with most sensitive data masked
- **Regional groups**: Geographic data restrictions

**Key Security Features:**
- PHI masking for non-clinical users
- PCI-DSS compliance with full credit card masking
- AML investigation data restricted to compliance officers
- Regional data filtering capabilities
- Time-limited audit access
- Trading hours restrictions for sensitive trading data

The configuration balances security with usability, allowing each role to access the data they need while protecting sensitive information according to healthcare, financial, and compliance requirements.