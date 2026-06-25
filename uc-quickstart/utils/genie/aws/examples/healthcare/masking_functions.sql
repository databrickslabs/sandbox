USE CATALOG <YOUR_CATALOG>;  -- replace with your catalog name
USE SCHEMA <YOUR_SCHEMA>;  -- replace with your schema name

-- === PII Masking ===

CREATE OR REPLACE FUNCTION mask_pii_partial(input STRING)
RETURNS STRING
COMMENT 'Masks middle characters; shows first and last character only.'
RETURN CASE
  WHEN input IS NULL THEN NULL
  WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
  ELSE CONCAT(LEFT(input, 1), REPEAT('*', LENGTH(input) - 2), RIGHT(input, 1))
END;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of SSN only.'
RETURN CASE
  WHEN ssn IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(ssn, '[^0-9]', '')) = 9 THEN
    CONCAT('XXX-XX-', RIGHT(REGEXP_REPLACE(ssn, '[^0-9]', ''), 4))
  ELSE 'XXX-XX-XXXX'
END;

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'Masks local part of email; preserves domain.'
RETURN CASE
  WHEN email IS NULL THEN NULL
  WHEN LOCATE('@', email) > 0 THEN
    CONCAT('****', SUBSTRING(email, LOCATE('@', email)))
  ELSE '****'
END;

CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'Shows last 4 digits of phone number.'
RETURN CASE
  WHEN phone IS NULL THEN NULL
  WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '')) >= 4 THEN
    CONCAT('***-***-', RIGHT(REGEXP_REPLACE(phone, '[^0-9]', ''), 4))
  ELSE '***-***-****'
END;

CREATE OR REPLACE FUNCTION mask_redact(input STRING)
RETURNS STRING
COMMENT 'Fully redacts the value.'
RETURN CASE
  WHEN input IS NULL THEN NULL
  ELSE '[REDACTED]'
END;

-- === Health / PHI Masking ===

CREATE OR REPLACE FUNCTION mask_mrn(mrn STRING)
RETURNS STRING
COMMENT 'Masks MRN; shows last 4 characters.'
RETURN CASE
  WHEN mrn IS NULL THEN NULL
  WHEN LENGTH(mrn) <= 4 THEN REPEAT('*', LENGTH(mrn))
  ELSE CONCAT(REPEAT('*', LENGTH(mrn) - 4), RIGHT(mrn, 4))
END;

CREATE OR REPLACE FUNCTION mask_diagnosis_code(code STRING)
RETURNS STRING
COMMENT 'Shows ICD-10 category (first 3 chars); hides specifics.'
RETURN CASE
  WHEN code IS NULL THEN NULL
  WHEN LENGTH(code) <= 3 THEN code
  WHEN LOCATE('.', code) > 0 THEN
    CONCAT(SUBSTRING(code, 1, LOCATE('.', code)), 'XX')
  ELSE CONCAT(LEFT(code, 3), '.XX')
END;

-- === Financial Masking ===

CREATE OR REPLACE FUNCTION mask_amount_rounded(amount DECIMAL(18,2))
RETURNS DECIMAL(18,2)
COMMENT 'Rounds to nearest 100 for approximate visibility.'
RETURN CASE
  WHEN amount IS NULL THEN NULL
  WHEN amount < 100 THEN ROUND(amount, -1)
  ELSE ROUND(amount, -2)
END;

CREATE OR REPLACE FUNCTION mask_account_number(account_id STRING)
RETURNS STRING
COMMENT 'Replaces with deterministic SHA-256 token.'
RETURN CASE
  WHEN account_id IS NULL THEN NULL
  ELSE CONCAT('ACCT-', LEFT(SHA2(account_id, 256), 12))
END;

-- === Row Filters ===

CREATE OR REPLACE FUNCTION filter_facility_us_east()
RETURNS BOOLEAN
COMMENT 'Row filter: only US_EAST facility data visible to regional staff.'
RETURN
  is_account_group_member('US_East_Staff')
  OR is_account_group_member('Chief_Medical_Officer');

CREATE OR REPLACE FUNCTION filter_facility_us_west()
RETURNS BOOLEAN
COMMENT 'Row filter: only US_WEST facility data visible to regional staff.'
RETURN
  is_account_group_member('US_West_Staff')
  OR is_account_group_member('Chief_Medical_Officer');
