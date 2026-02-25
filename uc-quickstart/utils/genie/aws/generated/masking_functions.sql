-- ============================================================================
-- GENERATED MASKING FUNCTIONS (FIRST DRAFT)
-- ============================================================================
-- Target: louis_sydney.clinical
-- Next: review generated/TUNING.md, tune if needed, then run this SQL.
-- ============================================================================

USE CATALOG louis_sydney;
USE SCHEMA clinical;

-- PII Masking Functions
CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters, shows first and last character only'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  WHEN LENGTH(input) = 3 THEN CONCAT(SUBSTRING(input, 1, 1), '*', SUBSTRING(input, -1, 1))
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Masks SSN showing only last 4 digits: XXX-XX-1234'
RETURN CASE 
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) >= 4 THEN 
    CONCAT('XXX-XX-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
  ELSE 'XXX-XX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks email local part, preserves domain: j***@domain.com'
RETURN CASE 
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+$' THEN email
  ELSE CONCAT(
    SUBSTRING(SPLIT(email, '@')[0], 1, 1),
    REPEAT('*', GREATEST(LENGTH(SPLIT(email, '@')[0]) - 1, 3)),
    '@',
    SPLIT(email, '@')[1]
  )
END;

CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Masks phone number showing only last 4 digits: XXX-XXX-1234'
RETURN CASE 
  WHEN phone IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '')) >= 4 THEN 
    CONCAT('XXX-XXX-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
  ELSE 'XXX-XXX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_full_name(name STRING)
RETURNS STRING
COMMENT 'Reduces full name to initials: John Smith -> J.S.'
RETURN CASE 
  WHEN name IS NULL THEN NULL
  ELSE CONCAT_WS('.', 
    ARRAY_JOIN(
      TRANSFORM(
        SPLIT(TRIM(name), ' '), 
        x -> SUBSTRING(x, 1, 1)
      ), 
      '.'
    ),
    '.'
  )
END;

-- Health-Specific Masking Functions
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN showing only last 4 characters: ****1234'
RETURN CASE 
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) >= 4 THEN CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
  ELSE REPEAT('*', LENGTH(mrn))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Masks ICD-10 specifics, shows category: I25.10 -> I25.XX'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN code RLIKE '^[A-Z][0-9]{2}\\.' THEN CONCAT(SUBSTRING(code, 1, 4), 'XX')
  WHEN code RLIKE '^[A-Z][0-9]{2}' THEN CONCAT(SUBSTRING(code, 1, 3), '.XX')
  ELSE 'XXX.XX'
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_desc(description STRING)
RETURNS STRING
COMMENT 'Masks diagnosis description to general category'
RETURN CASE 
  WHEN description IS NULL THEN NULL
  ELSE '[DIAGNOSIS CATEGORY REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_treatment_notes(notes STRING)
RETURNS STRING
COMMENT 'Redacts clinical notes completely'
RETURN CASE 
  WHEN notes IS NULL THEN NULL
  ELSE '[CLINICAL NOTES REDACTED]'
END;

-- Financial Masking Functions
CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds financial amounts to nearest $100 for privacy'
RETURN CASE 
  WHEN amount IS NULL THEN NULL
  ELSE ROUND(amount / 100.0, 0) * 100.0
END;

CREATE OR REPLACE FUNCTION mask_insurance_id(insurance_id STRING)
RETURNS STRING
COMMENT 'Masks insurance ID showing only last 4 characters'
RETURN CASE 
  WHEN insurance_id IS NULL THEN NULL
  WHEN LENGTH(insurance_id) >= 4 THEN CONCAT(REPEAT('*', LENGTH(insurance_id) - 4), RIGHT(insurance_id, 4))
  ELSE REPEAT('*', LENGTH(insurance_id))
END;

-- General Masking Functions
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Completely redacts sensitive content'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

CREATE OR REPLACE FUNCTION mask_hash(input STRING)
RETURNS STRING
COMMENT 'Returns SHA-256 hash for deterministic anonymization'
RETURN CASE 
  WHEN input IS NULL THEN NULL
  ELSE SHA2(input, 256)
END;

-- Row Filter Functions
CREATE OR REPLACE FUNCTION filter_by_region_us()
RETURNS BOOLEAN
COMMENT 'Row filter for US-only data access'
RETURN TRUE; -- Implement based on user context or session variables

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Row filter for EU-only data access'
RETURN TRUE; -- Implement based on user context or session variables

CREATE OR REPLACE FUNCTION filter_audit_expiry()
RETURNS BOOLEAN
COMMENT 'Temporary auditor access with expiration logic'
RETURN CURRENT_DATE() <= DATE('2024-12-31'); -- Example expiry date
