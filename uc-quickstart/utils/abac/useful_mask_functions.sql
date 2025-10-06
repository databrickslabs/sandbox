-- ================================
-- ROW FILTER FUNCTIONS
-- ================================

-- Completely filters out all rows for users.
-- Use this for highly restricted tables that should not be accessed by any role.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.no_rows()
RETURNS BOOLEAN
RETURN FALSE;

-- Allows access to rows only during business hours (9 AM to 6 PM AEST).
-- Useful for enforcing time-based access policies, such as offshore team restrictions.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.business_hours_filter()
RETURNS BOOLEAN
RETURN hour(from_utc_timestamp(current_timestamp(), 'Australia/Melbourne')) BETWEEN 9 AND 18;

-- ================================
-- COLUMN MASKING FUNCTIONS
-- ================================

-- Masks sensitive column for all roles. Always returns NULL.
-- Suitable for use with highly confidential fields like SSN or tax ID.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.mask_for_all_roles(id DECIMAL)
RETURNS DECIMAL
RETURN NULL;

-- Deterministic masking for referential integrity joins.
-- Enables join compatibility while keeping actual values hidden.
-- Useful when joining on masked columns without exposing raw values.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.mask_decimal_p_referential(id DECIMAL)
RETURNS DECIMAL
RETURN 
id * t3_a00cd1_snd_arg02_dbws01.ext_parquet.fast_deterministic_multiplier(id);

-- High-performance deterministic multiplier function.
-- Applies a transformation based on CRC32 hash of the ID cast to binary.
-- Ensures output is consistent for the same input while being non-reversible.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.fast_deterministic_multiplier(id DECIMAL)
RETURNS DECIMAL
RETURN 1 + MOD(CRC32(CAST(CAST(id AS STRING) AS BINARY)), 1000) * 0.001;

-- One-way masking function for string inputs.
-- Uses SHA-256 for irreversible obfuscation of fields such as emails or usernames.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.mask_nz_string(input STRING)
RETURNS STRING
RETURN sha2(input, 256);

-- ================================
-- CONDITIONAL ACCESS POLICIES
-- ================================

-- Combines time-based and region-based row-level access control.
-- Grants access only until 2025-12-31 and only for users in specific groups.
-- Note: Currently hardcoded end date; consider parameterizing for reuse.
CREATE OR REPLACE FUNCTION t3_a00cd1_snd_arg02_dbws01.ext_parquet.rlf_country_filter_expiring_2025(
  ca_country STRING
)
RETURNS BOOLEAN
RETURN CASE
  WHEN CURRENT_DATE <= DATE('2025-12-31') THEN
    CASE
      WHEN ca_country = 'Australia' THEN is_account_group_member('AU_Viewers')
      WHEN ca_country = 'New Zealand' THEN is_account_group_member('NZ_Viewers')
      ELSE FALSE
    END
  ELSE FALSE
END;
