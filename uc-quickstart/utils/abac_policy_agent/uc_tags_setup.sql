-- ================================================================
-- UNITY CATALOG ABAC POLICIES IMPLEMENTATION
-- Based on existing Unity Catalog demo with enterprise governance
-- ================================================================

-- Prerequisites:
-- 1. Enable ABAC in workspace: Admin > Previews > Attribute Based Access Control = ON
-- 2. Enable Tag Policies: Account Console > Previews > Tag policies = ON
-- 3. Compute: Databricks Runtime 16.4+ or Serverless
-- 4. Groups created in Databricks workspace (see section at bottom)

USE CATALOG enterprise_gov;
USE SCHEMA hr_finance;

-- ================================================================
-- STEP 1: CREATE GOVERNED TAGS AT ACCOUNT LEVEL
-- ================================================================
-- Note: These must be created in the Account Console > Governed tags section

/*
Account-level governed tags to be created via UI:
1. hr_data_classification: public, internal, confidential, restricted
2. pii_level: none, low, medium, high
3. financial_data: true, false
4. department: Human Resource, Finance, Sales, IT, Management
5. region: US-West, US-East, US-Central, APAC, Europe
6. access_level: standard, manager, admin, super_admin
7. role_required: employee, manager, hr_admin, finance_admin, system_admin
8. business_unit: Corporate, Field_Sales, Support, Operations
*/

-- ================================================================
-- STEP 2: APPLY TAGS TO EXISTING TABLES AND COLUMNS
-- ================================================================

-- Tag employees table and columns
ALTER TABLE employees SET TAGS (
  'hr_data_classification' = 'confidential',
  'department' = 'Human Resource',
  'pii_level' = 'high',
  'business_unit' = 'Corporate'
);

-- Tag sensitive employee columns
ALTER TABLE employees ALTER COLUMN ssn SET TAGS (
  'pii_level' = 'high',
  'hr_data_classification' = 'restricted',
  'role_required' = 'hr_admin'
);

ALTER TABLE employees ALTER COLUMN salary SET TAGS (
  'financial_data' = 'true',
  'hr_data_classification' = 'confidential',
  'access_level' = 'manager'
);

ALTER TABLE employees ALTER COLUMN phone_number SET TAGS (
  'pii_level' = 'medium',
  'hr_data_classification' = 'internal'
);

ALTER TABLE employees ALTER COLUMN address SET TAGS (
  'pii_level' = 'high',
  'hr_data_classification' = 'confidential'
);

ALTER TABLE employees ALTER COLUMN emergency_contact SET TAGS (
  'pii_level' = 'high',
  'hr_data_classification' = 'restricted',
  'role_required' = 'hr_admin'
);

-- Tag customers table and columns
ALTER TABLE customers SET TAGS (
  'hr_data_classification' = 'internal',
  'department' = 'Sales',
  'business_unit' = 'Field_Sales'
);

ALTER TABLE customers ALTER COLUMN credit_score SET TAGS (
  'financial_data' = 'true',
  'hr_data_classification' = 'confidential',
  'role_required' = 'finance_admin'
);

ALTER TABLE customers ALTER COLUMN account_value SET TAGS (
  'financial_data' = 'true',
  'hr_data_classification' = 'internal',
  'access_level' = 'manager'
);

-- Tag other demo tables
ALTER TABLE user_access_control SET TAGS (
  'hr_data_classification' = 'internal',
  'department' = 'IT',
  'business_unit' = 'Operations'
);

ALTER TABLE department_privileges SET TAGS (
  'hr_data_classification' = 'internal',
  'department' = 'IT'
);

ALTER TABLE personal_records SET TAGS (
  'hr_data_classification' = 'restricted',
  'pii_level' = 'high'
);

ALTER TABLE department_data SET TAGS (
  'hr_data_classification' = 'confidential',
  'financial_data' = 'true'
);

ALTER TABLE department_data ALTER COLUMN budget SET TAGS (
  'financial_data' = 'true',
  'hr_data_classification' = 'restricted',
  'role_required' = 'finance_admin'
);
