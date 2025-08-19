-- =============================================
-- DATABRICKS UNITY CATALOG ABAC MASKING FUNCTIONS
-- Updated Version with Configurable Catalog
-- Purpose: Attribute-Based Access Control (ABAC) utility functions for healthcare data masking
-- Reference: https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/
-- Usage: Set CATALOG_NAME variable before execution
-- =============================================

-- CONFIGURATION: Set your target catalog name here
-- Examples: 'apscat', 'main', 'your_catalog_name'
SET CATALOG_NAME = 'apscat';

-- Set catalog and schema context
USE CATALOG ${CATALOG_NAME};
USE SCHEMA healthcare;

-- =============================================
-- MASKING FUNCTIONS (9 total)
-- These transform/hide data values while preserving table structure
-- =============================================

-- =============================================
-- 1. PARTIAL STRING MASKING FUNCTION
-- Purpose: Show only first and last characters with middle masked
-- Usage: Patient names, addresses for partial visibility
-- Input: String value
-- Output: Partially masked string (e.g., J***n for John)
-- =============================================
CREATE OR REPLACE FUNCTION mask_string_partial(input STRING)
RETURNS STRING
COMMENT 'ABAC utility: Partial string masking showing first and last characters'
RETURN CASE 
    WHEN input IS NULL OR input = '' THEN input
    WHEN LENGTH(input) <= 2 THEN REPEAT('*', LENGTH(input))
    WHEN LENGTH(input) = 3 THEN CONCAT(LEFT(input, 1), '*', RIGHT(input, 1))
    ELSE CONCAT(LEFT(input, 1), REPEAT('*', LENGTH(input) - 2), RIGHT(input, 1))
END;

-- =============================================
-- 2. EMAIL MASKING FUNCTION
-- Purpose: Mask email addresses while preserving domain structure
-- Usage: Patient and provider email addresses
-- Input: Email string (e.g., john.doe@hospital.com)
-- Output: Masked email (e.g., ****@hospital.com)
-- =============================================
CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURNS STRING
COMMENT 'ABAC utility: Mask email local part while preserving domain'
RETURN CASE 
    WHEN email IS NULL OR email = '' THEN email
    WHEN LOCATE('@', email) > 0 THEN 
        CONCAT('****', SUBSTRING(email, LOCATE('@', email)))
    ELSE '****'
END;

-- =============================================
-- 3. PHONE NUMBER MASKING FUNCTION
-- Purpose: Mask phone numbers while preserving format
-- Usage: Patient and emergency contact phone numbers
-- Input: Phone string (e.g., 555-0123)
-- Output: Masked phone (e.g., XXXX0123)
-- =============================================
CREATE OR REPLACE FUNCTION mask_phone(phone STRING)
RETURNS STRING
COMMENT 'ABAC utility: Mask phone numbers while preserving format structure'
RETURN CASE 
    WHEN phone IS NULL OR phone = '' THEN phone
    WHEN LENGTH(phone) >= 4 THEN 
        CONCAT(REPEAT('X', LENGTH(phone) - 4), RIGHT(phone, 4))
    ELSE REPEAT('X', LENGTH(phone))
END;

-- =============================================
-- 4. ONE-WAY STRING MASKING FUNCTION
-- Purpose: Hash string values using SHA-256 for irreversible masking
-- Usage: Patient names, addresses, email domains for anonymization
-- Input: String value to be hashed
-- Output: SHA-256 hash string (64 characters)
-- =============================================
CREATE OR REPLACE FUNCTION mask_string_hash(input STRING)
RETURNS STRING
COMMENT 'ABAC utility: One-way hash masking using SHA-256 for complete anonymization'
RETURN sha2(input, 256);

-- =============================================
-- 5. DATE MASKING FUNCTION (YEAR ONLY)
-- Purpose: Mask date to show only year for age calculation
-- Usage: Date of birth masking while preserving year for demographics
-- Input: DATE value
-- Output: Date with January 1st of same year
-- =============================================
CREATE OR REPLACE FUNCTION mask_date_year_only(input_date DATE)
RETURNS DATE
COMMENT 'ABAC utility: Mask date to show only year (January 1st of same year)'
RETURN CASE 
    WHEN input_date IS NULL THEN NULL
    ELSE DATE(CONCAT(YEAR(input_date), '-01-01'))
END;

-- =============================================
-- 6. ADDRESS MASKING FUNCTION
-- Purpose: Mask street address while preserving city/state
-- Usage: Patient addresses for geographic analysis without full PII
-- Input: Full address string
-- Output: City and state only
-- =============================================
CREATE OR REPLACE FUNCTION mask_address_city_state(address STRING, city STRING, state STRING)
RETURNS STRING
COMMENT 'ABAC utility: Mask street address, show only city and state'
RETURN CASE 
    WHEN city IS NULL AND state IS NULL THEN '***'
    WHEN city IS NULL THEN state
    WHEN state IS NULL THEN city
    ELSE CONCAT(city, ', ', state)
END;

-- =============================================
-- 7. COMPLETE MASKING FUNCTION
-- Purpose: Completely mask any sensitive numeric column by returning NULL
-- Usage: PatientID, VisitID, or any numeric identifier that should be hidden
-- Input: Any DECIMAL value
-- Output: NULL (complete masking)
-- =============================================
CREATE OR REPLACE FUNCTION mask_for_all_roles(id DECIMAL)
RETURNS DECIMAL
COMMENT 'ABAC utility: Completely mask numeric values by returning NULL'
RETURN NULL;

-- =============================================
-- 8. DETERMINISTIC NUMERIC MASKING WITH REFERENTIAL INTEGRITY
-- Purpose: Mask numeric values while preserving referential relationships
-- Usage: Transform PatientID, ProviderID while maintaining join relationships
-- Input: DECIMAL value to be masked
-- Output: Deterministically transformed DECIMAL value
-- =============================================
CREATE OR REPLACE FUNCTION mask_decimal_referential(id DECIMAL)
RETURNS DECIMAL
COMMENT 'ABAC utility: Mask numeric values while preserving referential integrity'
RETURN id * fast_deterministic_multiplier(id);

-- =============================================
-- 9. FAST DETERMINISTIC MULTIPLIER HELPER FUNCTION
-- Purpose: Generate consistent multiplier for referential masking
-- Usage: Helper function for mask_decimal_referential
-- Input: DECIMAL value
-- Output: Consistent multiplier between 1.001 and 2.000
-- =============================================
CREATE OR REPLACE FUNCTION fast_deterministic_multiplier(id DECIMAL)
RETURNS DECIMAL
COMMENT 'ABAC utility: Generate deterministic multiplier for consistent masking'
RETURN 1 + MOD(CRC32(CAST(CAST(id AS STRING) AS BINARY)), 1000) * 0.001;

-- =============================================
-- ROW FILTER FUNCTIONS (7 total)
-- These return TRUE/FALSE to show/hide entire rows
-- Updated to work with ABAC policies (no is_account_group_member calls)
-- =============================================

-- =============================================
-- 10. TIME-BASED FILTER: BUSINESS HOURS
-- Purpose: Allow data access only during business hours (9 AM - 6 PM Melbourne time)
-- Usage: Time-based access control for sensitive healthcare operations
-- Output: TRUE during business hours, FALSE otherwise
-- =============================================
CREATE OR REPLACE FUNCTION business_hours_filter()
RETURNS BOOLEAN
COMMENT 'ABAC utility: Allow access only during business hours (9 AM - 6 PM Melbourne time)'
RETURN hour(from_utc_timestamp(current_timestamp(), 'Australia/Melbourne')) BETWEEN 9 AND 18;

-- =============================================
-- 11. EMERGENCY ACCESS FILTER
-- Purpose: Allow 24/7 access for emergency healthcare operations
-- Usage: Emergency access during off-hours, audit trail requirements
-- Output: TRUE (always allows access)
-- =============================================
CREATE OR REPLACE FUNCTION emergency_hours_access()
RETURNS BOOLEAN
COMMENT 'ABAC utility: Allow 24/7 access for emergency healthcare operations'
RETURN TRUE; -- Healthcare operates 24/7, but can be modified for specific use cases

-- =============================================
-- 12. NO ROWS FILTER
-- Purpose: Returns FALSE to filter out all rows (complete data hiding)
-- Usage: Row-level security to hide all data from unauthorized users
-- Output: FALSE (always hides all data)
-- =============================================
CREATE OR REPLACE FUNCTION no_rows()
RETURNS BOOLEAN
COMMENT 'ABAC utility: Returns FALSE to filter out all rows for complete data hiding'
RETURN FALSE;

-- =============================================
-- 13. HEALTHCARE ROLE FILTER (UPDATED FOR ABAC)
-- Purpose: Filter access based on healthcare roles and departments
-- Usage: Row-level security based on user roles and data sensitivity
-- Input: Data classification level
-- Output: Boolean for access permission (group membership handled by ABAC policy)
-- =============================================
CREATE OR REPLACE FUNCTION healthcare_role_filter(data_classification STRING)
RETURNS BOOLEAN
COMMENT 'ABAC utility: Healthcare role-based access control filter - group membership handled by ABAC policy'
RETURN CASE
    WHEN data_classification = 'PUBLIC' THEN TRUE
    WHEN data_classification = 'INTERNAL' THEN TRUE  -- ABAC policy will filter based on Healthcare_Staff group
    WHEN data_classification = 'CONFIDENTIAL' THEN TRUE  -- ABAC policy will filter based on Healthcare_Providers group
    WHEN data_classification = 'RESTRICTED' THEN TRUE  -- ABAC policy will filter based on Healthcare_Admins group
    ELSE FALSE
END;

-- =============================================
-- 14. HIPAA COMPLIANCE FILTER (UPDATED FOR ABAC)
-- Purpose: Apply HIPAA-compliant masking based on user clearance
-- Usage: Ensure HIPAA compliance for healthcare data access
-- Input: User clearance level
-- Output: Boolean for HIPAA-compliant access (group membership handled by ABAC policy)
-- =============================================
CREATE OR REPLACE FUNCTION hipaa_compliant_access(clearance_required STRING)
RETURNS BOOLEAN
COMMENT 'ABAC utility: HIPAA-compliant access control - group membership handled by ABAC policy'
RETURN CASE
    WHEN clearance_required = 'BASIC' THEN TRUE  -- ABAC policy will check Healthcare_Basic group
    WHEN clearance_required = 'ELEVATED' THEN TRUE  -- ABAC policy will check Healthcare_Elevated group
    WHEN clearance_required = 'ADMIN' THEN TRUE  -- ABAC policy will check Healthcare_Admin group
    ELSE FALSE
END;

-- =============================================
-- 15. SIMPLE ROW FILTER
-- Purpose: General purpose filter for basic row-level security
-- Usage: Simple row filtering where group-based filtering handled by ABAC policy
-- Output: TRUE (access control handled by ABAC policy)
-- =============================================
CREATE OR REPLACE FUNCTION simple_row_filter()
RETURNS BOOLEAN
COMMENT 'ABAC utility: Simple row filter - returns TRUE, group-based filtering handled by ABAC policy'
RETURN TRUE;

-- =============================================
-- 16. SENSITIVE DATA FILTER
-- Purpose: Filter for highly sensitive healthcare data
-- Usage: For patient records, lab results, prescriptions requiring special access
-- Output: TRUE (access control handled by ABAC policy)
-- =============================================
CREATE OR REPLACE FUNCTION sensitive_data_filter()
RETURNS BOOLEAN
COMMENT 'ABAC utility: Sensitive data filter - returns TRUE, access control handled by ABAC policy'
RETURN TRUE;

-- =============================================
-- FUNCTION TESTING AND VERIFICATION
-- =============================================

-- Test masking functions
SELECT 
    'mask_string_partial' as function_name,
    mask_string_partial('John Smith') as result
UNION ALL
SELECT 
    'mask_email',
    mask_email('john.smith@hospital.com')
UNION ALL
SELECT 
    'mask_phone',
    mask_phone('555-0123')
UNION ALL
SELECT 
    'mask_date_year_only',
    CAST(mask_date_year_only('1975-03-15') AS STRING)
UNION ALL
SELECT 
    'mask_address_city_state',
    mask_address_city_state('123 Main St', 'Seattle', 'WA')
UNION ALL
SELECT 
    'mask_for_all_roles',
    CAST(mask_for_all_roles(12345) AS STRING)
UNION ALL
SELECT 
    'mask_decimal_referential',
    CAST(mask_decimal_referential(12345) AS STRING)
UNION ALL
SELECT 
    'fast_deterministic_multiplier',
    CAST(fast_deterministic_multiplier(12345) AS STRING);

-- Test row filter functions
SELECT 
    'business_hours_filter' as function_name,
    CAST(business_hours_filter() AS STRING) as result
UNION ALL
SELECT 
    'emergency_hours_access',
    CAST(emergency_hours_access() AS STRING)
UNION ALL
SELECT 
    'no_rows',
    CAST(no_rows() AS STRING)
UNION ALL
SELECT 
    'simple_row_filter',
    CAST(simple_row_filter() AS STRING)
UNION ALL
SELECT 
    'sensitive_data_filter',
    CAST(sensitive_data_filter() AS STRING)
UNION ALL
SELECT 
    'healthcare_role_filter',
    CAST(healthcare_role_filter('CONFIDENTIAL') AS STRING)
UNION ALL
SELECT 
    'hipaa_compliant_access',
    CAST(hipaa_compliant_access('ELEVATED') AS STRING);

-- =============================================
-- EXAMPLE ABAC POLICY APPLICATIONS
-- =============================================

-- Example 1: Apply column masking to Patient names
-- ALTER TABLE Patients 
-- ALTER COLUMN FirstName 
-- SET MASK mask_string_partial(FirstName) 
-- USING ('Healthcare_Providers');

-- Example 2: Apply row filter for sensitive patient data
-- ALTER TABLE Patients 
-- SET ROW FILTER simple_row_filter() 
-- USING ('Healthcare_Staff');

-- Example 3: Time-based access for lab results
-- ALTER TABLE LabResults 
-- SET ROW FILTER business_hours_filter() 
-- USING ('Healthcare_Contractors');

-- Example 4: Email masking for patient privacy
-- ALTER TABLE Patients 
-- ALTER COLUMN Email 
-- SET MASK mask_email(Email) 
-- USING ('Healthcare_Basic');

-- Example 5: Phone number masking
-- ALTER TABLE Patients 
-- ALTER COLUMN PhoneNumber 
-- SET MASK mask_phone(PhoneNumber) 
-- USING ('Healthcare_Basic');

-- =============================================
-- FUNCTION INVENTORY SUMMARY
-- =============================================

-- Show all functions created in this schema
SHOW USER FUNCTIONS;

-- =============================================
-- DEPLOYMENT SUMMARY
-- =============================================
-- Successfully created 16 ABAC utility functions:
-- 
-- MASKING FUNCTIONS (9):
-- 1. mask_string_partial() - Partial name masking
-- 2. mask_email() - Email masking preserving domain
-- 3. mask_phone() - Phone number masking
-- 4. mask_string_hash() - SHA-256 hash masking
-- 5. mask_date_year_only() - Date masking to year only
-- 6. mask_address_city_state() - Address masking
-- 7. mask_for_all_roles() - Complete numeric masking
-- 8. mask_decimal_referential() - Referential integrity masking
-- 9. fast_deterministic_multiplier() - Helper for consistent transforms
--
-- ROW FILTER FUNCTIONS (7):
-- 10. business_hours_filter() - Time-based access control
-- 11. emergency_hours_access() - 24/7 healthcare access
-- 12. no_rows() - Complete data hiding
-- 13. healthcare_role_filter() - Role-based filtering
-- 14. hipaa_compliant_access() - HIPAA compliance filtering
-- 15. simple_row_filter() - General purpose filter
-- 16. sensitive_data_filter() - Sensitive data access control
--
-- All functions are catalog-agnostic and ready for ABAC policy deployment!
-- =============================================