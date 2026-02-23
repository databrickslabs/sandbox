-- =============================================
-- DATABRICKS UNITY CATALOG - FINANCE DOMAIN DATABASE SCHEMA
-- Purpose: Create comprehensive financial services database for ABAC demonstrations
-- Compliance: PCI-DSS, AML/KYC, GDPR, SOX, GLBA
-- Tables: Customers, Accounts, Transactions, CreditCards, TradingPositions, AMLAlerts, AuditLogs
-- =============================================

USE CATALOG fincat;

USE SCHEMA finance;

-- =============================================
-- TABLE 1: CUSTOMERS
-- Purpose: Core customer master data with PII
-- Compliance: GDPR, GLBA, CCPA
-- =============================================
DROP TABLE IF EXISTS Customers;

CREATE TABLE Customers (
    CustomerID STRING NOT NULL,
    FirstName STRING,
    LastName STRING,
    Email STRING,
    SSN STRING COMMENT 'Social Security Number - PII/Sensitive',
    DateOfBirth DATE,
    Address STRING,
    City STRING,
    State STRING,
    ZipCode STRING,
    CustomerRegion STRING COMMENT 'Data residency region: EU, US, APAC, LATAM',
    AccountOpenDate DATE,
    CustomerStatus STRING COMMENT 'Active, Suspended, Closed',
    RiskScore INT COMMENT 'AML risk score 1-100',
    KYCVerificationDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Customer master data with PII for GDPR/GLBA compliance demonstrations'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

-- Insert sample customer data
INSERT INTO Customers VALUES
    ('CUST00001', 'John', 'Smith', 'john.smith@email.com', '123-45-6789', '1975-03-15', '123 Main St', 'New York', 'NY', '10001', 'US', '2020-01-15', 'Active', 25, '2020-01-10', CURRENT_TIMESTAMP()),
    ('CUST00002', 'Maria', 'Garcia', 'maria.garcia@email.com', '234-56-7890', '1982-07-22', '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'US', '2019-05-20', 'Active', 15, '2019-05-15', CURRENT_TIMESTAMP()),
    ('CUST00003', 'Hans', 'Mueller', 'hans.mueller@email.de', '345-67-8901', '1990-11-08', 'Berliner Str 78', 'Berlin', 'BE', '10115', 'EU', '2021-03-10', 'Active', 10, '2021-03-05', CURRENT_TIMESTAMP()),
    ('CUST00004', 'Sophie', 'Dubois', 'sophie.dubois@email.fr', '456-78-9012', '1988-02-14', '12 Rue de Paris', 'Paris', 'IDF', '75001', 'EU', '2020-08-25', 'Active', 20, '2020-08-20', CURRENT_TIMESTAMP()),
    ('CUST00005', 'Wei', 'Chen', 'wei.chen@email.cn', '567-89-0123', '1985-09-30', '88 Nanjing Rd', 'Shanghai', 'SH', '200001', 'APAC', '2021-11-12', 'Active', 30, '2021-11-10', CURRENT_TIMESTAMP()),
    ('CUST00006', 'Sarah', 'Johnson', 'sarah.j@email.com', '678-90-1234', '1992-05-18', '789 Pine St', 'Chicago', 'IL', '60601', 'US', '2022-02-14', 'Active', 12, '2022-02-10', CURRENT_TIMESTAMP()),
    ('CUST00007', 'Carlos', 'Silva', 'carlos.silva@email.br', '789-01-2345', '1978-12-03', 'Av Paulista 1000', 'Sao Paulo', 'SP', '01310', 'LATAM', '2019-09-08', 'Active', 45, '2019-09-05', CURRENT_TIMESTAMP()),
    ('CUST00008', 'Yuki', 'Tanaka', 'yuki.tanaka@email.jp', '890-12-3456', '1995-06-25', '1-1-1 Shibuya', 'Tokyo', 'TK', '150-0001', 'APAC', '2022-07-19', 'Active', 8, '2022-07-15', CURRENT_TIMESTAMP()),
    ('CUST00009', 'Emma', 'Wilson', 'emma.wilson@email.co.uk', '901-23-4567', '1987-04-12', '10 Downing St', 'London', 'LDN', 'SW1A', 'EU', '2020-12-05', 'Suspended', 75, '2020-12-01', CURRENT_TIMESTAMP()),
    ('CUST00010', 'Ahmed', 'Al-Saud', 'ahmed.alsaud@email.sa', '012-34-5678', '1983-08-20', 'King Fahd Rd', 'Riyadh', 'RY', '11564', 'APAC', '2021-06-30', 'Active', 55, '2021-06-25', CURRENT_TIMESTAMP());

-- =============================================
-- TABLE 2: ACCOUNTS
-- Purpose: Bank accounts linked to customers
-- Compliance: GLBA, regional banking regulations
-- =============================================
DROP TABLE IF EXISTS Accounts;

CREATE TABLE Accounts (
    AccountID STRING NOT NULL,
    CustomerID STRING NOT NULL,
    AccountType STRING COMMENT 'Checking, Savings, Investment, Credit',
    Balance DECIMAL(18,2),
    Currency STRING DEFAULT 'USD',
    OpenDate DATE,
    AccountStatus STRING COMMENT 'Active, Frozen, Closed',
    AccountRegion STRING COMMENT 'Region where account is held',
    InterestRate DECIMAL(5,4),
    LastTransactionDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Bank account information for balance and transaction tracking'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO Accounts VALUES
    ('ACC1001', 'CUST00001', 'Checking', 15234.50, 'USD', '2020-01-15', 'Active', 'US', 0.0125, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1002', 'CUST00001', 'Savings', 45678.90, 'USD', '2020-01-15', 'Active', 'US', 0.0350, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1003', 'CUST00002', 'Checking', 8945.75, 'USD', '2019-05-20', 'Active', 'US', 0.0125, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1004', 'CUST00003', 'Checking', 12456.30, 'EUR', '2021-03-10', 'Active', 'EU', 0.0100, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1005', 'CUST00003', 'Investment', 78900.00, 'EUR', '2021-06-15', 'Active', 'EU', 0.0000, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1006', 'CUST00004', 'Savings', 23567.85, 'EUR', '2020-08-25', 'Active', 'EU', 0.0300, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1007', 'CUST00005', 'Checking', 34567.20, 'CNY', '2021-11-12', 'Active', 'APAC', 0.0200, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1008', 'CUST00006', 'Checking', 5678.40, 'USD', '2022-02-14', 'Active', 'US', 0.0125, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1009', 'CUST00007', 'Savings', 67890.50, 'BRL', '2019-09-08', 'Active', 'LATAM', 0.0650, '2026-02-08', CURRENT_TIMESTAMP()),
    ('ACC1010', 'CUST00009', 'Checking', 2345.60, 'GBP', '2020-12-05', 'Frozen', 'EU', 0.0150, '2026-02-08', CURRENT_TIMESTAMP());

-- =============================================
-- TABLE 3: TRANSACTIONS (RECREATED FOR FRAUD AI DEMO)
-- Purpose: Transaction history for AML monitoring + AI reasoning
-- Compliance: AML/KYC, FATF, FinCEN
-- =============================================

DROP TABLE IF EXISTS Transactions;

CREATE TABLE Transactions (
    TransactionID STRING NOT NULL,
    AccountID STRING NOT NULL,
    TransactionDate TIMESTAMP,
    Amount DECIMAL(18,2),
    Currency STRING DEFAULT 'USD',
    TransactionType STRING COMMENT 'Deposit, Withdrawal, Transfer, Payment',
    CountryCode STRING COMMENT 'Country where transaction originated',
    MerchantName STRING,
    TransactionStatus STRING COMMENT 'Completed, Pending, Flagged, Blocked',
    AMLFlagReason STRING COMMENT 'Large transaction, Cross-border, Suspicious pattern',

    -- Added for AI-driven fraud explanation
    IsInternational BOOLEAN COMMENT 'TRUE if transaction is cross-border',
    ExceedsHighRiskThreshold BOOLEAN COMMENT 'TRUE if amount exceeds high-risk threshold (e.g. >= 10000)',

    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Transaction history for AML/KYC monitoring and fraud investigation with AI context'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO Transactions VALUES
-- Normal domestic payments
('TXN000001', 'ACC1001', '2026-02-08 14:35:22', 234.50, 'USD', 'Payment', 'US', 'Amazon.com', 'Completed', NULL, FALSE, FALSE, CURRENT_TIMESTAMP()),
('TXN000002', 'ACC1001', '2026-02-08 09:12:45', 1500.00, 'USD', 'Deposit', 'US', 'Payroll Direct Deposit', 'Completed', NULL, FALSE, FALSE, CURRENT_TIMESTAMP()),
('TXN000008', 'ACC1002', '2026-02-08 10:15:55', 500.00, 'USD', 'Payment', 'US', 'Utility Bill', 'Completed', NULL, FALSE, FALSE, CURRENT_TIMESTAMP()),
('TXN000010', 'ACC1008', '2026-02-08 12:05:33', 78.90, 'USD', 'Payment', 'US', 'Coffee Shop', 'Completed', NULL, FALSE, FALSE, CURRENT_TIMESTAMP()),

-- Large but explainable withdrawals (kept)
('TXN000003', 'ACC1003', '2026-02-08 16:20:10', 15000.00, 'USD', 'Withdrawal', 'US', 'Cash Withdrawal ATM', 'Flagged', 'Large transaction', FALSE, TRUE, CURRENT_TIMESTAMP()),

-- Existing international transfers (kept)
('TXN000004', 'ACC1004', '2026-02-08 11:45:30', 8500.00, 'EUR', 'Transfer', 'DE', 'International Wire', 'Completed', NULL, TRUE, FALSE, CURRENT_TIMESTAMP()),
('TXN000005', 'ACC1007', '2026-02-08 08:30:15', 25000.00, 'CNY', 'Transfer', 'CN', 'Business Payment', 'Completed', NULL, TRUE, TRUE, CURRENT_TIMESTAMP()),

-- High-risk cash activity (kept)
('TXN000006', 'ACC1009', '2026-02-08 19:55:40', 45000.00, 'BRL', 'Deposit', 'BR', 'Large Cash Deposit', 'Flagged', 'Large transaction', FALSE, TRUE, CURRENT_TIMESTAMP()),

-- Existing blocked transfer (kept)
('TXN000007', 'ACC1010', '2026-02-08 14:22:18', 12000.00, 'GBP', 'Transfer', 'GB', 'Suspicious Transfer', 'Blocked', 'Suspicious pattern', TRUE, TRUE, CURRENT_TIMESTAMP()),

-- Investment-related transfer (kept)
('TXN000009', 'ACC1005', '2026-02-08 15:40:25', 12500.00, 'EUR', 'Transfer', 'FR', 'Investment Purchase', 'Completed', NULL, TRUE, TRUE, CURRENT_TIMESTAMP()),

-- =============================================
-- DEMO: TWO TOP URGENT ALERT TRANSACTIONS (NEW)
-- =============================================

-- ✅ DEMO #1 (Customer aware / reasonable): large first-time international transfer for CUST00001
('TXN_DEMO_01', 'ACC1001', '2026-02-08 08:30:00', 18000.00, 'USD', 'Transfer', 'DE', 'International Wire - Property Settlement', 'Flagged', 'Cross-border', TRUE, TRUE, CURRENT_TIMESTAMP()),

-- 🚨 DEMO #2 (Customer unreachable): large international transfer for CUST00009 (already Frozen account ACC1010)
('TXN_DEMO_02', 'ACC1010', '2026-02-08 08:40:00', 22000.00, 'GBP', 'Transfer', 'GB', 'International Wire - Beneficiary Added Recently', 'Blocked', 'Suspicious pattern', TRUE, TRUE, CURRENT_TIMESTAMP());

-- =============================================
-- TABLE 4: CREDIT CARDS
-- Purpose: Credit card information for PCI-DSS compliance
-- Compliance: PCI-DSS
-- =============================================
DROP TABLE IF EXISTS CreditCards;

CREATE TABLE CreditCards (
    CardID STRING NOT NULL,
    CustomerID STRING NOT NULL,
    CardNumber STRING COMMENT 'Full card number - PCI-DSS Sensitive',
    CVV STRING COMMENT 'Card Verification Value - PCI-DSS Sensitive',
    ExpirationDate STRING,
    CardType STRING COMMENT 'Visa, Mastercard, Amex, Discover',
    CardStatus STRING COMMENT 'Active, Blocked, Expired',
    CreditLimit DECIMAL(18,2),
    CurrentBalance DECIMAL(18,2),
    LastUsedDate DATE,
    IssueDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Credit card master data for PCI-DSS compliance demonstrations'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO CreditCards VALUES
    ('CARD0001', 'CUST00001', '4532-1234-5678-9010', '123', '12/2026', 'Visa', 'Active', 10000.00, 2345.60, '2026-02-08', '2020-01-15', CURRENT_TIMESTAMP()),
    ('CARD0002', 'CUST00002', '5425-2345-6789-0123', '456', '06/2025', 'Mastercard', 'Active', 5000.00, 1234.50, '2026-02-08', '2019-05-20', CURRENT_TIMESTAMP()),
    ('CARD0003', 'CUST00003', '3782-456789-01234', '789', '09/2027', 'Amex', 'Active', 15000.00, 5678.90, '2026-02-08', '2021-03-10', CURRENT_TIMESTAMP()),
    ('CARD0004', 'CUST00004', '6011-3456-7890-1234', '234', '03/2026', 'Discover', 'Active', 8000.00, 3456.70, '2026-02-08', '2020-08-25', CURRENT_TIMESTAMP()),
    ('CARD0005', 'CUST00005', '4916-4567-8901-2345', '567', '11/2025', 'Visa', 'Active', 12000.00, 4567.80, '2026-02-08', '2021-11-12', CURRENT_TIMESTAMP()),
    ('CARD0006', 'CUST00006', '5500-5678-9012-3456', '890', '05/2026', 'Mastercard', 'Active', 3000.00, 567.90, '2026-02-08', '2022-02-14', CURRENT_TIMESTAMP()),
    ('CARD0007', 'CUST00007', '4485-6789-0123-4567', '321', '08/2027', 'Visa', 'Active', 20000.00, 12345.00, '2026-02-08', '2019-09-08', CURRENT_TIMESTAMP()),
    ('CARD0008', 'CUST00009', '5425-7890-1234-5678', '654', '02/2024', 'Mastercard', 'Blocked', 7000.00, 6789.50, '2026-02-08', '2020-12-05', CURRENT_TIMESTAMP());

-- =============================================
-- TABLE 5: TRADING POSITIONS
-- Purpose: Trading desk positions for Chinese wall enforcement
-- Compliance: SEC, MiFID II, insider trading prevention
-- =============================================
DROP TABLE IF EXISTS TradingPositions;

CREATE TABLE TradingPositions (
    PositionID STRING NOT NULL,
    TraderID STRING NOT NULL COMMENT 'User ID of trader',
    SecurityID STRING NOT NULL COMMENT 'Stock ticker or security identifier',
    SecurityName STRING,
    Quantity INT,
    EntryPrice DECIMAL(18,4),
    CurrentPrice DECIMAL(18,4),
    PnL DECIMAL(18,2) COMMENT 'Profit and Loss',
    TradingDesk STRING COMMENT 'Equity, Fixed_Income, FX, Commodities',
    PositionDate DATE,
    PositionStatus STRING COMMENT 'Open, Closed',
    InformationBarrier STRING COMMENT 'Trading_Side, Advisory_Side, Neutral',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Trading positions for Chinese wall and insider trading prevention'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO TradingPositions VALUES
    ('POS00001', 'TRADER001', 'AAPL', 'Apple Inc', 1000, 150.25, 175.50, 25250.00, 'Equity', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP()),
    ('POS00002', 'TRADER001', 'GOOGL', 'Alphabet Inc', 500, 2800.00, 2950.75, 75375.00, 'Equity', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP()),
    ('POS00003', 'TRADER002', 'TSLA', 'Tesla Inc', 2000, 185.50, 165.25, -40500.00, 'Equity', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP()),
    ('POS00004', 'TRADER003', 'US10Y', 'US 10-Year Treasury', 10000000, 98.50, 99.25, 75000.00, 'Fixed_Income', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP()),
    ('POS00005', 'TRADER004', 'EURUSD', 'Euro/US Dollar', 5000000, 1.0850, 1.0920, 35000.00, 'FX', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP()),
    ('POS00006', 'TRADER005', 'GC', 'Gold Futures', 100, 2050.00, 2075.50, 2550.00, 'Commodities', '2026-02-08', 'Open', 'Trading_Side', CURRENT_TIMESTAMP());

-- =============================================
-- TABLE 6: AML ALERTS
-- Purpose: Anti-Money Laundering alert management
-- Compliance: AML/KYC, FATF, FinCEN
-- =============================================
DROP TABLE IF EXISTS AMLAlerts;

CREATE TABLE AMLAlerts (
    AlertID STRING NOT NULL,
    CustomerID STRING NOT NULL,
    TransactionID STRING,
    AlertDate TIMESTAMP,
    AlertType STRING COMMENT 'Large Transaction, Structuring, Cross-Border, Rapid Movement',
    RiskScore INT COMMENT '1-100 risk assessment',
    InvestigationStatus STRING COMMENT 'New, Under Review, Escalated, Cleared, SAR Filed',
    AssignedInvestigator STRING,
    InvestigationNotes STRING COMMENT 'Sensitive investigation details',
    ResolutionDate TIMESTAMP,
    SARFiled BOOLEAN COMMENT 'Suspicious Activity Report filed with FinCEN',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'AML alerts and investigation tracking for compliance monitoring'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO AMLAlerts VALUES
-- ✅ DEMO #1 (Customer aware) - still urgent but slightly lower than DEMO #2
(
  'AML_DEMO_01',
  'CUST00001',
  'TXN_DEMO_01',
  '2026-02-08 09:00:00',
  'Cross-Border',
  88,
  'Under Review',
  'AML_INV_DEMO',
  'First-time large international transfer flagged by threshold and cross-border controls',
  NULL,
  FALSE,
  CURRENT_TIMESTAMP()
),

-- 🚨 DEMO #2 (Customer unreachable) - highest urgency
(
  'AML_DEMO_02',
  'CUST00009',
  'TXN_DEMO_02',
  '2026-02-08 09:05:00',
  'Cross-Border',
  92,
  'Under Review',
  'AML_INV_DEMO',
  'Large international transfer blocked; account is frozen and customer could not be reached',
  NULL,
  FALSE,
  CURRENT_TIMESTAMP()
);
-- =============================================
-- TABLE 7: AUDIT LOGS
-- Purpose: Audit trail for SOX compliance
-- Compliance: SOX, regulatory audit requirements
-- =============================================
DROP TABLE IF EXISTS AuditLogs;

CREATE TABLE AuditLogs (
    LogID STRING NOT NULL,
    UserID STRING NOT NULL,
    UserRole STRING,
    AccessTime TIMESTAMP,
    TableAccessed STRING,
    OperationType STRING COMMENT 'SELECT, INSERT, UPDATE, DELETE',
    RecordsAffected INT,
    AuditProject STRING COMMENT 'Q1_SOX_Audit, Annual_Financial_Audit, Regulatory_Review',
    AccessGrantedUntil DATE COMMENT 'Temporary access expiration date',
    IPAddress STRING,
    SessionID STRING,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Audit log for access tracking and SOX compliance'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO AuditLogs VALUES
    ('LOG00001', 'auditor@external.com', 'External_Auditor', '2026-02-08 10:30:00', 'Accounts', 'SELECT', 150, 'Q1_SOX_Audit', '2026-02-08', '203.0.113.25', 'SESS_A1B2C3', CURRENT_TIMESTAMP()),
    ('LOG00002', 'compliance@company.com', 'Compliance_Officer', '2026-02-08 14:20:00', 'AMLAlerts', 'SELECT', 45, 'Regulatory_Review', '2026-02-08', '198.51.100.42', 'SESS_D4E5F6', CURRENT_TIMESTAMP()),
    ('LOG00003', 'analyst@company.com', 'AML_Investigator_Senior', '2026-02-08 09:15:00', 'Transactions', 'SELECT', 8932, NULL, '2026-02-08', '192.0.2.15', 'SESS_G7H8I9', CURRENT_TIMESTAMP()),
    ('LOG00004', 'support@company.com', 'Credit_Card_Support', '2026-02-08 11:45:00', 'CreditCards', 'SELECT', 23, NULL, '2026-02-08', '198.51.100.87', 'SESS_J1K2L3', CURRENT_TIMESTAMP());

DROP TABLE IF EXISTS CustomerInteractions;

CREATE TABLE CustomerInteractions (
    InteractionID STRING NOT NULL,
    CustomerID STRING NOT NULL,
    InteractionTime TIMESTAMP,
    Channel STRING COMMENT 'Call, Chat, Email',
    AgentID STRING,
    InteractionNotes STRING COMMENT 'Free-text customer interaction notes',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'Customer interaction history used for fraud investigation context'
TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported');

INSERT INTO CustomerInteractions VALUES
-- ✅ Customer aware -> approve/monitor
(
  'INT_DEMO_01',
  'CUST00001',
  '2026-02-08 08:45:00',
  'Call',
  'AGENT_101',
  'Customer confirmed the international transfer was intentional and related to an overseas property purchase. Customer acknowledged the amount and destination account.',
  CURRENT_TIMESTAMP()
),

-- 🚨 Customer unreachable -> escalate
(
  'INT_DEMO_02',
  'CUST00009',
  '2026-02-08 08:50:00',
  'Call',
  'AGENT_102',
  'Multiple attempts were made to contact the customer regarding the international transfer. No response was received and the customer could not be reached.',
  CURRENT_TIMESTAMP()
);

-- =============================================
-- VERIFICATION
-- =============================================

-- Show all created tables
SHOW TABLES IN finance;

-- Display row counts
SELECT 'Customers' as table_name, COUNT(*) as row_count FROM Customers
UNION ALL
SELECT 'Accounts', COUNT(*) FROM Accounts
UNION ALL
SELECT 'Transactions', COUNT(*) FROM Transactions
UNION ALL
SELECT 'CreditCards', COUNT(*) FROM CreditCards
UNION ALL
SELECT 'TradingPositions', COUNT(*) FROM TradingPositions
UNION ALL
SELECT 'AMLAlerts', COUNT(*) FROM AMLAlerts
UNION ALL
SELECT 'AuditLogs', COUNT(*) FROM AuditLogs
ORDER BY table_name;

SELECT '✅ Successfully created 7 finance tables with sample data' as status;
SELECT '📊 Tables: Customers, Accounts, Transactions, CreditCards, TradingPositions, AMLAlerts, AuditLogs' as tables_created;
SELECT '🔐 Ready for: PCI-DSS, AML/KYC, GDPR, SOX, GLBA compliance demonstrations' as compliance_ready;


-- Show the two top urgent alerts
SELECT
  a.AlertID,
  a.AlertDate,
  a.RiskScore,
  a.InvestigationStatus,
  a.CustomerID,
  a.TransactionID
FROM AMLAlerts a
ORDER BY a.RiskScore DESC, a.AlertDate DESC;

-- Verify both demo transactions exist and are international + exceed threshold
SELECT
  TransactionID,
  AccountID,
  TransactionDate,
  Amount,
  Currency,
  CountryCode,
  TransactionStatus,
  AMLFlagReason,
  IsInternational,
  ExceedsHighRiskThreshold
FROM Transactions
WHERE TransactionID IN ('TXN_DEMO_01', 'TXN_DEMO_02')
ORDER BY TransactionDate;

-- Verify interactions exist for both customers
SELECT
  CustomerID,
  InteractionTime,
  Channel,
  AgentID,
  InteractionNotes
FROM CustomerInteractions
ORDER BY InteractionTime DESC;
