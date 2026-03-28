-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Finance ABAC Policies - Minimal 5 Scenarios
-- MAGIC
-- MAGIC Catalog-level ABAC policies for the minimal finance demo (5 groups, 5 scenarios).
-- MAGIC
-- MAGIC ## Prerequisites
-- MAGIC - Unity Catalog enabled with ABAC
-- MAGIC - Tag policies created (Terraform or 2.CreateFinanceTagPolicies.py)
-- MAGIC - 5 groups created (Terraform: Junior_Analyst, Senior_Analyst, US_Region_Staff, EU_Region_Staff, Compliance_Officer)
-- MAGIC - Tables tagged (3.ApplyFinanceSetTags.sql)
-- MAGIC - ABAC functions deployed (0.1finance_abac_functions.sql)
-- MAGIC
-- MAGIC ## 5 Scenarios
-- MAGIC 1. PII masking (Customers) - Junior masked, Senior + Compliance unmasked
-- MAGIC 2. Fraud / card (CreditCards) - Junior last-4, Senior full card, Compliance full+CVV
-- MAGIC 3. Fraud / transactions (Transactions) - Junior rounded amount, Senior + Compliance full
-- MAGIC 4. US region - US_Region_Staff row filter
-- MAGIC 5. EU region - EU_Region_Staff row filter

-- COMMAND ----------

USE CATALOG fincat;
SHOW FUNCTIONS IN fincat.finance LIKE 'mask*';
SHOW FUNCTIONS IN fincat.finance LIKE 'filter*';
SELECT "Ready to create catalog-level ABAC policies (5 scenarios)" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## POLICY 1: PII Masking (Customers)
-- MAGIC Junior_Analyst: mask_pii_partial on Limited_PII columns, mask_ssn on SSN. Senior_Analyst and Compliance_Officer: unmasked.

-- COMMAND ----------

CREATE OR REPLACE POLICY fincat_pii_junior_mask
ON CATALOG fincat
COMMENT 'PII: Mask names and email for junior analysts'
COLUMN MASK fincat.finance.mask_pii_partial
TO `Junior_Analyst`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Limited_PII') AS pii_cols
ON COLUMN pii_cols;

CREATE OR REPLACE POLICY fincat_pii_junior_ssn
ON CATALOG fincat
COMMENT 'PII: Mask SSN for junior analysts'
COLUMN MASK fincat.finance.mask_ssn
TO `Junior_Analyst`
FOR TABLES
MATCH COLUMNS hasTagValue('pii_level', 'Full_PII') AND hasTagValue('data_residency', 'US') AS ssn_cols
ON COLUMN ssn_cols;

SELECT "POLICY 1: PII masking policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## POLICY 2: Fraud / Card (CreditCards)
-- MAGIC Junior_Analyst: last-4 only. Senior_Analyst: full card (CVV masked). Compliance_Officer: full card + CVV.

-- COMMAND ----------

CREATE OR REPLACE POLICY fincat_pci_junior_last4
ON CATALOG fincat
COMMENT 'Card: Last 4 digits only for junior analysts'
COLUMN MASK fincat.finance.mask_credit_card_last4
TO `Junior_Analyst`
FOR TABLES
MATCH COLUMNS hasTagValue('pci_clearance', 'Full') AS card_cols
ON COLUMN card_cols;

CREATE OR REPLACE POLICY fincat_pci_cvv_mask_except_compliance
ON CATALOG fincat
COMMENT 'Card: Mask CVV for all except Compliance_Officer'
COLUMN MASK fincat.finance.mask_credit_card_full
TO `account users`
EXCEPT `Compliance_Officer`
FOR TABLES
MATCH COLUMNS hasTagValue('pci_clearance', 'Administrative') AS cvv_cols
ON COLUMN cvv_cols;

SELECT "POLICY 2: Fraud/card policies created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## POLICY 3: Fraud / Transactions (Amount rounding)
-- MAGIC Junior_Analyst: rounded amounts. Senior_Analyst and Compliance_Officer: full.

-- COMMAND ----------

CREATE OR REPLACE POLICY fincat_aml_junior_round
ON CATALOG fincat
COMMENT 'Transactions: Round amount for junior analysts'
COLUMN MASK fincat.finance.mask_amount_rounded
TO `Junior_Analyst`
FOR TABLES
MATCH COLUMNS hasTagValue('aml_clearance', 'Junior_Analyst') AS aml_cols
ON COLUMN aml_cols;

SELECT "POLICY 3: Fraud/transactions policy created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## POLICY 4: US Region (Row filter for US_Region_Staff)
-- MAGIC Tables tagged customer_region = 'Regional' get row filter for US staff.

-- COMMAND ----------

CREATE OR REPLACE POLICY fincat_region_us
ON CATALOG fincat
COMMENT 'Region: US staff see US customer data only'
ROW FILTER fincat.finance.filter_by_region_us
TO `US_Region_Staff`
FOR TABLES
WHEN hasTagValue('customer_region', 'Regional');

SELECT "POLICY 4: US region policy created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## POLICY 5: EU Region (Row filter for EU_Region_Staff)
-- MAGIC Tables tagged customer_region = 'Regional' get row filter for EU staff.

-- COMMAND ----------

CREATE OR REPLACE POLICY fincat_region_eu
ON CATALOG fincat
COMMENT 'Region: EU staff see EU customer data only'
ROW FILTER fincat.finance.filter_by_region_eu
TO `EU_Region_Staff`
FOR TABLES
WHEN hasTagValue('customer_region', 'Regional');

SELECT "POLICY 5: EU region policy created" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verification

-- COMMAND ----------

SHOW POLICIES ON CATALOG fincat;

SELECT 'Policy Summary' as section, '5 scenarios' as status
UNION ALL SELECT 'Scenario 1', 'PII masking (2 policies)'
UNION ALL SELECT 'Scenario 2', 'Fraud/card (2 policies)'
UNION ALL SELECT 'Scenario 3', 'Fraud/transactions (1 policy)'
UNION ALL SELECT 'Scenario 4', 'US region (1 policy)'
UNION ALL SELECT 'Scenario 5', 'EU region (1 policy)';

SELECT "All 7 finance ABAC policies created (minimal demo)" as status;
SELECT "Next: 5.TestFinanceABACPolicies.sql" as next_step;
