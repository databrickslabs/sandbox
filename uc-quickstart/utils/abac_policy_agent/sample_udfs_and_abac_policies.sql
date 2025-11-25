-- ================================================================
-- COMPLETE UNITY CATALOG ABAC POLICIES IMPLEMENTATION
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
-- STEP 1: CREATE OPTIMIZED UDFS FOR ABAC POLICIES
-- ================================================================
-- Following best practices: simple, deterministic, no external calls

-- UDF for hierarchical employee row filtering
CREATE OR REPLACE FUNCTION abac_employee_row_filter(emp_email STRING, emp_department STRING, emp_region STRING, emp_manager STRING)
RETURNS BOOLEAN
DETERMINISTIC
COMMENT 'ABAC row filter for employee data based on hierarchy and department'
RETURN (
  -- Self access
  emp_email = current_user()
  OR
  -- Manager access (lookup current user's direct reports)
  emp_manager = current_user()
  OR
  -- Department admin access
  EXISTS(
    SELECT 1 FROM user_access_control uac1
    JOIN user_access_control uac2 ON uac1.department = uac2.department
    WHERE uac1.username = current_user() 
    AND uac2.username = emp_email
    AND uac1.access_level = 'admin'
  )
  OR
  -- Regional manager access
  EXISTS(
    SELECT 1 FROM user_access_control uac1
    JOIN user_access_control uac2 ON uac1.region = uac2.region
    WHERE uac1.username = current_user()
    AND uac2.username = emp_email
    AND uac1.access_level IN ('manager', 'super_admin')
  )
  OR
  -- Super admin access
  EXISTS(
    SELECT 1 FROM user_access_control 
    WHERE username = current_user() 
    AND access_level = 'super_admin'
  )
);

-- UDF for sales territory customer filtering
CREATE OR REPLACE FUNCTION abac_customer_row_filter(assigned_rep STRING, cust_region STRING)
RETURNS BOOLEAN
DETERMINISTIC
COMMENT 'ABAC row filter for customer data based on sales territory'
RETURN (
  -- Sales rep sees assigned customers
  assigned_rep = current_user()
  OR
  -- Regional managers see customers in their region
  EXISTS(
    SELECT 1 FROM user_access_control
    WHERE username = current_user()
    AND region = cust_region
    AND access_level IN ('manager', 'super_admin')
  )
  OR
  -- Admins see everything
  EXISTS(
    SELECT 1 FROM user_access_control
    WHERE username = current_user()
    AND access_level IN ('admin', 'super_admin')
  )
);

-- UDF for personal record filtering (user can only see their own)
CREATE OR REPLACE FUNCTION abac_personal_record_filter(record_user_email STRING)
RETURNS BOOLEAN
DETERMINISTIC
COMMENT 'ABAC row filter for personal records - users can only see their own'
RETURN record_user_email = current_user();

-- UDF for department-based filtering
CREATE OR REPLACE FUNCTION abac_department_filter(record_department STRING)
RETURNS BOOLEAN
DETERMINISTIC
COMMENT 'ABAC row filter based on department membership'
RETURN (
  EXISTS(
    SELECT 1 FROM user_access_control uac1
    WHERE uac1.username = current_user()
    AND (
      uac1.department = record_department  -- Same department
      OR uac1.access_level = 'super_admin'  -- Super admin override
    )
  )
);

-- ================================================================
-- STEP 4: CREATE COLUMN MASKING UDFS
-- ================================================================

-- SSN masking function
CREATE OR REPLACE FUNCTION abac_mask_ssn(ssn_value STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'ABAC column mask for SSN - only Human Resource admins see full SSN'
RETURN (
  CASE
    WHEN EXISTS(
      SELECT 1 FROM user_access_control uac
      JOIN department_privileges dp ON uac.department = dp.department
      WHERE uac.username = current_user()
      AND dp.can_view_ssn = true
    ) THEN ssn_value
    ELSE CONCAT('XXX-XX-', RIGHT(ssn_value, 4))
  END
);

-- Salary masking function
CREATE OR REPLACE FUNCTION abac_mask_salary(salary_value DECIMAL(10,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
COMMENT 'ABAC column mask for salary - only authorized roles see full salary'
RETURN (
  CASE
    WHEN EXISTS(
      SELECT 1 FROM user_access_control uac
      JOIN department_privileges dp ON uac.department = dp.department
      WHERE uac.username = current_user()
      AND dp.can_view_salary = true
    ) THEN salary_value
    ELSE 0.00
  END
);

-- Phone number partial masking
CREATE OR REPLACE FUNCTION abac_mask_phone(phone_value STRING, record_owner STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'ABAC column mask for phone numbers with partial masking'
RETURN (
  CASE
    WHEN record_owner = current_user() THEN phone_value  -- Own record
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND access_level IN ('admin', 'super_admin')
    ) THEN phone_value  -- Admins see all
    ELSE CONCAT(LEFT(phone_value, 8), 'XXXX')  -- Partial masking
  END
);

-- Address masking with hierarchical logic
CREATE OR REPLACE FUNCTION abac_mask_address(address_value STRING, record_owner STRING, record_manager STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'ABAC column mask for addresses based on hierarchy'
RETURN (
  CASE
    WHEN record_owner = current_user() THEN address_value  -- Own record
    WHEN record_manager = current_user() THEN address_value  -- Direct reports
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND access_level IN ('admin', 'super_admin')
    ) THEN address_value  -- Admins see all
    ELSE '[CONFIDENTIAL ADDRESS]'
  END
);

-- Emergency contact masking (Human Resource only)
CREATE OR REPLACE FUNCTION abac_mask_emergency_contact(contact_value STRING, record_owner STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'ABAC column mask for emergency contacts - Human Resource and self only'
RETURN (
  CASE
    WHEN record_owner = current_user() THEN contact_value  -- Own record
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND department = 'Human Resource'
      AND access_level IN ('admin', 'super_admin')
    ) THEN contact_value  -- Human Resource admin only
    ELSE '[Human Resource CONFIDENTIAL]'
  END
);

-- Credit score masking for customers
CREATE OR REPLACE FUNCTION abac_mask_credit_score(score_value INT, cust_region STRING)
RETURNS INT
DETERMINISTIC
COMMENT 'ABAC column mask for customer credit scores'
RETURN (
  CASE
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND department IN ('Finance', 'Management')
      AND access_level IN ('admin', 'super_admin')
    ) THEN score_value
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND region = cust_region
      AND access_level = 'manager'
    ) THEN score_value
    ELSE 0
  END
);

-- Generic PII masking function
CREATE OR REPLACE FUNCTION abac_mask_pii(pii_value STRING, sensitivity_level STRING)
RETURNS STRING
DETERMINISTIC
COMMENT 'Generic ABAC PII masking based on sensitivity level'
RETURN (
  CASE
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND access_level = 'super_admin'
    ) THEN pii_value  -- Super admin bypass
    WHEN sensitivity_level = 'low' AND LENGTH(pii_value) > 4
      THEN CONCAT(LEFT(pii_value, LENGTH(pii_value) - 4), REPEAT('*', 4))
    WHEN sensitivity_level = 'medium' AND LENGTH(pii_value) > 6
      THEN CONCAT(LEFT(pii_value, 3), REPEAT('*', LENGTH(pii_value) - 6), RIGHT(pii_value, 3))
    WHEN sensitivity_level = 'high'
      THEN '[REDACTED]'
    ELSE pii_value
  END
);

-- ================================================================
-- STEP 5: CREATE ABAC POLICIES AT CATALOG LEVEL
-- ================================================================
-- Policies are created through the UI but here's the equivalent SQL syntax

-- Row filter policy for employee hierarchical access
CREATE POLICY employee_hierarchical_access ON CATALOG enterprise_governance
COMMENT 'Hierarchical row filtering for employee data based on management structure'
ROW FILTER abac_employee_row_filter
TO `hr_users`, `hr_admins`, `managers`, `system_admins`, `all_employees`
EXCEPT `data_stewards`  -- Data stewards can see all for governance
FOR TABLES
WHEN hasTagValue('department', 'Human Resource') OR hasTagValue('pii_level', 'high')
MATCH COLUMNS hasTag('department') AS dept, hasTag('region') AS reg, hasTag('access_level') AS mgr
USING COLUMNS (email, dept, reg, manager_email);

-- Row filter policy for sales territory access
CREATE POLICY sales_territory_access ON CATALOG enterprise_governance
COMMENT 'Sales territory-based row filtering for customer data'
ROW FILTER abac_customer_row_filter
TO `sales_users`, `sales_managers`, `regional_managers`
EXCEPT `finance_admins`  -- Finance can see all for reporting
FOR TABLES
WHEN hasTagValue('department', 'Sales') OR hasTagValue('business_unit', 'Field_Sales')
MATCH COLUMNS hasTag('region') AS region
USING COLUMNS (assigned_sales_rep, region);

-- Row filter policy for personal records
CREATE POLICY personal_record_access ON CATALOG enterprise_governance
COMMENT 'Users can only access their own personal records'
ROW FILTER abac_personal_record_filter
TO `all_employees`
EXCEPT `hr_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('hr_data_classification', 'restricted') AND hasTagValue('pii_level', 'high')
MATCH COLUMNS hasTag('pii_level') AS pii
USING COLUMNS (user_email);

-- Row filter policy for department-based access
CREATE POLICY department_based_access ON CATALOG enterprise_governance
COMMENT 'Department-based row filtering for organizational data'
ROW FILTER abac_department_filter
TO `all_employees`
EXCEPT `system_admins`
FOR TABLES
WHEN hasTagValue('hr_data_classification', 'internal') OR hasTagValue('hr_data_classification', 'confidential')
MATCH COLUMNS hasTag('department') AS dept
USING COLUMNS (dept);

-- ================================================================
-- STEP 6: CREATE COLUMN MASK POLICIES
-- ================================================================

-- SSN masking policy
CREATE POLICY mask_ssn_policy ON CATALOG enterprise_governance
COMMENT 'Mask SSN except for Human Resource admins and system admins'
COLUMN MASK abac_mask_ssn
TO `all_employees`
EXCEPT `hr_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('pii_level', 'high')
MATCH COLUMNS hasTagValue('role_required', 'hr_admin') AS ssn_col
USING COLUMNS (ssn_col);

-- Salary masking policy
CREATE POLICY mask_salary_policy ON CATALOG enterprise_governance
COMMENT 'Mask salary except for authorized roles'
COLUMN MASK abac_mask_salary
TO `all_employees`
EXCEPT `finance_admins`, `hr_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('financial_data', 'true')
MATCH COLUMNS hasTagValue('access_level', 'manager') AS sal_col
USING COLUMNS (sal_col);

-- Phone number masking policy
CREATE POLICY mask_phone_policy ON CATALOG enterprise_governance
COMMENT 'Partially mask phone numbers with hierarchical access'
COLUMN MASK abac_mask_phone
TO `all_employees`
EXCEPT `system_admins`
FOR TABLES
WHEN hasTagValue('pii_level', 'medium')
MATCH COLUMNS hasTag('pii_level') AS phone_col
USING COLUMNS (phone_col, email);

-- Address masking policy
CREATE POLICY mask_address_policy ON CATALOG enterprise_governance
COMMENT 'Mask addresses based on hierarchical relationships'
COLUMN MASK abac_mask_address
TO `all_employees`
EXCEPT `hr_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('pii_level', 'high') AND hasTagValue('hr_data_classification', 'confidential')
MATCH COLUMNS hasTag('pii_level') AS addr_col
USING COLUMNS (addr_col, email, manager_email);

-- Emergency contact masking policy
CREATE POLICY mask_emergency_contact_policy ON CATALOG enterprise_governance
COMMENT 'Mask emergency contacts - Human Resource admins and self only'
COLUMN MASK abac_mask_emergency_contact
TO `all_employees`
EXCEPT `hr_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('role_required', 'hr_admin')
MATCH COLUMNS hasTagValue('role_required', 'hr_admin') AS emerg_col
USING COLUMNS (emerg_col, email);

-- Credit score masking policy
CREATE POLICY mask_credit_score_policy ON CATALOG enterprise_governance
COMMENT 'Mask customer credit scores except for finance and regional managers'
COLUMN MASK abac_mask_credit_score
TO `sales_users`, `all_employees`
EXCEPT `finance_admins`, `regional_managers`, `system_admins`
FOR TABLES
WHEN hasTagValue('financial_data', 'true') AND hasTagValue('role_required', 'finance_admin')
MATCH COLUMNS hasTagValue('role_required', 'finance_admin') AS credit_col, hasTag('region') AS reg_col
USING COLUMNS (credit_col, reg_col);

-- ================================================================
-- STEP 7: SPECIALIZED POLICIES FOR DIFFERENT SCENARIOS
-- ================================================================

-- Policy for financial data access (multi-table)
CREATE POLICY financial_data_access ON CATALOG enterprise_governance
COMMENT 'Comprehensive financial data access control across all tables'
ROW FILTER (
  CASE
    WHEN EXISTS(
      SELECT 1 FROM user_access_control
      WHERE username = current_user()
      AND department IN ('Finance', 'Management')
      AND access_level IN ('admin', 'super_admin')
    ) THEN TRUE
    ELSE FALSE
  END
)
TO `all_employees`
EXCEPT `finance_admins`, `system_admins`
FOR TABLES
WHEN hasTagValue('financial_data', 'true');

-- Policy for regional data compliance (GDPR-like)
CREATE POLICY regional_compliance_policy ON CATALOG enterprise_governance
COMMENT 'Regional data access control for compliance requirements'
ROW FILTER (
  EXISTS(
    SELECT 1 FROM user_access_control uac1
    WHERE uac1.username = current_user()
    AND (
      uac1.access_level = 'super_admin'
      OR EXISTS(
        SELECT 1 FROM user_access_control uac2
        WHERE uac2.region = uac1.region
        AND uac2.username = current_user()
      )
    )
  )
)
TO `all_employees`
EXCEPT `system_admins`, `data_stewards`
FOR TABLES
WHEN hasTag('region')
MATCH COLUMNS hasTag('region') AS reg_col
USING COLUMNS (reg_col);

-- ================================================================
-- STEP 8: MONITORING AND AUDIT POLICIES
-- ================================================================

-- Create audit view for policy effectiveness
CREATE OR REPLACE VIEW abac_policy_audit AS
SELECT 
  current_user() as accessing_user,
  current_timestamp() as access_time,
  'employees' as table_name,
  COUNT(*) as visible_records,
  AVG(
    CASE 
      WHEN salary > 0 THEN 1 
      ELSE 0 
    END
  ) as salary_visibility_rate
FROM employees
UNION ALL
SELECT 
  current_user(),
  current_timestamp(),
  'customers',
  COUNT(*),
  AVG(
    CASE 
      WHEN credit_score > 0 THEN 1 
      ELSE 0 
    END
  )
FROM customers;

-- Create user access summary view
CREATE OR REPLACE VIEW user_access_summary AS
SELECT 
  current_user() as user,
  uac.department,
  uac.region,
  uac.access_level,
  dp.can_view_salary,
  dp.can_view_ssn,
  dp.can_view_all_regions
FROM user_access_control uac
LEFT JOIN department_privileges dp ON uac.department = dp.department
WHERE uac.username = current_user();

-- ================================================================
-- STEP 9: TEST QUERIES FOR DIFFERENT USER SCENARIOS
-- ================================================================

-- Test query 1: Employee data visibility
-- SELECT employee_id, first_name, last_name, department, salary, ssn, phone_number, address
-- FROM employees 
-- ORDER BY employee_id;

-- Test query 2: Customer data visibility  
-- SELECT customer_id, company_name, region, account_value, credit_score
-- FROM customers
-- ORDER BY customer_id;

-- Test query 3: Personal records access
-- SELECT * FROM personal_records;

-- Test query 4: Department data access
-- SELECT * FROM department_data;

-- Test query 5: Cross-table join with masking
-- SELECT 
--   e.first_name,
--   e.last_name, 
--   e.department,
--   e.salary,
--   e.ssn,
--   c.company_name,
--   c.credit_score
-- FROM employees e
-- LEFT JOIN customers c ON e.email = c.assigned_sales_rep;

-- Test query 6: Audit current user access
-- SELECT * FROM user_access_summary;

-- Test query 7: Policy effectiveness audit
-- SELECT * FROM abac_policy_audit;

-- ================================================================
-- STEP 10: REQUIRED DATABRICKS GROUPS
-- ================================================================
/*
Create these groups in Databricks Admin Console > Groups:

Core Groups:
1. all_employees - All company employees
2. system_admins - IT administrators with full access
3. data_stewards - Data governance team with audit access

Department Groups:
4. hr_users - Human Resource department standard users
5. hr_admins - Human Resource department administrators
6. finance_users - Finance department standard users  
7. finance_admins - Finance department administrators
8. sales_users - Sales department standard users
9. sales_managers - Sales department managers
10. it_users - IT department users

Regional Groups:
11. us_west_users - US West region users
12. us_east_users - US East region users
13. us_central_users - US Central region users
14. apac_users - APAC region users
15. europe_users - Europe region users

Role-based Groups:
16. managers - All management levels
17. regional_managers - Regional management
18. senior_managers - Senior management

Business Unit Groups:
19. corporate_users - Corporate functions
20. field_sales_users - Field sales teams
21. support_users - Support functions
22. operations_users - Operations teams

Group Assignments should be based on:
- user_access_control table data
- Employee department and access_level
- Regional assignments
- Management hierarchy

Example assignments:
- john.smith@databricks.com -> sales_users, us_west_users, all_employees
- jane.doe@databricks.com -> hr_users, hr_admins, us_east_users, all_employees  
- sarah.johnson@databricks.com -> system_admins, managers, senior_managers, all_employees
*/

-- ================================================================
-- STEP 11: POLICY MANAGEMENT AND MAINTENANCE
-- ================================================================

-- View all active policies
-- SELECT policy_name, policy_type, scope, principals 
-- FROM system.information_schema.policies
-- WHERE catalog_name = 'enterprise_gov';

-- Monitor policy performance
-- SELECT * FROM system.access_control.audit()
-- WHERE source_type = 'ABAC_POLICY'
-- AND event_time > current_timestamp() - INTERVAL 1 DAY;

-- ================================================================
-- CLEANUP COMMANDS (FOR TESTING ONLY)
-- ================================================================
-- Uncomment to remove policies during testing

-- DROP POLICY IF EXISTS employee_hierarchical_access ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS sales_territory_access ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS personal_record_access ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS department_based_access ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_ssn_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_salary_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_phone_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_address_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_emergency_contact_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS mask_credit_score_policy ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS financial_data_access ON CATALOG enterprise_gov;
-- DROP POLICY IF EXISTS regional_compliance_policy ON CATALOG enterprise_gov;

-- ================================================================
-- END OF COMPLETE ABAC POLICIES IMPLEMENTATION
-- ================================================================
