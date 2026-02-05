-- =============================================
-- APPLY FINANCE ABAC TAGS TO TABLES AND COLUMNS
-- Purpose: Tag finance tables and columns for 7 ABAC scenarios
-- Compliance: PCI-DSS, AML/KYC, GDPR, SOX, GLBA
-- =============================================

USE CATALOG fincat;
USE SCHEMA finance;

-- =============================================
-- SCENARIO 1: PCI-DSS PAYMENT CARD MASKING
-- Apply tags to CreditCards table and sensitive columns
-- =============================================

-- Tag the entire CreditCards table
ALTER TABLE CreditCards 
SET TAGS (
    'pci_clearance' = 'Full',
    'payment_role' = 'Fraud_Analyst'
);

-- Tag sensitive card number column (highest protection)
ALTER TABLE CreditCards ALTER COLUMN CardNumber
SET TAGS (
    'pci_clearance' = 'Full',
    'payment_role' = 'Fraud_Analyst'
);

-- Tag CVV column (administrative access only)
ALTER TABLE CreditCards ALTER COLUMN CVV
SET TAGS (
    'pci_clearance' = 'Administrative'
);

-- Tag customer service viewable columns
ALTER TABLE CreditCards ALTER COLUMN CardType
SET TAGS (
    'pci_clearance' = 'Basic',
    'payment_role' = 'Customer_Service'
);

SELECT '✅ SCENARIO 1: PCI-DSS tags applied to CreditCards table' as status;

-- =============================================
-- SCENARIO 2: AML/KYC TRANSACTION MONITORING
-- Apply tags to Transactions and AMLAlerts tables
-- =============================================

-- Tag Transactions table for AML monitoring
ALTER TABLE Transactions
SET TAGS (
    'aml_clearance' = 'Senior_Investigator'
);

-- Tag transaction amount column
ALTER TABLE Transactions ALTER COLUMN Amount
SET TAGS (
    'aml_clearance' = 'Junior_Analyst'  -- Junior analysts can see amounts
);

-- Tag AML flag reason (senior access only)
ALTER TABLE Transactions ALTER COLUMN AMLFlagReason
SET TAGS (
    'aml_clearance' = 'Senior_Investigator'
);

-- Tag AMLAlerts table (compliance officer access)
ALTER TABLE AMLAlerts
SET TAGS (
    'aml_clearance' = 'Compliance_Officer'
);

-- Tag investigation notes (highly sensitive)
ALTER TABLE AMLAlerts ALTER COLUMN InvestigationNotes
SET TAGS (
    'aml_clearance' = 'Compliance_Officer'
);

SELECT '✅ SCENARIO 2: AML/KYC tags applied to Transactions and AMLAlerts' as status;

-- =============================================
-- SCENARIO 3: TRADING DESK CHINESE WALLS
-- Apply information barrier tags to TradingPositions
-- =============================================

-- Tag TradingPositions table
ALTER TABLE TradingPositions
SET TAGS (
    'trading_desk' = 'Equity',
    'information_barrier' = 'Trading_Side',
    'market_hours' = 'Trading_Hours'
);

-- Tag P&L column (sensitive during trading hours)
ALTER TABLE TradingPositions ALTER COLUMN PnL
SET TAGS (
    'information_barrier' = 'Trading_Side',
    'market_hours' = 'After_Hours'  -- Risk can only view after hours
);

-- Tag trading desk column
ALTER TABLE TradingPositions ALTER COLUMN TradingDesk
SET TAGS (
    'trading_desk' = 'Equity',
    'information_barrier' = 'Trading_Side'
);

SELECT '✅ SCENARIO 3: Chinese wall tags applied to TradingPositions' as status;

-- =============================================
-- SCENARIO 4: CROSS-BORDER DATA RESIDENCY
-- Apply geographic tags to Customers table
-- =============================================

-- Tag Customers table for data residency
ALTER TABLE Customers
SET TAGS (
    'data_residency' = 'Global',
    'pii_level' = 'Full_PII'
);

-- Tag customer region column (critical for GDPR)
ALTER TABLE Customers ALTER COLUMN CustomerRegion
SET TAGS (
    'customer_region' = 'EU',
    'data_residency' = 'EU'
);

-- Tag PII columns
ALTER TABLE Customers ALTER COLUMN SSN
SET TAGS (
    'pii_level' = 'Full_PII',
    'data_residency' = 'US'  -- SSN is US-specific
);

ALTER TABLE Customers ALTER COLUMN Email
SET TAGS (
    'pii_level' = 'Limited_PII'
);

ALTER TABLE Customers ALTER COLUMN FirstName
SET TAGS (
    'pii_level' = 'Limited_PII'
);

ALTER TABLE Customers ALTER COLUMN LastName
SET TAGS (
    'pii_level' = 'Limited_PII'
);

SELECT '✅ SCENARIO 4: Data residency tags applied to Customers' as status;

-- =============================================
-- SCENARIO 5: TIME-BASED TRADING ACCESS
-- Additional market hours tags for positions
-- =============================================

-- Tag current price (changes during trading hours)
ALTER TABLE TradingPositions ALTER COLUMN CurrentPrice
SET TAGS (
    'market_hours' = 'Trading_Hours'
);

-- Tag position status
ALTER TABLE TradingPositions ALTER COLUMN PositionStatus
SET TAGS (
    'market_hours' = '24x7'  -- Status can be viewed anytime
);

SELECT '✅ SCENARIO 5: Market hours tags applied to TradingPositions' as status;

-- =============================================
-- SCENARIO 6: TEMPORARY AUDITOR ACCESS
-- Apply audit tags to AuditLogs and relevant tables
-- =============================================

-- Tag AuditLogs table
ALTER TABLE AuditLogs
SET TAGS (
    'audit_project' = 'Q1_SOX_Audit',
    'sox_scope' = 'In_Scope'
);

-- Tag audit project column
ALTER TABLE AuditLogs ALTER COLUMN AuditProject
SET TAGS (
    'audit_project' = 'Q1_SOX_Audit'
);

-- Tag access expiration column
ALTER TABLE AuditLogs ALTER COLUMN AccessGrantedUntil
SET TAGS (
    'sox_scope' = 'In_Scope'
);

-- Tag Accounts table for SOX audit scope
ALTER TABLE Accounts
SET TAGS (
    'sox_scope' = 'In_Scope'
);

-- Tag account balance (SOX financial reporting)
ALTER TABLE Accounts ALTER COLUMN Balance
SET TAGS (
    'sox_scope' = 'In_Scope'
);

SELECT '✅ SCENARIO 6: Audit tags applied to AuditLogs and Accounts' as status;

-- =============================================
-- SCENARIO 7: CUSTOMER PII PROGRESSIVE PRIVACY
-- Apply tiered PII tags across customer data
-- =============================================

-- Tag date of birth (de-identified for marketing)
ALTER TABLE Customers ALTER COLUMN DateOfBirth
SET TAGS (
    'pii_level' = 'De_Identified'  -- Marketing sees age groups only
);

-- Tag address (limited PII)
ALTER TABLE Customers ALTER COLUMN Address
SET TAGS (
    'pii_level' = 'Limited_PII'
);

-- Tag Accounts for privacy levels
ALTER TABLE Accounts ALTER COLUMN Balance
SET TAGS (
    'pii_level' = 'Statistical_Only'  -- Marketing sees aggregated balances
);

-- Tag transaction amounts
ALTER TABLE Transactions ALTER COLUMN Amount
SET TAGS (
    'pii_level' = 'Statistical_Only'
);

SELECT '✅ SCENARIO 7: PII privacy tags applied across customer tables' as status;

-- =============================================
-- VERIFICATION: Check all applied tags
-- =============================================

-- View all table-level tags
SELECT 
    table_name,
    tag_name,
    tag_value,
    'Table-level' as tag_scope
FROM system.information_schema.table_tags 
WHERE schema_name = 'finance'
ORDER BY table_name, tag_name;

-- View all column-level tags
SELECT 
    table_name,
    column_name,
    tag_name,
    tag_value,
    'Column-level' as tag_scope
FROM system.information_schema.column_tags 
WHERE schema_name = 'finance'
ORDER BY table_name, column_name, tag_name;

-- Summary of tags by table
SELECT 
    table_name,
    COUNT(DISTINCT tag_name) as unique_tags,
    COUNT(*) as total_tags
FROM system.information_schema.table_tags 
WHERE schema_name = 'finance'
GROUP BY table_name
ORDER BY table_name;

-- Summary of column tags
SELECT 
    table_name,
    COUNT(DISTINCT column_name) as tagged_columns,
    COUNT(*) as total_column_tags
FROM system.information_schema.column_tags 
WHERE schema_name = 'finance'
GROUP BY table_name
ORDER BY table_name;

SELECT '✅ All finance ABAC tags applied successfully!' as status;
SELECT '📊 7 scenarios tagged: PCI-DSS, AML/KYC, Chinese Walls, Data Residency, Time-Based, Auditor Access, PII Privacy' as scenarios;
SELECT '🔐 Ready to create ABAC policies using 4.CreateFinanceABACPolicies.sql' as next_step;
