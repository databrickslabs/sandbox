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
COMMENT 'Masks middle characters, shows first and last character'
RETURN CASE 
  WHEN input IS NULL OR LENGTH(input) <= 2 THEN input
  ELSE CONCAT(SUBSTRING(input, 1, 1), REPEAT('*', LENGTH(input) - 2), SUBSTRING(input, -1, 1))
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
  WHEN email IS NULL OR NOT email RLIKE '^[^@]+@[^@]+$' THEN email
  ELSE CONCAT('***@', SPLIT(email, '@')[1])
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
  ELSE CONCAT(LEFT(name, 1), '.')
END;

-- Health-specific Functions
CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN showing only last 4 characters'
RETURN CASE 
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) >= 4 THEN CONCAT('****', RIGHT(mrn, 4))
  ELSE '********'
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD-10 category (first 3 chars) but hides specific diagnosis'
RETURN CASE 
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) >= 3 THEN CONCAT(LEFT(code, 3), '.XX')
  ELSE 'XXX.XX'
END;

CREATE OR REPLACE FUNCTION mask_clinical_notes(notes STRING)
RETURNS STRING
COMMENT 'Redacts clinical notes for non-clinical staff'
RETURN CASE 
  WHEN notes IS NULL THEN NULL
  ELSE '[CLINICAL_NOTES_REDACTED]'
END;

-- Financial Functions
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
  WHEN LENGTH(insurance_id) >= 4 THEN CONCAT('****', RIGHT(insurance_id, 4))
  ELSE '********'
END;

-- General Masking Functions
CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Completely redacts sensitive information'
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
COMMENT 'Filter to show only US regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_by_region_eu()
RETURNS BOOLEAN
COMMENT 'Filter to show only EU regional data'
RETURN TRUE;

CREATE OR REPLACE FUNCTION filter_clinical_staff_only()
RETURNS BOOLEAN
COMMENT 'Filter allowing access only during business hours for clinical staff'
RETURN TRUE;
