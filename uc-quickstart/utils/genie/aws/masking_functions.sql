-- ============================================================================
-- GENERATED MASKING FUNCTIONS (FIRST DRAFT)
-- ============================================================================
-- Target(s): louis_sydney.clinical, louis_sydney.finance
-- Next: review generated/TUNING.md, tune if needed, then run this SQL.
-- ============================================================================

-- === louis_sydney.clinical functions ===
USE CATALOG louis_sydney;
USE SCHEMA clinical;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, 3, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD category (first 3 chars), masks specific diagnosis'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(SUBSTRING(code, 1, 3), '***')
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU region data'
RETURN TRUE;

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, 3, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, LENGTH(input), 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of SSN, masks the rest'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) < 4 THEN '***-**-****'
  ELSE CONCAT('***-**-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks local part of email, keeps domain visible'
RETURN CASE 
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+$' THEN email
  ELSE CONCAT('****@', SUBSTRING(email, INSTR(email, '@') + 1))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Completely masks credit card number'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  ELSE '****-****-****-****'
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of credit card, masks the rest'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) < 4 THEN '****-****-****-****'
  ELSE CONCAT('****-****-****-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Creates deterministic hash token for account numbers'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACC_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_hash(input STRING)
RETURNS STRING
COMMENT 'Returns SHA-256 hash of input'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE SHA2(input, 256)
END;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_trading_hours()
RETURNS BOOLEAN
COMMENT 'Restricts access to non-trading hours (before 9 AM or after 4 PM)'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Time-limited access that expires at end of 2025'
RETURN CURRENT_DATE() <= DATE('2025-12-31');
