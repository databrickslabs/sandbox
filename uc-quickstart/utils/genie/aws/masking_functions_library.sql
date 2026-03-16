-- ============================================================================
-- REUSABLE MASKING FUNCTIONS LIBRARY
-- ============================================================================
-- A categorized library of masking UDFs for Unity Catalog ABAC.
-- Pick the functions you need, find-replace {catalog}.{schema} with your own,
-- then execute only the selected functions in your Databricks workspace.
--
-- Categories:
--   PII        : Personal identifiable information masking
--   Financial  : Credit card, account number, monetary amounts
--   Health     : Medical record numbers, diagnosis codes
--   General    : Redact, hash, nullify utilities
--   Row Filters: Region-based, time-based, audit filters
-- ============================================================================

USE CATALOG {catalog};
USE SCHEMA {schema};

-- ============================================================================
-- PII MASKING FUNCTIONS
-- ============================================================================

-- Partial PII masking: show first and last character, mask the middle.
-- Input:  "John"        -> "J**n"
-- Input:  "alice@x.com" -> "a*********m"
CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Partial PII masking — first and last character visible, middle masked. Use for names, addresses, or any short PII string.'
RETURN CASE
    WHEN input IS NULL OR input = '' THEN input
    WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
    WHEN LENGTH(input) = 3 THEN CONCAT(LEFT(input, 1), '*', RIGHT(input, 1))
    ELSE CONCAT(LEFT(input, 1), REPEAT('*', LENGTH(input) - 2), RIGHT(input, 1))
END;

-- SSN masking: show last 4 digits.
-- Input:  "123-45-6789" -> "XXX-XX-6789"
CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Mask SSN showing only last 4 digits. Use for US Social Security Numbers (GLBA/CCPA).'
RETURN CASE
    WHEN ssn IS NULL OR ssn = '' THEN ssn
    WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) = 9 THEN
        CONCAT('XXX-XX-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
    ELSE 'XXX-XX-XXXX'
END;

-- Email masking: preserve domain, mask local part.
-- Input:  "john.doe@example.com" -> "****@example.com"
CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Mask email local part, preserve domain. Use for GDPR/privacy-compliant email display.'
RETURN CASE
    WHEN email IS NULL OR email = '' THEN email
    WHEN LOCATE('@', email) > 0 THEN
        CONCAT('****', SUBSTRING(email, LOCATE('@', email)))
    ELSE '****'
END;

-- Phone number masking: show last 4 digits.
-- Input:  "+1-555-123-4567" -> "***-***-4567"
CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Mask phone number showing only last 4 digits.'
RETURN CASE
    WHEN phone IS NULL OR phone = '' THEN phone
    WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '')) >= 4 THEN
        CONCAT('***-***-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
    ELSE '***-***-****'
END;

-- Full name masking: first initial + last initial.
-- Input:  "John Doe" -> "J. D."
CREATE OR REPLACE FUNCTION mask_full_name(name STRING)
RETURNS STRING
COMMENT 'Reduce full name to initials. Use for anonymized reporting.'
RETURN CASE
    WHEN name IS NULL OR name = '' THEN name
    WHEN LOCATE(' ', name) > 0 THEN
        CONCAT(LEFT(name, 1), '. ', LEFT(SUBSTRING(name, LOCATE(' ', name) + 1), 1), '.')
    ELSE CONCAT(LEFT(name, 1), '.')
END;

-- ============================================================================
-- FINANCIAL MASKING FUNCTIONS
-- ============================================================================

-- Full credit card masking.
-- Input:  "4532-1234-5678-9010" -> "XXXX-XXXX-XXXX-XXXX"
CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Full credit card masking for PCI-DSS compliance. All digits hidden.'
RETURN CASE
    WHEN card_number IS NULL OR card_number = '' THEN card_number
    ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

-- Credit card last 4 digits visible.
-- Input:  "4532-1234-5678-9010" -> "XXXX-XXXX-XXXX-9010"
CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Show last 4 digits of credit card. Use for customer verification (PCI-DSS).'
RETURN CASE
    WHEN card_number IS NULL OR card_number = '' THEN card_number
    WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) >= 4 THEN
        CONCAT('XXXX-XXXX-XXXX-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
    ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

-- Account number tokenization (deterministic hash).
-- Input:  "ACC123456" -> "ACCT_a3f9c2b1e8d7"
CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Deterministic account number tokenization via SHA-256. Preserves join capability across tables.'
RETURN CASE
    WHEN account_id IS NULL OR account_id = '' THEN account_id
    ELSE CONCAT('ACCT_', LEFT(SHA2(account_id, 256), 12))
END;

-- Transaction amount rounding.
-- Input:  1234.56 -> 1200.00
-- Input:  42.50   -> 40.00
CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Round amounts to nearest 10 (< $100) or 100 (>= $100). Use for aggregated analytics.'
RETURN CASE
    WHEN amount IS NULL THEN NULL
    WHEN amount < 100 THEN ROUND(amount, -1)
    ELSE ROUND(amount, -2)
END;

-- IBAN masking: show country code + last 4.
-- Input:  "DE89370400440532013000" -> "DE**************3000"
CREATE OR REPLACE FUNCTION mask_iban(iban STRING)
RETURNS STRING
COMMENT 'Mask IBAN showing country code and last 4 digits. Use for EU banking compliance.'
RETURN CASE
    WHEN iban IS NULL OR iban = '' THEN iban
    WHEN LENGTH(iban) > 6 THEN
        CONCAT(LEFT(iban, 2), REPEAT('*', LENGTH(iban) - 6), RIGHT(iban, 4))
    ELSE REPEAT('*', LENGTH(iban))
END;

-- ============================================================================
-- HEALTH MASKING FUNCTIONS
-- ============================================================================

-- Medical Record Number masking.
-- Input:  "MRN-12345678" -> "MRN-****5678"
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Mask medical record number showing only last 4 digits. Use for HIPAA compliance.'
RETURN CASE
    WHEN mrn IS NULL OR mrn = '' THEN mrn
    WHEN LENGTH(mrn) > 4 THEN
        CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
    ELSE REPEAT('*', LENGTH(mrn))
END;

-- ICD/diagnosis code masking: show category, hide specifics.
-- Input:  "E11.65" -> "E11.XX"
CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Mask diagnosis code sub-category. Shows ICD category but hides specifics for de-identification.'
RETURN CASE
    WHEN code IS NULL OR code = '' THEN code
    WHEN LOCATE('.', code) > 0 THEN
        CONCAT(SUBSTRING(code, 1, LOCATE('.', code)), 'XX')
    ELSE code
END;

-- ============================================================================
-- GENERAL UTILITY MASKING FUNCTIONS
-- ============================================================================

-- Full redaction: replace with a fixed string.
-- Input:  "anything" -> "[REDACTED]"
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Full redaction — replaces any value with [REDACTED]. Use for maximum restriction.'
RETURN CASE
    WHEN input IS NULL THEN NULL
    ELSE '[REDACTED]'
END;

-- Deterministic hash: SHA-256 for consistent pseudonymization.
-- Input:  "john@x.com" -> "a7f3c9e2b1d4..."
CREATE OR REPLACE FUNCTION mask_hash(input STRING)
RETURNS STRING
COMMENT 'SHA-256 deterministic hash. Use for pseudonymization that preserves join capability.'
RETURN CASE
    WHEN input IS NULL OR input = '' THEN input
    ELSE SHA2(input, 256)
END;

-- Nullify: return NULL regardless of input.
-- Input:  "anything" -> NULL
CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Return NULL for any input. Use when the column should be completely invisible.'
RETURN NULL;

-- ============================================================================
-- ROW FILTER FUNCTIONS (zero-argument for Unity Catalog ABAC)
-- ============================================================================
-- UC row filter policies require zero-argument functions.
-- The policy's WHEN clause controls which tables the filter applies to.

-- Regional filter — US data only.
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Row filter: restrict to US customer data (CCPA/GLBA). Apply via WHEN hasTagValue on region tag.'
RETURN TRUE;

-- Regional filter — EU data only.
CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Row filter: restrict to EU customer data (GDPR). Apply via WHEN hasTagValue on region tag.'
RETURN TRUE;

-- Regional filter — APAC data only.
CREATE OR REPLACE FUNCTION filter_by_region_apac()
RETURNS BOOLEAN
COMMENT 'Row filter: restrict to APAC customer data (PDPA). Apply via WHEN hasTagValue on region tag.'
RETURN TRUE;

-- Trading hours filter.
CREATE OR REPLACE FUNCTION filter_trading_hours()
RETURNS BOOLEAN
COMMENT 'Row filter: restrict access to outside NYSE trading hours (9:30 AM - 4:00 PM ET).'
RETURN CASE
    WHEN hour(current_timestamp()) < 14 OR hour(current_timestamp()) >= 21 THEN TRUE
    ELSE FALSE
END;

-- Audit expiry filter.
CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Row filter: temporary access for external auditors. Apply via WHEN hasTagValue on audit tag.'
RETURN TRUE;
