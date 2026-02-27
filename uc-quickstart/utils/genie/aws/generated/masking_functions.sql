-- ============================================================================
-- GENERATED MASKING FUNCTIONS (FIRST DRAFT)
-- ============================================================================
-- Target(s): louis_sydney.clinical, louis_sydney.finance
-- Next: review generated/TUNING.md, tune if needed, then run this SQL.
-- ============================================================================

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
