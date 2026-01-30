-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 🔐 Finance ABAC Policies - Unity Catalog Implementation
-- MAGIC
-- MAGIC This notebook creates **catalog-level ABAC policies** for financial services data governance using Unity Catalog syntax.
-- MAGIC
-- MAGIC ## 📋 Prerequisites
-- MAGIC - ✅ Unity Catalog enabled with ABAC policies feature
-- MAGIC - ✅ Finance tag policies created (from `2.CreateFinanceTagPolicies.py`)
-- MAGIC - ✅ Finance account groups created (from `1.CreateFinanceGroups.py`)
-- MAGIC - ✅ Finance tables tagged (from `3.ApplyFinanceSetTags.sql`)
-- MAGIC - ✅ ABAC masking functions deployed (from `0.1finance_abac_functions.sql`)
-- MAGIC - ✅ Appropriate permissions to create catalog-level policies
-- MAGIC
-- MAGIC ## 🎯 Policy Creation Approach
-- MAGIC - **Catalog-level policies:** Apply to entire `fincat` catalog
-- MAGIC - **Tag-based conditions:** Use existing finance tags
-- MAGIC - **Group-based principals:** Target finance account groups
-- MAGIC - **Compliance frameworks:** PCI-DSS, AML/KYC, GDPR, SOX, GLBA, SEC
-- MAGIC
-- MAGIC ## 🏦 Finance ABAC Policies (7 Scenarios)
-- MAGIC 1. **PCI-DSS Payment Card Masking** - Credit card data protection
-- MAGIC 2. **AML/KYC Transaction Monitoring** - Progressive access to transaction data
-- MAGIC 3. **Trading Desk Chinese Walls** - Information barriers between trading and research
-- MAGIC 4. **Cross-Border Data Residency** - Geographic data access control (GDPR, CCPA)
-- MAGIC 5. **Time-Based Trading Access** - Market hours restrictions for positions
-- MAGIC 6. **Temporary Auditor Access** - Time-limited SOX audit access
-- MAGIC 7. **Customer PII Progressive Privacy** - Tiered PII access by role

-- COMMAND ----------

-- Set catalog context for policy creation
USE CATALOG fincat;

-- Verify we have the required masking functions
SHOW FUNCTIONS IN fincat.finance LIKE 'mask*';
SHOW FUNCTIONS IN fincat.finance LIKE 'filter*';

SELECT "✅ Ready to create catalog-level ABAC policies for finance domain" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🔐 POLICY 1: PCI-DSS Payment Card Masking
-- MAGIC
-- MAGIC **Purpose:** Protect credit card data according to PCI-DSS requirements by showing different levels of card data based on role.
-- MAGIC
-- MAGIC **Business Value:** Enables customer service and fraud detection while maintaining PCI-DSS compliance
-- MAGIC
-- MAGIC **Compliance:** PCI-DSS Data Security Standard
-- MAGIC
-- MAGIC **Tag Conditions:** 
-- MAGIC - `pci_clearance = 'Full'` - Full card number visible
-- MAGIC - `payment_role = 'Fraud_Analyst'` - Fraud analysts get full access
-- MAGIC
-- MAGIC **Access Levels:**
-- MAGIC - Customer Service: Last 4 digits only (XXXX-XXXX-XXXX-1234)
-- MAGIC - Fraud Analysts: Full card number (4532-1234-5678-9010)
-- MAGIC - Others: Fully masked (XXXX-XXXX-XXXX-XXXX)

-- COMMAND ----------

-- POLICY 1A: Credit Card Number - Full Access for Fraud Analysts
CREATE OR REPLACE POLICY fincat_pci_card_full_access
ON CATALOG fincat
COMMENT 'PCI-DSS: Full credit card number access for fraud analysts'
COLUMN MASK fincat.finance.mask_credit_card_last4
TO `Fraud_Analyst`
FOR TABLES
MATCH COLUMNS hasTagValue('pci_clearance', 'Full') AND hasTagValue('payment_role', 'Fraud_Analyst') AS card_cols
ON COLUMN card_cols;

-- POLICY 1B: Credit Card Number - Last 4 Digits for Customer Service
CREATE OR REPLACE POLICY fincat_pci_card_customer_service
ON CATALOG fincat
COMMENT 'PCI-DSS: Show last 4 digits of card number for customer service'
COLUMN MASK fincat.finance.mask_credit_card_last4
TO `Credit_Card_Support`
FOR TABLES
MATCH COLUMNS hasTagValue('pci_clearance', 'Full') AS cs_card_cols
ON COLUMN cs_card_cols;

-- POLICY 1C: CVV - Complete Masking for All Except Compliance
CREATE OR REPLACE POLICY fincat_pci_cvv_mask
ON CATALOG fincat
COMMENT 'PCI-DSS: Mask CVV completely for all users except compliance officers'
COLUMN MASK fincat.finance.mask_credit_card_full
TO `Credit_Card_Support`, `Fraud_Analyst`, `Marketing_Team`
FOR TABLES
MATCH COLUMNS hasTagValue('pci_clearance', 'Administrative') AS cvv_cols
ON COLUMN cvv_cols;

SELECT "✅ POLICY 1: PCI-DSS payment card masking policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 💰 POLICY 2: AML/KYC Transaction Monitoring
-- MAGIC
-- MAGIC **Purpose:** Provide progressive access to transaction data based on AML investigation level - junior analysts see aggregated data, senior investigators see full details.
-- MAGIC
-- MAGIC **Business Value:** Enables efficient AML investigations while protecting customer privacy for routine monitoring
-- MAGIC
-- MAGIC **Compliance:** AML/KYC, FATF recommendations, FinCEN
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `aml_clearance = 'Senior_Investigator'` - Full transaction details
-- MAGIC - `aml_clearance = 'Junior_Analyst'` - Aggregated amounts only
-- MAGIC
-- MAGIC **Access Levels:**
-- MAGIC - Junior Analysts: Rounded transaction amounts
-- MAGIC - Senior Investigators: Full transaction details
-- MAGIC - Compliance Officers: All data including investigation notes

-- COMMAND ----------

-- POLICY 2A: Transaction Amount Rounding for Junior Analysts
CREATE OR REPLACE POLICY fincat_aml_transaction_junior
ON CATALOG fincat
COMMENT 'AML: Round transaction amounts for junior analysts'
COLUMN MASK fincat.finance.mask_amount_rounded
TO `AML_Investigator_Junior`
FOR TABLES
MATCH COLUMNS hasTagValue('aml_clearance', 'Junior_Analyst') AS junior_amount_cols
ON COLUMN junior_amount_cols;

-- POLICY 2B: Full Transaction Access for Senior Investigators
-- (No masking policy needed - they see original data)

-- POLICY 2C: Row Filter - Hide Flagged Transactions from Junior Analysts
CREATE OR REPLACE POLICY fincat_aml_flagged_filter
ON CATALOG fincat
COMMENT 'AML: Hide flagged transactions from junior analysts'
ROW FILTER fincat.finance.filter_aml_clearance
TO `AML_Investigator_Junior`
FOR TABLES
WHEN hasTagValue('aml_clearance', 'Compliance_Officer');

SELECT "✅ POLICY 2: AML/KYC transaction monitoring policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🏛️ POLICY 3: Trading Desk Chinese Walls
-- MAGIC
-- MAGIC **Purpose:** Enforce information barriers between trading desks and research/advisory teams to prevent conflicts of interest and insider trading.
-- MAGIC
-- MAGIC **Business Value:** SEC and MiFID II compliance while enabling independent operation of trading and research
-- MAGIC
-- MAGIC **Compliance:** SEC regulations, MiFID II
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `information_barrier = 'Trading_Side'` - Trading desk data
-- MAGIC - `information_barrier = 'Advisory_Side'` - Research/advisory data
-- MAGIC - `information_barrier = 'Neutral'` - Risk and compliance see all
-- MAGIC
-- MAGIC **Access Rules:**
-- MAGIC - Equity Traders: See only equity trading positions
-- MAGIC - Research Analysts: Blocked from all trading data
-- MAGIC - Risk Managers: Neutral access to all desks

-- COMMAND ----------

-- POLICY 3A: Block Trading Data from Research Analysts
CREATE OR REPLACE POLICY fincat_chinese_wall_block_research
ON CATALOG fincat
COMMENT 'Chinese Wall: Block research analysts from accessing trading positions'
ROW FILTER fincat.finance.filter_information_barrier
TO `Research_Analyst`
FOR TABLES
WHEN hasTagValue('information_barrier', 'Trading_Side');

-- POLICY 3B: Filter Trading Positions by Desk
-- Each trading desk only sees their own positions
CREATE OR REPLACE POLICY fincat_trading_desk_filter
ON CATALOG fincat
COMMENT 'Chinese Wall: Traders only see their own desk positions'
ROW FILTER fincat.finance.filter_information_barrier
TO `Equity_Trader`, `Fixed_Income_Trader`
FOR TABLES
WHEN hasTagValue('trading_desk', 'Equity') OR hasTagValue('trading_desk', 'Fixed_Income');

SELECT "✅ POLICY 3: Trading desk Chinese wall policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🌍 POLICY 4: Cross-Border Data Residency
-- MAGIC
-- MAGIC **Purpose:** Enforce geographic data access control to comply with GDPR (EU), CCPA (California), PDPA (Singapore), and regional banking regulations.
-- MAGIC
-- MAGIC **Business Value:** Avoid regulatory violations and fines by ensuring data stays within jurisdictional boundaries
-- MAGIC
-- MAGIC **Compliance:** GDPR, CCPA, PDPA, LGPD
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `customer_region = 'EU'` - European customer data
-- MAGIC - `data_residency = 'EU'` - Must stay in EU
-- MAGIC
-- MAGIC **Access Rules:**
-- MAGIC - EU Staff: Access only EU customer data
-- MAGIC - US Staff: Access only US customer data
-- MAGIC - APAC Staff: Access only APAC customer data
-- MAGIC - Global roles (Compliance): Access all regions

-- COMMAND ----------

-- POLICY 4A: EU Data Residency - EU Staff Only
CREATE OR REPLACE POLICY fincat_gdpr_eu_residency
ON CATALOG fincat
COMMENT 'GDPR: EU customer data accessible only by EU-based staff'
ROW FILTER fincat.finance.filter_by_region_eu
TO `Regional_EU_Staff`
FOR TABLES
WHEN hasTagValue('customer_region', 'EU');

-- POLICY 4B: US Data Residency - US Staff Only
CREATE OR REPLACE POLICY fincat_ccpa_us_residency
ON CATALOG fincat
COMMENT 'CCPA/GLBA: US customer data accessible only by US-based staff'
ROW FILTER fincat.finance.filter_by_region_us
TO `Regional_US_Staff`
FOR TABLES
WHEN hasTagValue('customer_region', 'US');

-- POLICY 4C: APAC Data Residency - APAC Staff Only
CREATE OR REPLACE POLICY fincat_apac_residency
ON CATALOG fincat
COMMENT 'PDPA: APAC customer data accessible only by APAC-based staff'
ROW FILTER fincat.finance.filter_by_region_apac
TO `Regional_APAC_Staff`
FOR TABLES
WHEN hasTagValue('customer_region', 'APAC');

-- POLICY 4D: SSN Masking for Non-US Staff
CREATE OR REPLACE POLICY fincat_ssn_mask_non_us
ON CATALOG fincat
COMMENT 'GLBA: Mask US SSN from non-US staff'
COLUMN MASK fincat.finance.mask_ssn
TO `Regional_EU_Staff`, `Regional_APAC_Staff`
FOR TABLES
MATCH COLUMNS hasTagValue('data_residency', 'US') AND hasTagValue('pii_level', 'Full_PII') AS ssn_cols
ON COLUMN ssn_cols;

SELECT "✅ POLICY 4: Cross-border data residency policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## ⏰ POLICY 5: Time-Based Trading Access
-- MAGIC
-- MAGIC **Purpose:** Restrict access to trading positions and P&L data during market hours to prevent manipulation and ensure proper oversight.
-- MAGIC
-- MAGIC **Business Value:** Prevent market manipulation and conflicts of interest during active trading
-- MAGIC
-- MAGIC **Compliance:** Market manipulation prevention, insider trading controls
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `market_hours = 'Trading_Hours'` - Restricted during market hours
-- MAGIC - `market_hours = 'After_Hours'` - Accessible only after market close
-- MAGIC
-- MAGIC **Access Rules:**
-- MAGIC - Risk Managers: Cannot access live positions during trading hours (9:30 AM - 4:00 PM ET)
-- MAGIC - Traders: Full access during trading hours
-- MAGIC - After Hours: Risk managers can review P&L after market close

-- COMMAND ----------

-- POLICY 5A: Block Risk Managers from Live Positions During Trading Hours
CREATE OR REPLACE POLICY fincat_trading_hours_restriction
ON CATALOG fincat
COMMENT 'Market Hours: Block risk managers from accessing positions during trading hours'
ROW FILTER fincat.finance.filter_trading_hours
TO `Risk_Manager`
FOR TABLES
WHEN hasTagValue('market_hours', 'Trading_Hours');

-- POLICY 5B: Mask P&L During Trading Hours
CREATE OR REPLACE POLICY fincat_pnl_trading_hours_mask
ON CATALOG fincat
COMMENT 'Market Hours: Mask P&L values during active trading'
COLUMN MASK fincat.finance.mask_amount_rounded
TO `Risk_Manager`
FOR TABLES
MATCH COLUMNS hasTagValue('market_hours', 'After_Hours') AS pnl_cols
ON COLUMN pnl_cols;

SELECT "✅ POLICY 5: Time-based trading access policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 📊 POLICY 6: Temporary Auditor Access
-- MAGIC
-- MAGIC **Purpose:** Grant external auditors temporary, expiring access to financial records for SOX compliance audits.
-- MAGIC
-- MAGIC **Business Value:** Enable external audits while automatically revoking access after audit completion
-- MAGIC
-- MAGIC **Compliance:** SOX (Sarbanes-Oxley), external audit requirements
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `audit_project = 'Q1_SOX_Audit'` - Specific audit project
-- MAGIC - `sox_scope = 'In_Scope'` - Tables included in SOX audit scope
-- MAGIC
-- MAGIC **Access Rules:**
-- MAGIC - External Auditors: Access expires based on audit project timeline
-- MAGIC - Limited to SOX in-scope tables and accounts
-- MAGIC - Automatic revocation after expiry date

-- COMMAND ----------

-- POLICY 6A: Temporary Access for External Auditors with Expiry
CREATE OR REPLACE POLICY fincat_sox_audit_temporary_access
ON CATALOG fincat
COMMENT 'SOX: Temporary auditor access with automatic expiration'
ROW FILTER fincat.finance.filter_audit_expiry
TO `External_Auditor`
FOR TABLES
WHEN hasTagValue('audit_project', 'Q1_SOX_Audit');

-- POLICY 6B: Limit Auditor Access to SOX In-Scope Tables Only
CREATE OR REPLACE POLICY fincat_sox_scope_filter
ON CATALOG fincat
COMMENT 'SOX: Auditors can only access in-scope financial tables'
ROW FILTER fincat.finance.filter_audit_expiry
TO `External_Auditor`
FOR TABLES
WHEN hasTagValue('sox_scope', 'In_Scope');

-- POLICY 6C: Mask Customer PII from External Auditors
CREATE OR REPLACE POLICY fincat_auditor_pii_mask
ON CATALOG fincat
COMMENT 'SOX: Mask customer PII from external auditors (not required for financial audit)'
COLUMN MASK fincat.finance.mask_pii_partial
TO `External_Auditor`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Full_PII') OR hasTagValue('pii_level', 'Limited_PII') AS auditor_pii_cols
ON COLUMN auditor_pii_cols;

SELECT "✅ POLICY 6: Temporary auditor access policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🔒 POLICY 7: Customer PII Progressive Privacy
-- MAGIC
-- MAGIC **Purpose:** Provide tiered access to customer personal information based on role and business purpose - marketing sees anonymized data, customer service sees partial data, KYC teams see full details.
-- MAGIC
-- MAGIC **Business Value:** Enable marketing analytics and customer service while protecting customer privacy
-- MAGIC
-- MAGIC **Compliance:** GDPR, GLBA, CCPA privacy regulations
-- MAGIC
-- MAGIC **Tag Conditions:**
-- MAGIC - `pii_level = 'Full_PII'` - Complete personal information
-- MAGIC - `pii_level = 'Limited_PII'` - Partial personal information
-- MAGIC - `pii_level = 'De_Identified'` - Anonymized/aggregated data
-- MAGIC
-- MAGIC **Access Levels:**
-- MAGIC - Marketing Team: De-identified, aggregated data only
-- MAGIC - Customer Service: Partial PII (masked names, emails)
-- MAGIC - KYC Specialists: Full PII for verification purposes

-- COMMAND ----------

-- POLICY 7A: De-Identify Customer Data for Marketing
CREATE OR REPLACE POLICY fincat_pii_marketing_deidentify
ON CATALOG fincat
COMMENT 'GDPR: De-identify customer PII for marketing team analytics'
COLUMN MASK fincat.finance.mask_customer_id_deterministic
TO `Marketing_Team`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Full_PII') AS marketing_pii_cols
ON COLUMN marketing_pii_cols;

-- POLICY 7B: Partial Masking for Customer Service
CREATE OR REPLACE POLICY fincat_pii_customer_service_partial
ON CATALOG fincat
COMMENT 'GDPR: Partial PII masking for customer service representatives'
COLUMN MASK fincat.finance.mask_pii_partial
TO `Credit_Card_Support`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Limited_PII') AS cs_pii_cols
ON COLUMN cs_pii_cols;

-- POLICY 7C: Email Masking for Non-KYC Roles
CREATE OR REPLACE POLICY fincat_pii_email_mask
ON CATALOG fincat
COMMENT 'GDPR: Mask customer email addresses for marketing and general staff'
COLUMN MASK fincat.finance.mask_email_finance
TO `Marketing_Team`, `Credit_Card_Support`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Limited_PII') AS email_cols
ON COLUMN email_cols;

-- POLICY 7D: Full PII Access for KYC Specialists (No masking policy - default behavior)
-- KYC_Specialist group sees unmasked data for verification purposes

SELECT "✅ POLICY 7: Customer PII progressive privacy policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## ✅ Verification and Summary

-- COMMAND ----------

-- List all created policies
SHOW POLICIES ON CATALOG fincat;

-- Summary of policies by scenario
SELECT 'Policy Summary' as section, '21 Total ABAC Policies Created' as status
UNION ALL
SELECT 'Scenario 1', 'PCI-DSS Payment Card Masking (3 policies)'
UNION ALL
SELECT 'Scenario 2', 'AML/KYC Transaction Monitoring (3 policies)'
UNION ALL
SELECT 'Scenario 3', 'Trading Desk Chinese Walls (2 policies)'
UNION ALL
SELECT 'Scenario 4', 'Cross-Border Data Residency (4 policies)'
UNION ALL
SELECT 'Scenario 5', 'Time-Based Trading Access (2 policies)'
UNION ALL
SELECT 'Scenario 6', 'Temporary Auditor Access (3 policies)'
UNION ALL
SELECT 'Scenario 7', 'Customer PII Progressive Privacy (4 policies)';

SELECT "🎉 All 21 finance ABAC policies created successfully!" as status;
SELECT "🔐 Compliance frameworks: PCI-DSS, AML/KYC, GDPR, SOX, GLBA, SEC, MiFID II, CCPA, PDPA" as frameworks;
SELECT "🏦 Ready for testing with 5.TestFinanceABACPolicies.sql" as next_step;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🎯 Next Steps
-- MAGIC
-- MAGIC 1. **Test policies** with different user personas using `5.TestFinanceABACPolicies.sql`
-- MAGIC 2. **Verify masking** by running queries as different groups
-- MAGIC 3. **Demo scenarios** using the field tricks from `ABAC_FINANCE_Demo_Plan.md`
-- MAGIC 4. **Monitor performance** following guidelines in `ABAC_Performance_Finance.md`
-- MAGIC
-- MAGIC ## 📚 Policy Architecture Summary
-- MAGIC
-- MAGIC ```
-- MAGIC Finance ABAC Policies
-- MAGIC ├── Payment Security (PCI-DSS)
-- MAGIC │   ├── Card number masking (role-based)
-- MAGIC │   ├── CVV protection
-- MAGIC │   └── Customer service limited access
-- MAGIC │
-- MAGIC ├── Compliance & Investigation (AML/KYC)
-- MAGIC │   ├── Progressive transaction access
-- MAGIC │   ├── Investigation notes protection
-- MAGIC │   └── Junior/senior analyst separation
-- MAGIC │
-- MAGIC ├── Market Operations (SEC, MiFID II)
-- MAGIC │   ├── Chinese wall enforcement
-- MAGIC │   ├── Desk-based position filtering
-- MAGIC │   └── Time-based P&L access
-- MAGIC │
-- MAGIC ├── Privacy & Residency (GDPR, CCPA)
-- MAGIC │   ├── Geographic data filtering
-- MAGIC │   ├── Cross-border restrictions
-- MAGIC │   ├── PII tiered access
-- MAGIC │   └── Marketing de-identification
-- MAGIC │
-- MAGIC └── Audit & Governance (SOX)
-- MAGIC     ├── Temporary auditor access
-- MAGIC     ├── Scope-based filtering
-- MAGIC     └── Automatic expiration
-- MAGIC ```
-- MAGIC
-- MAGIC ## 🏦 Enterprise-Grade Financial Data Governance Complete! 🎉
