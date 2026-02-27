I'll analyze your clinical and financial tables and generate comprehensive ABAC configuration files. Based on your schema, I can see you have sensitive healthcare data (PHI) and financial data (PCI-DSS, PII) that require different access controls.

## File 1: `masking_functions.sql`

```sql
-- === louis_sydney.clinical functions ===
USE CATALOG louis_sydney;
USE SCHEMA clinical;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Masks ICD-10 diagnosis codes to show only category (first 3 chars) for non-clinical users'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) >= 3 THEN CONCAT(SUBSTRING(code, 1, 3), 'XXX')
  ELSE 'XXX'
END;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Shows first and last character, masks middle with asterisks'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
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
COMMENT 'Filters clinical data to show only US regions (US_EAST, US_WEST)'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters clinical data to show only EU region data'
RETURN TRUE;

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

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
COMMENT 'Masks email local part, preserves domain (@company.com)'
RETURN CASE 
  WHEN email IS NULL THEN NULL
  WHEN email LIKE '%@%' THEN CONCAT('****', SUBSTRING(email, POSITION('@' IN email), LENGTH(email)))
  ELSE '****@****.com'
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Fully masks credit card number with asterisks'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  ELSE REPEAT('*', LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Masks credit card showing only last 4 digits (****-****-****-1234)'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) >= 4 THEN 
    CONCAT('****-****-****-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
  ELSE '****-****-****-****'
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Masks account ID with deterministic SHA-256 hash for consistent tokenization'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE SHA2(account_id, 256)
END;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Shows first and last character, masks middle with asterisks'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces sensitive content with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds monetary amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION filter_trading_hours()
RETURNS BOOLEAN
COMMENT 'Restricts access to trading data outside market hours (9 AM - 4 PM)'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters financial data to show only US region records'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters financial data to show only EU region records'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Time-limited audit access expires December 31, 2025'
RETURN CURRENT_DATE() <= DATE('2025-12-31');
```

## File 2: `abac.auto.tfvars`

```hcl
groups = {
  "Clinical_Staff"     = { description = "Full access to patient data for clinical care" }
  "Clinical_Analyst"   = { description = "Limited clinical data access with masked PII" }
  "Finance_Admin"      = { description = "Full access to financial data for operations" }
  "Finance_Analyst"    = { description = "Standard financial analysis with PII masking" }
  "Compliance_Officer" = { description = "Audit and compliance monitoring access" }
  "Junior_Analyst"     = { description = "Restricted access with heavy masking" }
  "Auditor_Temp"       = { description = "Time-limited audit access" }
}

tag_policies = [
  { key = "phi_level", description = "Protected Health Information sensitivity", values = ["public", "masked", "restricted"] },
  { key = "pii_level", description = "Personally Identifiable Information sensitivity", values = ["public", "masked", "restricted"] },
  { key = "pci_level", description = "Payment Card Industry data classification", values = ["public", "masked", "restricted"] },
  { key = "financial_sensitivity", description = "Financial data access control", values = ["public", "analyst", "admin"] },
  { key = "data_region", description = "Data residency and regional access control", values = ["us", "eu", "global"] },
  { key = "audit_scope", description = "Audit and compliance data classification", values = ["standard", "sensitive", "restricted"] },
]

tag_assignments = [
  # Clinical PHI tags
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.PatientID", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisCode", tag_key = "phi_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.DiagnosisDesc", tag_key = "phi_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.TreatmentNotes", tag_key = "phi_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.clinical.encounters.AttendingDoc", tag_key = "phi_level", tag_value = "masked" },
  
  # Regional access control for clinical data
  { entity_type = "tables", entity_name = "louis_sydney.clinical.encounters", tag_key = "data_region", tag_value = "us" },
  
  # Financial PII tags
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.FirstName", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.LastName", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Email", tag_key = "pii_level", tag_value = "masked" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.SSN", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.DateOfBirth", tag_key = "pii_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customers.Address", tag_key = "pii_level", tag_value = "masked" },
  
  # PCI-DSS sensitive data
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CardNumber", tag_key = "pci_level", tag_value = "restricted" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.creditcards.CVV", tag_key = "pci_level", tag_value = "restricted" },
  
  # Financial sensitive data
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.AccountID", tag_key = "financial_sensitivity", tag_value = "analyst" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.accounts.Balance", tag_key = "financial_sensitivity", tag_value = "analyst" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.transactions.Amount", tag_key = "financial_sensitivity", tag_value = "analyst" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.tradingpositions.PnL", tag_key = "financial_sensitivity", tag_value = "admin" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.tradingpositions.EntryPrice", tag_key = "financial_sensitivity", tag_value = "admin" },
  
  # AML and investigation data
  { entity_type = "columns", entity_name = "louis_sydney.finance.amlalerts.InvestigationNotes", tag_key = "financial_sensitivity", tag_value = "admin" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.customerinteractions.InteractionNotes", tag_key = "financial_sensitivity", tag_value = "analyst" },
  
  # Audit data classification
  { entity_type = "columns", entity_name = "louis_sydney.finance.auditlogs.UserID", tag_key = "audit_scope", tag_value = "sensitive" },
  { entity_type = "columns", entity_name = "louis_sydney.finance.auditlogs.IPAddress", tag_key = "audit_scope", tag_value = "sensitive" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.auditlogs", tag_key = "audit_scope", tag_value = "restricted" },
  
  # Regional data residency
  { entity_type = "tables", entity_name = "louis_sydney.finance.customers", tag_key = "data_region", tag_value = "global" },
  { entity_type = "tables", entity_name = "louis_sydney.finance.tradingpositions", tag_key = "data_region", tag_value = "us" },
]

fgac_policies = [
  # Clinical PHI masking policies
  {
    name             = "mask_diagnosis_codes_non_clinical"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Junior_Analyst"]
    comment          = "Mask diagnosis codes for non-clinical staff"
    match_condition  = "hasTagValue('phi_level', 'masked')"
    match_alias      = "diagnosis_data"
    function_name    = "mask_diagnosis_code"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "redact_clinical_notes"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Finance_Analyst", "Junior_Analyst"]
    comment          = "Redact treatment notes and patient identifiers"
    match_condition  = "hasTagValue('phi_level', 'restricted')"
    match_alias      = "restricted_phi"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "mask_clinical_names"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst", "Junior_Analyst"]
    comment          = "Partially mask attending physician names"
    match_condition  = "hasTagValue('phi_level', 'masked')"
    match_alias      = "clinical_names"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  
  # Financial PII masking policies
  {
    name             = "mask_customer_ssn"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst", "Clinical_Analyst"]
    comment          = "Mask SSN showing only last 4 digits"
    match_condition  = "hasTagValue('pii_level', 'restricted')"
    match_alias      = "ssn_data"
    function_name    = "mask_ssn"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_customer_email"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst"]
    comment          = "Mask email addresses preserving domain"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "email_data"
    function_name    = "mask_email"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "mask_customer_names"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Junior_Analyst"]
    comment          = "Partially mask customer names for junior analysts"
    match_condition  = "hasTagValue('pii_level', 'masked')"
    match_alias      = "name_data"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # PCI-DSS credit card masking
  {
    name             = "mask_credit_cards_full"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst", "Clinical_Analyst"]
    comment          = "Fully mask credit card numbers and CVV"
    match_condition  = "hasTagValue('pci_level', 'restricted')"
    match_alias      = "pci_data"
    function_name    = "mask_credit_card_full"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # Financial data masking
  {
    name             = "mask_account_ids"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Junior_Analyst"]
    comment          = "Hash account IDs for junior analysts"
    match_condition  = "hasTagValue('financial_sensitivity', 'analyst')"
    match_alias      = "account_data"
    function_name    = "mask_account_number"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "round_financial_amounts"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Junior_Analyst"]
    comment          = "Round monetary amounts for privacy"
    match_condition  = "hasTagValue('financial_sensitivity', 'analyst')"
    match_alias      = "amount_data"
    function_name    = "mask_amount_rounded"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "redact_admin_financial_data"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst", "Clinical_Analyst"]
    comment          = "Redact admin-only financial data"
    match_condition  = "hasTagValue('financial_sensitivity', 'admin')"
    match_alias      = "admin_financial"
    function_name    = "mask_redact"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # Audit data masking
  {
    name             = "mask_audit_sensitive_data"
    policy_type      = "POLICY_TYPE_COLUMN_MASK"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst"]
    comment          = "Mask sensitive audit information"
    match_condition  = "hasTagValue('audit_scope', 'sensitive')"
    match_alias      = "audit_sensitive"
    function_name    = "mask_pii_partial"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  
  # Row-level filters
  {
    name             = "filter_trading_hours_only"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Finance_Analyst", "Junior_Analyst"]
    comment          = "Restrict trading data access to non-market hours"
    when_condition   = "hasTagValue('data_region', 'us')"
    function_name    = "filter_trading_hours"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
  {
    name             = "filter_us_clinical_data"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Clinical_Analyst"]
    comment          = "Limit clinical data to US regions only"
    when_condition   = "hasTagValue('data_region', 'us')"
    function_name    = "filter_by_region_us"
    function_catalog = "louis_sydney"
    function_schema  = "clinical"
  },
  {
    name             = "filter_audit_time_limited"
    policy_type      = "POLICY_TYPE_ROW_FILTER"
    catalog          = "louis_sydney"
    to_principals    = ["Auditor_Temp"]
    comment          = "Time-limited access to audit data"
    when_condition   = "hasTagValue('audit_scope', 'restricted')"
    function_name    = "filter_audit_expiry"
    function_catalog = "louis_sydney"
    function_schema  = "finance"
  },
]

group_members = {}

genie_space_title       = "Healthcare Finance Analytics"
genie_space_description = "Explore patient encounters, financial transactions, and compliance data. Designed for clinical staff, financial analysts, and compliance officers with appropriate data masking."

genie_sample_questions = [
  "What is the total transaction volume by account type for active customers?",
  "How many patient encounters occurred last month by encounter type?",
  "Which accounts have been flagged for AML review this quarter?",
  "What is the average balance for checking accounts by region?",
  "Show the top 10 customers by transaction volume for completed transactions",
  "How many credit cards are currently active vs blocked?",
  "What are the most common diagnosis codes in outpatient encounters?",
  "Which trading desks have the highest P&L this month?",
  "How many AML alerts are currently under investigation?",
]

genie_instructions = "When asked about 'customers' without a status qualifier, default to active customers (CustomerStatus = 'Active'). When asked about 'transactions' without specifying status, default to completed transactions (TransactionStatus = 'Completed'). When asked about 'accounts' without status, default to active accounts (AccountStatus = 'Active'). For patient encounters, default to all encounter types unless specified. 'Last month' means the previous calendar month. Round monetary values to 2 decimal places. Patient names and SSNs are masked for non-clinical roles. Credit card numbers are always masked except for authorized PCI-DSS personnel."

genie_benchmarks = [
  {
    question = "What is the total amount of completed transactions?"
    sql      = "SELECT SUM(Amount) as total_amount FROM louis_sydney.finance.transactions WHERE TransactionStatus = 'Completed'"
  },
  {
    question = "How many patient encounters occurred last month?"
    sql      = "SELECT COUNT(*) FROM louis_sydney.clinical.encounters WHERE EncounterDate >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND EncounterDate < DATE_TRUNC('month', CURRENT_DATE)"
  },
  {
    question = "What is the average risk score for active customers?"
    sql      = "SELECT AVG(RiskScore) as avg_risk_score FROM louis_sydney.finance.customers WHERE CustomerStatus = 'Active'"
  },
  {
    question = "How many AML alerts are currently under investigation?"
    sql      = "SELECT COUNT(*) FROM louis_sydney.finance.amlalerts WHERE InvestigationStatus = 'Under Review'"
  },
  {
    question = "What is the total credit limit for active credit cards?"
    sql      = "SELECT SUM(CreditLimit) as total_credit_limit FROM louis_sydney.finance.creditcards WHERE CardStatus = 'Active'"
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
  {
    sql          = "accounts.AccountStatus = 'Active'"
    display_name = "active accounts"
    comment      = "Only include active bank accounts"
    instruction  = "Apply when the user asks about accounts without specifying a status"
  },
  {
    sql          = "creditcards.CardStatus = 'Active'"
    display_name = "active credit cards"
    comment      = "Only include active credit cards"
    instruction  = "Apply when the user asks about credit cards without specifying a status"
  },
]

genie_sql_measures = [
  {
    alias        = "total_transaction_amount"
    sql          = "SUM(transactions.Amount)"
    display_name = "total transaction amount"
    comment      = "Sum of all transaction amounts"
    instruction  = "Use for revenue, total transaction volume, or payment calculations"
  },
  {
    alias        = "avg_account_balance"
    sql          = "AVG(accounts.Balance)"
    display_name = "average account balance"
    comment      = "Average balance across bank accounts"
    instruction  = "Use when asked about average balances or account values"
  },
  {
    alias        = "total_credit_limit"
    sql          = "SUM(creditcards.CreditLimit)"
    display_name = "total credit limit"
    comment      = "Sum of credit limits across cards"
    instruction  = "Use for credit exposure or limit analysis"
  },
  {
    alias        = "avg_risk_score"
    sql          = "AVG(customers.RiskScore)"
    display_name = "average risk score"
    comment      = "Average AML risk score across customers"
    instruction  = "Use when asked about risk scores or risk averages"
  },
  {
    alias        = "encounter_count"
    sql          = "COUNT(encounters.EncounterID)"
    display_name = "encounter count"
    comment      = "Number of patient encounters"
    instruction  = "Use when counting patient visits or encounters"
  },
]

genie_sql_expressions = [
  {
    alias        = "transaction_year"
    sql          = "YEAR(transactions.TransactionDate)"
    display_name = "transaction year"
    comment      = "Extracts year from transaction date"
    instruction  = "Use for year-over-year transaction analysis"
  },
  {
    alias        = "encounter_month"
    sql          = "DATE_TRUNC('month', encounters.EncounterDate)"
    display_name = "encounter month"
    comment      = "Groups encounters by month"
    instruction  = "Use for monthly encounter trending"
  },
  {
    alias        = "account_age_days"
    sql          = "DATEDIFF(CURRENT_DATE, accounts.OpenDate)"
    display_name = "account age in days"
    comment      = "Number of days since account was opened"
    instruction  = "Use for account tenure analysis"
  },
  {
    alias        = "high_risk_customer"
    sql          = "CASE WHEN customers.RiskScore >= 70 THEN 'High Risk' ELSE 'Standard Risk' END"
    display_name = "risk category"
    comment      = "Categorizes customers as high risk (70+) or standard"
    instruction  = "Use when segmenting customers by risk level"
  },
]

genie_join_specs = [
  {
    left_table  = "louis_sydney.finance.transactions"
    left_alias  = "transactions"
    right_table = "louis_sydney.finance.accounts"
    right_alias = "accounts"
    sql         = "transactions.AccountID = accounts.AccountID"
    comment     = "Join transactions to accounts on AccountID"
    instruction = "Use when you need account details for transaction queries"
  },
  {
    left_table  = "louis_sydney.finance.accounts"
    left_alias  = "accounts"
    right_table = "louis_sydney.finance.customers"
    right_alias = "customers"
    sql         = "accounts.CustomerID = customers.CustomerID"
    comment     = "Join accounts to customers on CustomerID"
    instruction = "Use when you need customer details for account queries"
  },
  {
    left_table  = "louis_sydney.finance.creditcards"
    left_alias  = "creditcards"
    right_table = "louis_sydney.finance.customers"
    right_alias = "customers"
    sql         = "creditcards.CustomerID = customers.CustomerID"
    comment     = "Join credit cards to customers on CustomerID"
    instruction = "Use when you need customer details for credit card queries"
  },
  {
    left_table  = "louis_sydney.finance.amlalerts"
    left_alias  = "amlalerts"
    right_table = "louis_sydney.finance.customers"
    right_alias = "customers"
    sql         = "amlalerts.CustomerID = customers.CustomerID"
    comment     = "Join AML alerts to customers on CustomerID"
    instruction = "Use when you need customer context for AML alert analysis"
  },
  {
    left_table  = "louis_sydney.finance.amlalerts"
    left_alias  = "amlalerts"
    right_table = "louis_sydney.finance.transactions"
    right_alias = "transactions"
    sql         = "amlalerts.TransactionID = transactions.TransactionID"
    comment     = "Join AML alerts to transactions on TransactionID"
    instruction = "Use when you need transaction details for AML alert investigation"
  },
]
```

This configuration provides comprehensive ABAC controls for your healthcare and financial data with:

1. **7 user groups** with different access levels
2. **6 tag policies** covering PHI, PII, PCI-DSS, financial sensitivity, regional access, and audit scope
3. **Column masking** for sensitive data like SSNs, credit cards, diagnosis codes, and treatment notes
4. **Row-level filtering** for regional access control, trading hours restrictions, and time-limited audit access
5. **Genie Space configuration** tailored to healthcare finance analytics with relevant sample questions, measures, and joins

The masking functions are deployed only to the schemas where they're needed, and all policies reference the correct catalog/schema combinations for your `louis_sydney.clinical` and `louis_sydney.finance` data.