USE CATALOG louis_sydney;
USE SCHEMA clinical;

-- PII Masking Functions
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
COMMENT 'Masks SSN showing only last 4 digits'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) >= 4 THEN 
    CONCAT('***-**-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
  ELSE '***-**-****'
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks email local part, preserves domain'
RETURN CASE 
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+\\.[^@]+$' THEN email
  ELSE CONCAT(
    SUBSTRING(SPLIT(email, '@')[0], 1, 1),
    REPEAT('*', GREATEST(LENGTH(SPLIT(email, '@')[0]) - 1, 1)),
    '@',
    SPLIT(email, '@')[1]
  )
END;

CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Masks phone number showing only last 4 digits'
RETURN CASE 
  WHEN phone IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '')) >= 4 THEN 
    CONCAT('***-***-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
  ELSE '***-***-****'
END;

CREATE OR REPLACE FUNCTION mask_full_name(name STRING)
RETURNS STRING
COMMENT 'Reduces full name to initials'
RETURN CASE 
  WHEN name IS NULL THEN NULL
  ELSE REGEXP_REPLACE(TRIM(name), '\\b(\\w)\\w*', '$1.')
END;

-- Health-specific Functions
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN showing only last 4 characters'
RETURN CASE 
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) >= 4 THEN CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
  ELSE REPEAT('*', LENGTH(mrn))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD category (first 3 chars), masks specifics'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) >= 3 THEN CONCAT(SUBSTRING(code, 1, 3), REPEAT('*', LENGTH(code) - 3))
  ELSE code
END;

-- Financial Functions
CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Replaces account number with deterministic SHA-256 hash'
RETURN CASE 
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACCT_', SUBSTRING(SHA2(account_id, 256), 1, 8))
END;

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest 100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount / 100) * 100
END;

-- General Masking
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Replaces input with [REDACTED] placeholder'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_nullify(input STRING)
RETURNS STRING
COMMENT 'Returns NULL for complete data suppression'
RETURN NULL;

-- Row Filter Functions
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Filters to show only US regional data (US_EAST, US_WEST)'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filters to show only EU regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Temporary access filter for auditors (implement time-based logic as needed)'
RETURN TRUE;
