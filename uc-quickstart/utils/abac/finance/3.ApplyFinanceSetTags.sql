-- =============================================
-- APPLY FINANCE ABAC TAGS (Minimal 5 Scenarios)
-- Purpose: Tag tables/columns for 5 ABAC scenarios only
-- Tables: Customers, CreditCards, Transactions, Accounts
-- =============================================

USE CATALOG fincat;
USE SCHEMA finance;

-- =============================================
-- SCENARIO 1: PII MASKING (Customers)
-- Junior: masked; Senior + Compliance: unmasked
-- =============================================

ALTER TABLE Customers
SET TAGS (
    'data_residency' = 'Global',
    'pii_level' = 'Full_PII'
);

ALTER TABLE Customers ALTER COLUMN CustomerRegion
SET TAGS (
    'customer_region' = 'EU',
    'data_residency' = 'EU'
);

ALTER TABLE Customers ALTER COLUMN SSN
SET TAGS (
    'pii_level' = 'Full_PII',
    'data_residency' = 'US'
);

ALTER TABLE Customers ALTER COLUMN FirstName SET TAGS ('pii_level' = 'Limited_PII');
ALTER TABLE Customers ALTER COLUMN LastName  SET TAGS ('pii_level' = 'Limited_PII');
ALTER TABLE Customers ALTER COLUMN Email     SET TAGS ('pii_level' = 'Limited_PII');

SELECT '✅ SCENARIO 1: PII and region tags applied to Customers' as status;

-- =============================================
-- SCENARIO 2: FRAUD / CARD (CreditCards)
-- Junior: last-4 only; Senior: full card; Compliance: full + CVV
-- =============================================

ALTER TABLE CreditCards SET TAGS ('pci_clearance' = 'Full');

ALTER TABLE CreditCards ALTER COLUMN CardNumber SET TAGS ('pci_clearance' = 'Full');
ALTER TABLE CreditCards ALTER COLUMN CVV        SET TAGS ('pci_clearance' = 'Administrative');

SELECT '✅ SCENARIO 2: PCI tags applied to CreditCards' as status;

-- =============================================
-- SCENARIO 3: FRAUD / TRANSACTIONS (Amount rounding)
-- Junior: rounded amounts; Senior + Compliance: full
-- =============================================

ALTER TABLE Transactions SET TAGS ('aml_clearance' = 'Senior_Investigator');

ALTER TABLE Transactions ALTER COLUMN Amount SET TAGS ('aml_clearance' = 'Junior_Analyst');

SELECT '✅ SCENARIO 3: AML tags applied to Transactions' as status;

-- =============================================
-- SCENARIOS 4 & 5: REGIONAL ROW FILTERS (US / EU)
-- Tag tables so row filter policies apply (filter functions restrict by row)
-- =============================================

-- Customers table: in scope for regional policies (US_Region_Staff -> US rows; EU_Region_Staff -> EU rows)
ALTER TABLE Customers SET TAGS ('customer_region' = 'Regional', 'data_residency' = 'Global');

-- Accounts: optional for regional demo
ALTER TABLE Accounts SET TAGS ('data_residency' = 'Global', 'customer_region' = 'Regional');

SELECT '✅ SCENARIOS 4 & 5: Region tags applied for US/EU row filters' as status;

-- =============================================
-- VERIFICATION
-- =============================================

SELECT table_name, tag_name, tag_value
FROM system.information_schema.table_tags
WHERE schema_name = 'finance'
ORDER BY table_name, tag_name;

SELECT '✅ Minimal finance ABAC tags applied (5 scenarios)' as status;
SELECT '🔐 Next: 4.CreateFinanceABACPolicies.sql' as next_step;
