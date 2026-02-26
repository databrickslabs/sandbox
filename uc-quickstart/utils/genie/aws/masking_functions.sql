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
COMMENT 'Masks middle characters, shows first and last character for names/identifiers'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, -1, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Masks ICD-10 code specifics, shows only category (first 3 characters)'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  ELSE CONCAT(SUBSTRING(code, 1, 3), '***')
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
COMMENT 'Row filter for US regional data access only'
RETURN current_user() LIKE '%_us@%' OR is_member('US_Regional_Access');

CREATE OR REPLACE FUNCTION filter_by_region_eu() 
RETURNS BOOLEAN
COMMENT 'Row filter for EU regional data access only'
RETURN current_user() LIKE '%_eu@%' OR is_member('EU_Regional_Access');

-- === louis_sydney.finance functions ===
USE CATALOG louis_sydney;
USE SCHEMA finance;

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character for names/identifiers'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, -1, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

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
COMMENT 'Masks email local part, preserves domain (@example.com)'
RETURN CASE 
  WHEN email IS NULL OR email NOT LIKE '%@%' THEN email
  ELSE CONCAT('****', SUBSTRING(email, INSTR(email, '@')))
END;

CREATE OR REPLACE FUNCTION mask_credit_card_full(card_number STRING)
RETURNS STRING
COMMENT 'Completely masks credit card number'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_credit_card_last4(card_number STRING)
RETURNS STRING
COMMENT 'Masks credit card showing only last 4 digits'
RETURN CASE 
  WHEN card_number IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(card_number, '[^0-9]', '')) >= 4 THEN 
    CONCAT('XXXX-XXXX-XXXX-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
  ELSE 'XXXX-XXXX-XXXX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Deterministic hash for account numbers to maintain referential integrity'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACC_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces sensitive content with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Returns NULL for highly sensitive data'
RETURN NULL;

CREATE OR REPLACE FUNCTION filter_by_region_us() 
RETURNS BOOLEAN
COMMENT 'Row filter for US regional data access only'
RETURN current_user() LIKE '%_us@%' OR is_member('US_Regional_Access');

CREATE OR REPLACE FUNCTION filter_by_region_eu() 
RETURNS BOOLEAN
COMMENT 'Row filter for EU regional data access only'
RETURN current_user() LIKE '%_eu@%' OR is_member('EU_Regional_Access');

CREATE OR REPLACE FUNCTION filter_trading_hours() 
RETURNS BOOLEAN
COMMENT 'Restricts access to trading data outside market hours'
RETURN HOUR(NOW()) < 9 OR HOUR(NOW()) > 16 OR DAYOFWEEK(NOW()) IN (1, 7);

CREATE OR REPLACE FUNCTION filter_audit_expiry() 
RETURNS BOOLEAN
COMMENT 'Temporary auditor access with expiration check'
RETURN current_date() <= '2024-12-31' AND is_member('External_Auditors');
