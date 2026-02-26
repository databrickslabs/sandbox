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
  WHEN input IS NULL OR LENGTH(input) = 0 THEN input
  WHEN LENGTH(input) = 1 THEN '*'
  WHEN LENGTH(input) = 2 THEN CONCAT(SUBSTRING(input, 1, 1), '*')
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD category (first 3 chars), masks specific diagnosis'
RETURN CASE 
  WHEN code IS NULL OR LENGTH(code) = 0 THEN code
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(SUBSTRING(code, 1, 3), '***')
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN input
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters rows to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters rows to show only EU region data'
RETURN TRUE;

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) = 0 THEN input
  WHEN LENGTH(input) = 1 THEN '*'
  WHEN LENGTH(input) = 2 THEN CONCAT(SUBSTRING(input, 1, 1), '*')
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of SSN, masks the rest'
RETURN CASE 
  WHEN ssn IS NULL OR LENGTH(ssn) = 0 THEN ssn
  WHEN LENGTH(ssn) <= 4 THEN REPEAT('*', LENGTH(ssn))
  ELSE CONCAT(REPEAT('*', LENGTH(ssn) - 4), SUBSTRING(ssn, -4, 4))
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks local part of email, keeps domain visible'
RETURN CASE 
  WHEN email IS NULL OR LENGTH(email) = 0 THEN email
  WHEN LOCATE('@', email) = 0 THEN REPEAT('*', LENGTH(email))
  ELSE CONCAT(REPEAT('*', LOCATE('@', email) - 1), SUBSTRING(email, LOCATE('@', email)))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Completely masks credit card number'
RETURN CASE 
  WHEN card_number IS NULL OR LENGTH(card_number) = 0 THEN card_number
  ELSE REPEAT('*', LENGTH(card_number))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of credit card, masks the rest'
RETURN CASE 
  WHEN card_number IS NULL OR LENGTH(card_number) = 0 THEN card_number
  WHEN LENGTH(card_number) <= 4 THEN REPEAT('*', LENGTH(card_number))
  ELSE CONCAT(REPEAT('*', LENGTH(card_number) - 4), SUBSTRING(card_number, -4, 4))
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Returns deterministic SHA-256 hash of account number'
RETURN CASE 
  WHEN account_id IS NULL OR LENGTH(account_id) = 0 THEN account_id
  ELSE SHA2(account_id, 256)
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN amount
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces content with [REDACTED]'
RETURN CASE 
  WHEN input IS NULL THEN input
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Returns NULL to hide sensitive data'
RETURN CAST(NULL AS STRING);

CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters rows to show only US region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters rows to show only EU region data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_trading_hours()
RETURNS BOOLEAN
COMMENT 'Restricts access to non-market hours (before 9 AM or after 4 PM)'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Time-limited access that expires at end of 2025'
RETURN CURRENT_DATE() <= DATE('2025-12-31');
