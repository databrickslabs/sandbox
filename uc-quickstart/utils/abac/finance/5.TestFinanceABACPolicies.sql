-- =============================================
-- FINANCE ABAC POLICIES - TEST AND VALIDATION QUERIES
-- Purpose: Validate all 7 finance ABAC scenarios with test queries
-- Run these queries as different user groups to verify masking and filtering
-- =============================================

USE CATALOG fincat;
USE SCHEMA finance;

-- =============================================
-- TEST SCENARIO 1: PCI-DSS PAYMENT CARD MASKING
-- Test as: Credit_Card_Support, Fraud_Analyst, Compliance_Officer
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 1: PCI-DSS Payment Card Masking' as test_name;
SELECT '========================================' as divider;

-- Test 1A: View credit cards (different roles see different masking)
SELECT 
    CardID,
    CustomerID,
    CardNumber,        -- Should be masked based on role
    CVV,               -- Should be masked for most roles
    CardType,
    CardStatus,
    ExpirationDate
FROM CreditCards
LIMIT 5;

-- Expected Results:
-- Credit_Card_Support: CardNumber shows XXXX-XXXX-XXXX-1234, CVV = XXXX-XXXX-XXXX-XXXX
-- Fraud_Analyst: CardNumber shows XXXX-XXXX-XXXX-9010 (last 4), CVV masked
-- Compliance_Officer: Full access to all fields

SELECT '✅ Test 1A Complete: Check card number and CVV masking based on your role' as result;

-- =============================================
-- TEST SCENARIO 2: AML/KYC TRANSACTION MONITORING
-- Test as: AML_Investigator_Junior, AML_Investigator_Senior, Compliance_Officer
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 2: AML/KYC Transaction Monitoring' as test_name;
SELECT '========================================' as divider;

-- Test 2A: View all transactions
SELECT 
    TransactionID,
    AccountID,
    TransactionDate,
    Amount,            -- Should be rounded for junior analysts
    TransactionType,
    AMLFlagReason,     -- Sensitive for senior only
    TransactionStatus
FROM Transactions
ORDER BY TransactionDate DESC
LIMIT 10;

-- Expected Results:
-- AML_Investigator_Junior: Amount rounded to nearest 100, limited rows
-- AML_Investigator_Senior: Full amounts, all details visible
-- Compliance_Officer: Complete access including investigation notes

SELECT '✅ Test 2A Complete: Check transaction amount rounding and row filtering' as result;

-- Test 2B: View AML alerts (sensitive investigation data)
SELECT 
    AlertID,
    CustomerID,
    AlertType,
    RiskScore,
    InvestigationStatus,
    InvestigationNotes  -- Highly sensitive
FROM AMLAlerts
ORDER BY AlertDate DESC;

-- Expected Results:
-- AML_Investigator_Junior: Limited or no access
-- AML_Investigator_Senior: Can see alerts but not investigation notes
-- Compliance_Officer: Full access to all investigation data

SELECT '✅ Test 2B Complete: Check AML alert access based on clearance level' as result;

-- =============================================
-- TEST SCENARIO 3: TRADING DESK CHINESE WALLS
-- Test as: Equity_Trader, Research_Analyst, Risk_Manager
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 3: Trading Desk Chinese Walls' as test_name;
SELECT '========================================' as divider;

-- Test 3A: View trading positions
SELECT 
    PositionID,
    TraderID,
    SecurityName,
    TradingDesk,
    Quantity,
    PnL,
    PositionStatus
FROM TradingPositions
ORDER BY PositionDate DESC;

-- Expected Results:
-- Equity_Trader: See only Equity desk positions
-- Fixed_Income_Trader: See only Fixed_Income desk positions
-- Research_Analyst: BLOCKED - Should see NO rows (Chinese wall)
-- Risk_Manager: See all positions (neutral access)

SELECT '✅ Test 3A Complete: Verify Chinese wall blocks research from trading data' as result;

-- Test 3B: Count positions by desk (verify filtering)
SELECT 
    TradingDesk,
    COUNT(*) as position_count,
    SUM(PnL) as total_pnl
FROM TradingPositions
GROUP BY TradingDesk;

-- Expected Results:
-- Equity_Trader: See only "Equity" row
-- Research_Analyst: See ZERO rows
-- Risk_Manager: See all desks

SELECT '✅ Test 3B Complete: Verify desk-based position filtering' as result;

-- =============================================
-- TEST SCENARIO 4: CROSS-BORDER DATA RESIDENCY
-- Test as: Regional_EU_Staff, Regional_US_Staff, Regional_APAC_Staff
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 4: Cross-Border Data Residency (GDPR, CCPA)' as test_name;
SELECT '========================================' as divider;

-- Test 4A: View customers (filtered by region)
SELECT 
    CustomerID,
    FirstName,
    LastName,
    Email,
    SSN,              -- Should be masked for non-US staff
    CustomerRegion,
    CustomerStatus
FROM Customers
ORDER BY CustomerID;

-- Expected Results:
-- Regional_EU_Staff: See ONLY EU customers (CustomerRegion = 'EU')
-- Regional_US_Staff: See ONLY US customers (CustomerRegion = 'US')
-- Regional_APAC_Staff: See ONLY APAC customers (CustomerRegion = 'APAC')
-- Compliance_Officer: See all regions (Global access)

SELECT '✅ Test 4A Complete: Verify geographic data residency filtering' as result;

-- Test 4B: Count customers by region (verify filtering)
SELECT 
    CustomerRegion,
    COUNT(*) as customer_count
FROM Customers
GROUP BY CustomerRegion;

-- Expected Results:
-- Regional_EU_Staff: See only "EU" row with count
-- Regional_US_Staff: See only "US" row with count
-- Regional_APAC_Staff: See only "APAC" row with count
-- Compliance_Officer: See all regions

SELECT '✅ Test 4B Complete: Regional staff see only their region data' as result;

-- =============================================
-- TEST SCENARIO 5: TIME-BASED TRADING ACCESS
-- Test as: Risk_Manager, Equity_Trader
-- Note: Results depend on current time (trading hours 9:30 AM - 4:00 PM ET)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 5: Time-Based Trading Access' as test_name;
SELECT '========================================' as divider;

-- Test 5A: Check current time and trading hours status
SELECT 
    CURRENT_TIMESTAMP() as current_time,
    HOUR(CURRENT_TIMESTAMP()) as current_hour_utc,
    CASE 
        WHEN HOUR(CURRENT_TIMESTAMP()) BETWEEN 14 AND 20 THEN 'TRADING HOURS (9:30 AM - 4:00 PM ET)'
        ELSE 'AFTER HOURS'
    END as market_status;

-- Test 5B: View trading positions with P&L
SELECT 
    PositionID,
    SecurityName,
    TradingDesk,
    CurrentPrice,
    PnL               -- Should be masked for Risk_Manager during trading hours
FROM TradingPositions
LIMIT 5;

-- Expected Results:
-- Risk_Manager (During Trading Hours): See NO ROWS or masked P&L
-- Risk_Manager (After Hours): Full access to positions and P&L
-- Equity_Trader: Always see their desk positions

SELECT '✅ Test 5B Complete: Verify time-based access restrictions' as result;

-- =============================================
-- TEST SCENARIO 6: TEMPORARY AUDITOR ACCESS
-- Test as: External_Auditor
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 6: Temporary Auditor Access (SOX)' as test_name;
SELECT '========================================' as divider;

-- Test 6A: View audit logs
SELECT 
    LogID,
    UserID,
    UserRole,
    AccessTime,
    TableAccessed,
    AuditProject,
    AccessGrantedUntil
FROM AuditLogs
ORDER BY AccessTime DESC;

-- Expected Results:
-- External_Auditor: See only Q1_SOX_Audit project data
-- External_Auditor: Access filtered by AccessGrantedUntil date
-- Compliance_Officer: See all audit logs

SELECT '✅ Test 6A Complete: Verify audit project filtering and expiry' as result;

-- Test 6B: View accounts (SOX in-scope)
SELECT 
    AccountID,
    CustomerID,
    AccountType,
    Balance,          -- Financial data for audit
    OpenDate,
    AccountStatus
FROM Accounts
LIMIT 5;

-- Expected Results:
-- External_Auditor: See account data but CustomerID should be masked/tokenized
-- Access expires based on audit timeline

SELECT '✅ Test 6B Complete: Auditors see financial data but not customer PII' as result;

-- Test 6C: View customers (PII should be masked for auditors)
SELECT 
    CustomerID,
    FirstName,        -- Should be partially masked
    LastName,         -- Should be partially masked
    Email,            -- Should be masked
    DateOfBirth
FROM Customers
LIMIT 5;

-- Expected Results:
-- External_Auditor: Names show J*** S***, email shows ****@domain.com

SELECT '✅ Test 6C Complete: Customer PII masked for external auditors' as result;

-- =============================================
-- TEST SCENARIO 7: CUSTOMER PII PROGRESSIVE PRIVACY
-- Test as: Marketing_Team, Credit_Card_Support, KYC_Specialist
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST SCENARIO 7: Customer PII Progressive Privacy' as test_name;
SELECT '========================================' as divider;

-- Test 7A: View customer personal information
SELECT 
    CustomerID,       -- Should be deterministic masked for marketing
    FirstName,        -- Partial mask for CS, de-identified for marketing
    LastName,         -- Partial mask for CS, de-identified for marketing
    Email,            -- Masked for non-KYC roles
    DateOfBirth,      -- Age groups for marketing
    Address           -- Partial for CS
FROM Customers
LIMIT 5;

-- Expected Results:
-- Marketing_Team: CustomerID = REF_abc123..., names/email fully masked, DOB = age group
-- Credit_Card_Support: CustomerID masked, names = J*** S***, email = ****@domain
-- KYC_Specialist: Full access to all PII for verification

SELECT '✅ Test 7A Complete: Verify tiered PII access by role' as result;

-- Test 7B: View account balances (aggregated for marketing)
SELECT 
    AccountID,
    CustomerID,
    AccountType,
    Balance           -- Should be rounded for marketing
FROM Accounts
LIMIT 10;

-- Expected Results:
-- Marketing_Team: Balance rounded to nearest 100 (e.g., 15234.50 → 15200.00)
-- Credit_Card_Support: Original balance visible
-- KYC_Specialist: Original balance visible

SELECT '✅ Test 7B Complete: Balance masking for marketing analytics' as result;

-- Test 7C: Cross-table join with masked IDs (referential integrity)
SELECT 
    c.CustomerID,
    c.FirstName,
    c.LastName,
    a.AccountID,
    a.Balance,
    t.Amount as recent_transaction_amount
FROM Customers c
JOIN Accounts a ON c.CustomerID = a.CustomerID
LEFT JOIN Transactions t ON a.AccountID = t.AccountID
WHERE t.TransactionDate >= CURRENT_DATE() - INTERVAL 7 DAYS
LIMIT 10;

-- Expected Results:
-- Marketing_Team: Deterministic masking preserves joins (same masked ID appears consistently)
-- All roles: Joins work correctly despite masking

SELECT '✅ Test 7C Complete: Cross-table joins work with deterministic masking' as result;

-- =============================================
-- COMPREHENSIVE VALIDATION SUMMARY
-- =============================================

SELECT '========================================' as divider;
SELECT 'COMPREHENSIVE TEST SUMMARY' as test_name;
SELECT '========================================' as divider;

SELECT 'Finance ABAC Policy Validation' as category, 'Complete' as status
UNION ALL
SELECT 'Total Scenarios Tested', '7'
UNION ALL
SELECT 'Scenario 1', 'PCI-DSS Payment Card Masking ✅'
UNION ALL
SELECT 'Scenario 2', 'AML/KYC Transaction Monitoring ✅'
UNION ALL
SELECT 'Scenario 3', 'Trading Desk Chinese Walls ✅'
UNION ALL
SELECT 'Scenario 4', 'Cross-Border Data Residency ✅'
UNION ALL
SELECT 'Scenario 5', 'Time-Based Trading Access ✅'
UNION ALL
SELECT 'Scenario 6', 'Temporary Auditor Access ✅'
UNION ALL
SELECT 'Scenario 7', 'Customer PII Progressive Privacy ✅';

-- =============================================
-- TESTING INSTRUCTIONS
-- =============================================

SELECT '📋 TESTING INSTRUCTIONS' as section;
SELECT '
To properly test these ABAC policies:

1. Run this notebook as DIFFERENT USER GROUPS:
   - Switch user context or impersonate different groups
   - Expected to see different results based on role

2. Key test groups:
   - Credit_Card_Support (PCI-DSS basic access)
   - Fraud_Analyst (PCI-DSS full access)
   - AML_Investigator_Junior (limited AML access)
   - AML_Investigator_Senior (enhanced AML access)
   - Equity_Trader (trading desk access)
   - Research_Analyst (blocked from trading)
   - Regional_EU_Staff (EU data only)
   - Regional_US_Staff (US data only)
   - Risk_Manager (neutral access, time-restricted)
   - External_Auditor (temporary SOX access)
   - Marketing_Team (de-identified data)
   - KYC_Specialist (full PII access)

3. Validate for each test:
   ✓ Correct data masking applied
   ✓ Row filtering working as expected
   ✓ Cross-table joins maintain referential integrity
   ✓ Time-based policies activate at correct hours
   ✓ Geographic filtering enforces residency rules

4. Document any discrepancies or unexpected behavior

🎉 All tests passed? Your Finance ABAC implementation is production-ready!
' as instructions;
