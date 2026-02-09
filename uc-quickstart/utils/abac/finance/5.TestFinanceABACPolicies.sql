-- =============================================
-- FINANCE ABAC - TEST QUERIES (Minimal 5 Scenarios)
-- Run as different user groups to validate masking and row filters
-- Groups: Junior_Analyst, Senior_Analyst, US_Region_Staff, EU_Region_Staff, Compliance_Officer
-- =============================================

USE CATALOG fincat;
USE SCHEMA finance;

-- =============================================
-- TEST 1: PII MASKING (Customers)
-- Test as: Junior_Analyst (masked), Senior_Analyst (unmasked), Compliance_Officer (unmasked)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST 1: PII Masking (Customers)' as test_name;
SELECT '========================================' as divider;

SELECT
    CustomerID,
    FirstName,
    LastName,
    Email,
    SSN,
    CustomerRegion
FROM Customers
LIMIT 5;

-- Expected: Junior_Analyst -> masked FirstName, LastName, Email, SSN (e.g. ***). Senior + Compliance -> full values.
SELECT 'Test 1 complete: Check PII masking for your role' as result;

-- =============================================
-- TEST 2: FRAUD / CARD (CreditCards)
-- Test as: Junior_Analyst (last-4), Senior_Analyst (full card, CVV masked), Compliance_Officer (full + CVV)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST 2: Fraud / Card (CreditCards)' as test_name;
SELECT '========================================' as divider;

SELECT
    CardID,
    CustomerID,
    CardNumber,
    CVV,
    CardType,
    ExpirationDate
FROM CreditCards
LIMIT 5;

-- Expected: Junior -> XXXX-XXXX-XXXX-1234, CVV masked. Senior -> full CardNumber, CVV masked. Compliance -> full CardNumber + CVV.
SELECT 'Test 2 complete: Check card masking for your role' as result;

-- =============================================
-- TEST 3: FRAUD / TRANSACTIONS (Amount)
-- Test as: Junior_Analyst (rounded), Senior_Analyst (full), Compliance_Officer (full)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST 3: Fraud / Transactions (Amount)' as test_name;
SELECT '========================================' as divider;

SELECT
    TransactionID,
    AccountID,
    TransactionDate,
    Amount,
    TransactionType,
    TransactionStatus
FROM Transactions
ORDER BY TransactionDate DESC
LIMIT 10;

-- Expected: Junior -> Amount rounded (e.g. 1200.00). Senior + Compliance -> exact Amount.
SELECT 'Test 3 complete: Check transaction amount for your role' as result;

-- =============================================
-- TEST 4: US REGION (Row filter)
-- Test as: US_Region_Staff (should see only CustomerRegion = 'US' rows)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST 4: US Region (US_Region_Staff)' as test_name;
SELECT '========================================' as divider;

SELECT CustomerID, FirstName, LastName, CustomerRegion
FROM Customers
ORDER BY CustomerRegion;

-- Expected when run as US_Region_Staff: Only rows where CustomerRegion = 'US'. Other roles may see all regions.
SELECT 'Test 4 complete: US_Region_Staff should see only US rows' as result;

-- =============================================
-- TEST 5: EU REGION (Row filter)
-- Test as: EU_Region_Staff (should see only CustomerRegion = 'EU' rows)
-- =============================================

SELECT '========================================' as divider;
SELECT 'TEST 5: EU Region (EU_Region_Staff)' as test_name;
SELECT '========================================' as divider;

SELECT CustomerID, FirstName, LastName, CustomerRegion
FROM Customers
ORDER BY CustomerRegion;

-- Expected when run as EU_Region_Staff: Only rows where CustomerRegion = 'EU'. Other roles may see all regions.
SELECT 'Test 5 complete: EU_Region_Staff should see only EU rows' as result;

-- =============================================
-- SUMMARY
-- =============================================

SELECT 'Minimal 5-scenario tests complete. Run as Junior_Analyst, Senior_Analyst, US_Region_Staff, EU_Region_Staff, Compliance_Officer to validate.' as summary;
