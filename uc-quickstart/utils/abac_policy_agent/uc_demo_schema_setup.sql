-- ================================================================
-- Unity Catalog Row Filter & Column Mask Demo
-- Comprehensive examples showcasing enterprise data governance
-- ================================================================

-- Create Demo Catalog and Schema
CREATE CATALOG IF NOT EXISTS enterprise_gov;
USE CATALOG enterprise_gov;

CREATE SCHEMA IF NOT EXISTS hr_finance;
USE SCHEMA hr_finance;

-- ================================================================
-- STEP 1: Create User Groups and Mapping Tables
-- ================================================================

-- User access mapping table
CREATE OR REPLACE TABLE user_access_control (
    username STRING,
    department STRING,
    region STRING,
    access_level STRING,
    manager_email STRING
);

INSERT INTO user_access_control VALUES
('john.smith@databricks.com', 'Sales', 'US-West', 'standard', 'sarah.johnson@databricks.com'),
('jane.doe@databricks.com', 'Human Resource', 'US-East', 'admin', 'sarah.johnson@databricks.com'),
('mike.wilson@databricks.com', 'Finance', 'US-Central', 'standard', 'sarah.johnson@databricks.com'),
('sarah.johnson@databricks.com', 'Management', 'US-West', 'super_admin', null),
('raj.patel@databricks.com', 'Sales', 'APAC', 'standard', 'lisa.chen@databricks.com'),
('lisa.chen@databricks.com', 'Sales', 'APAC', 'manager', 'sarah.johnson@databricks.com'),
('emma.brown@databricks.com', 'Human Resource', 'Europe', 'admin', 'david.garcia@databricks.com'),
('david.garcia@databricks.com', 'Management', 'Europe', 'manager', 'sarah.johnson@databricks.com'),
('alex.kim@databricks.com', 'Finance', 'APAC', 'standard', 'mike.wilson@databricks.com'),
('maria.rodriguez@databricks.com', 'IT', 'US-Central', 'admin', 'sarah.johnson@databricks.com');

-- Department access levels
CREATE OR REPLACE TABLE department_privileges (
    department STRING,
    can_view_salary BOOLEAN,
    can_view_ssn BOOLEAN,
    can_view_all_regions BOOLEAN
);

INSERT INTO department_privileges VALUES
('Human Resource', true, true, true),
('Management', true, true, true),
('Finance', true, false, false),
('Sales', false, false, false),
('IT', false, false, true);

-- ================================================================
-- STEP 2: Create Main Employee Data Table
-- ================================================================

CREATE OR REPLACE TABLE employees (
    employee_id INT,
    first_name STRING,
    last_name STRING,
    email STRING,
    department STRING,
    region STRING,
    salary DECIMAL(10,2),
    ssn STRING,
    hire_date DATE,
    performance_rating STRING,
    manager_email STRING,
    phone_number STRING,
    address STRING,
    emergency_contact STRING
);

INSERT INTO employees VALUES
(1001, 'John', 'Smith', 'john.smith@databricks.com', 'Sales', 'US-West', 95000.00, '123-45-6789', '2022-03-15', 'Exceeds', 'sarah.johnson@databricks.com', '555-0101', '123 Main St, San Francisco, CA', 'spouse: 555-0102'),
(1002, 'Jane', 'Doe', 'jane.doe@databricks.com', 'Human Resource', 'US-East', 87000.00, '234-56-7890', '2021-08-20', 'Meets', 'sarah.johnson@databricks.com', '555-0103', '456 Oak Ave, New York, NY', 'parent: 555-0104'),
(1003, 'Mike', 'Wilson', 'mike.wilson@databricks.com', 'Finance', 'US-Central', 105000.00, '345-67-8901', '2020-11-10', 'Exceeds', 'sarah.johnson@databricks.com', '555-0105', '789 Pine Rd, Chicago, IL', 'sibling: 555-0106'),
(1004, 'Sarah', 'Johnson', 'sarah.johnson@databricks.com', 'Management', 'US-West', 150000.00, '456-78-9012', '2019-01-05', 'Outstanding', null, '555-0107', '321 Elm Dr, Los Angeles, CA', 'spouse: 555-0108'),
(1005, 'Raj', 'Patel', 'raj.patel@databricks.com', 'Sales', 'APAC', 78000.00, '567-89-0123', '2022-07-12', 'Meets', 'lisa.chen@databricks.com', '555-0109', '654 Maple Ln, Singapore', 'parent: 555-0110'),
(1006, 'Lisa', 'Chen', 'lisa.chen@databricks.com', 'Sales', 'APAC', 120000.00, '678-90-1234', '2021-02-28', 'Exceeds', 'sarah.johnson@databricks.com', '555-0111', '987 Cedar St, Tokyo, Japan', 'spouse: 555-0112'),
(1007, 'Emma', 'Brown', 'emma.brown@databricks.com', 'Human Resource', 'Europe', 82000.00, '789-01-2345', '2021-09-15', 'Meets', 'david.garcia@databricks.com', '555-0113', '147 Birch Ave, London, UK', 'friend: 555-0114'),
(1008, 'David', 'Garcia', 'david.garcia@databricks.com', 'Management', 'Europe', 135000.00, '890-12-3456', '2020-04-22', 'Exceeds', 'sarah.johnson@databricks.com', '555-0115', '258 Willow Rd, Madrid, Spain', 'parent: 555-0116'),
(1009, 'Alex', 'Kim', 'alex.kim@databricks.com', 'Finance', 'APAC', 92000.00, '901-23-4567', '2022-12-01', 'Meets', 'mike.wilson@databricks.com', '555-0117', '369 Spruce Dr, Seoul, Korea', 'sibling: 555-0118'),
(1010, 'Maria', 'Rodriguez', 'maria.rodriguez@databricks.com', 'IT', 'US-Central', 98000.00, '012-34-5678', '2021-06-30', 'Exceeds', 'sarah.johnson@databricks.com', '555-0119', '741 Ash Ln, Austin, TX', 'spouse: 555-0120');

-- ================================================================
-- STEP 3: Create Customer Data Table for Sales Filtering
-- ================================================================

CREATE OR REPLACE TABLE customers (
    customer_id INT,
    company_name STRING,
    contact_email STRING,
    region STRING,
    account_value DECIMAL(12,2),
    assigned_sales_rep STRING,
    credit_score INT,
    payment_terms STRING,
    created_date DATE
);

INSERT INTO customers VALUES
(2001, 'TechCorp Inc', 'admin@techcorp.com', 'US-West', 250000.00, 'john.smith@databricks.com', 780, 'NET30', '2022-01-15'),
(2002, 'DataSystems LLC', 'contact@datasystems.com', 'US-East', 180000.00, 'john.smith@databricks.com', 720, 'NET45', '2022-03-20'),
(2003, 'Global Analytics', 'info@globalanalytics.com', 'APAC', 320000.00, 'raj.patel@databricks.com', 820, 'NET30', '2022-02-10'),
(2004, 'InnovateTech', 'hello@innovatetech.com', 'Europe', 195000.00, 'lisa.chen@databricks.com', 750, 'NET30', '2022-04-05'),
(2005, 'SmartSolutions', 'team@smartsolutions.com', 'APAC', 280000.00, 'raj.patel@databricks.com', 790, 'NET15', '2022-05-12'),
(2006, 'CloudFirst Systems', 'support@cloudfirst.com', 'US-Central', 150000.00, 'john.smith@databricks.com', 680, 'NET60', '2022-06-18'),
(2007, 'SecureData Corp', 'admin@securedata.com', 'Europe', 420000.00, 'lisa.chen@databricks.com', 850, 'NET30', '2022-07-25'),
(2008, 'AI Innovations', 'contact@aiinnovations.com', 'US-West', 380000.00, 'john.smith@databricks.com', 800, 'NET30', '2022-08-14'),
(2009, 'NextGen Analytics', 'info@nextgenanalytics.com', 'APAC', 220000.00, 'raj.patel@databricks.com', 740, 'NET45', '2022-09-30'),
(2010, 'Future Systems', 'hello@futuresystems.com', 'Europe', 160000.00, 'lisa.chen@databricks.com', 710, 'NET30', '2022-10-22');

-- ================================================================
-- STEP 4: ROW FILTER FUNCTIONS
-- ================================================================

-- 1. User-based row filter - Users can only see their own employee record
CREATE OR REPLACE FUNCTION user_own_record_filter(email STRING)
RETURN email = current_user();

-- 2. Department-based row filter - Users can see records in their department
CREATE OR REPLACE FUNCTION department_filter(emp_email STRING)
RETURN EXISTS(
    SELECT 1 FROM user_access_control u1
    JOIN user_access_control u2 ON u1.department = u2.department
    WHERE u1.username = current_user() 
    AND u2.username = emp_email
);

-- 3. Regional access filter with admin override
CREATE OR REPLACE FUNCTION regional_access_filter(emp_region STRING, emp_email STRING)
RETURN 
    -- Super admins see everything
    EXISTS(SELECT 1 FROM user_access_control WHERE username = current_user() AND access_level = 'super_admin')
    OR
    -- Regional managers see their region
    EXISTS(SELECT 1 FROM user_access_control u1
           JOIN user_access_control u2 ON u1.region = u2.region
           WHERE u1.username = current_user() 
           AND u2.username = emp_email
           AND u1.access_level IN ('manager', 'admin'))
    OR
    -- Users see their own record
    emp_email = current_user();

-- 4. Hierarchical access filter - Managers can see their subordinates
CREATE OR REPLACE FUNCTION hierarchical_filter(emp_email STRING, emp_manager STRING)
RETURN 
    -- Super admins see everything
    EXISTS(SELECT 1 FROM user_access_control WHERE username = current_user() AND access_level = 'super_admin')
    OR
    -- Managers see their direct reports
    emp_manager = current_user()
    OR
    -- Users see their own record
    emp_email = current_user()
    OR
    -- Department admins see department records
    EXISTS(SELECT 1 FROM user_access_control u1
           JOIN user_access_control u2 ON u1.department = u2.department
           WHERE u1.username = current_user() 
           AND u2.username = emp_email
           AND u1.access_level = 'admin');

-- 5. Sales territory filter for customers
CREATE OR REPLACE FUNCTION sales_territory_filter(assigned_rep STRING, cust_region STRING)
RETURN 
    -- Sales reps see their assigned customers
    assigned_rep = current_user()
    OR
    -- Managers see customers in their region
    EXISTS(SELECT 1 FROM user_access_control 
           WHERE username = current_user() 
           AND region = cust_region 
           AND access_level IN ('manager', 'super_admin'))
    OR
    -- Admins see everything
    EXISTS(SELECT 1 FROM user_access_control 
           WHERE username = current_user() 
           AND access_level IN ('admin', 'super_admin'));

-- ================================================================
-- STEP 5: COLUMN MASK FUNCTIONS
-- ================================================================

-- 1. SSN masking - Only Human Resource and Management can see full SSN
CREATE OR REPLACE FUNCTION ssn_mask(ssn STRING)
RETURN 
    CASE 
        WHEN EXISTS(SELECT 1 FROM user_access_control u
                   JOIN department_privileges d ON u.department = d.department
                   WHERE u.username = current_user() AND d.can_view_ssn = true)
        THEN ssn
        ELSE 'XXX-XX-' || RIGHT(ssn, 4)
    END;

-- 2. Salary masking - Human Resource, Management, and Finance can see salaries
CREATE OR REPLACE FUNCTION salary_mask(salary DECIMAL(10,2))
RETURN 
    CASE 
        WHEN EXISTS(SELECT 1 FROM user_access_control u
                   JOIN department_privileges d ON u.department = d.department
                   WHERE u.username = current_user() AND d.can_view_salary = true)
        THEN salary
        ELSE 0.00
    END;

-- 3. Phone number partial masking
CREATE OR REPLACE FUNCTION phone_mask(phone STRING, emp_email STRING)
RETURN 
    CASE 
        WHEN emp_email = current_user() THEN phone  -- Own record
        WHEN EXISTS(SELECT 1 FROM user_access_control WHERE username = current_user() AND access_level IN ('admin', 'super_admin'))
        THEN phone  -- Admins see all
        ELSE LEFT(phone, 8) || 'XXXX'  -- Others see partial
    END;

-- 4. Address masking based on hierarchy
CREATE OR REPLACE FUNCTION address_mask(address STRING, emp_email STRING, emp_manager STRING)
RETURN 
    CASE 
        WHEN emp_email = current_user() THEN address  -- Own record
        WHEN emp_manager = current_user() THEN address  -- Direct reports
        WHEN EXISTS(SELECT 1 FROM user_access_control WHERE username = current_user() AND access_level IN ('admin', 'super_admin'))
        THEN address  -- Admins see all
        ELSE '[CONFIDENTIAL]'
    END;

-- 5. Emergency contact masking
CREATE OR REPLACE FUNCTION emergency_contact_mask(contact STRING, emp_email STRING)
RETURN 
    CASE 
        WHEN emp_email = current_user() THEN contact  -- Own record
        WHEN EXISTS(SELECT 1 FROM user_access_control u
                   WHERE u.username = current_user() 
                   AND u.department IN ('Human Resource', 'Management'))
        THEN contact  -- Human Resource and Management only
        ELSE '[REDACTED]'
    END;

-- 6. Credit score masking for customers
CREATE OR REPLACE FUNCTION credit_score_mask(score INT, cust_region STRING)
RETURN 
    CASE 
        WHEN EXISTS(SELECT 1 FROM user_access_control 
                   WHERE username = current_user() 
                   AND department IN ('Finance', 'Management'))
        THEN score
        WHEN EXISTS(SELECT 1 FROM user_access_control 
                   WHERE username = current_user() 
                   AND region = cust_region 
                   AND access_level = 'manager')
        THEN score
        ELSE 0
    END;

-- ================================================================
-- STEP 6: APPLY FILTERS AND MASKS TO TABLES
-- ================================================================

-- Apply comprehensive governance to employees table
ALTER TABLE employees SET ROW FILTER hierarchical_filter ON (email, manager_email);

-- Apply column masks
ALTER TABLE employees ALTER COLUMN ssn SET MASK ssn_mask;
ALTER TABLE employees ALTER COLUMN salary SET MASK salary_mask;
ALTER TABLE employees ALTER COLUMN phone_number SET MASK phone_mask USING COLUMNS (email);
ALTER TABLE employees ALTER COLUMN address SET MASK address_mask USING COLUMNS (email, manager_email);
ALTER TABLE employees ALTER COLUMN emergency_contact SET MASK emergency_contact_mask USING COLUMNS (email);

-- Apply sales territory filter to customers
ALTER TABLE customers SET ROW FILTER sales_territory_filter ON (assigned_sales_rep, region);

-- Apply credit score masking
ALTER TABLE customers ALTER COLUMN credit_score SET MASK credit_score_mask USING COLUMNS (region);

-- ================================================================
-- STEP 7: CREATE ADDITIONAL DEMO TABLES FOR SPECIFIC USE CASES
-- ================================================================

-- Table with user-level filtering only
CREATE OR REPLACE TABLE personal_records (
    record_id INT,
    user_email STRING,
    personal_notes STRING,
    confidential_data STRING
) WITH ROW FILTER user_own_record_filter ON (user_email);

INSERT INTO personal_records VALUES
(1, 'john.smith@databricks.com', 'Performance goals for Q4', 'Salary negotiation notes'),
(2, 'jane.doe@databricks.com', 'Training completion status', 'Human Resource disciplinary records'),
(3, 'mike.wilson@databricks.com', 'Budget planning notes', 'Financial projections');

-- Table with department-only access
CREATE OR REPLACE TABLE department_data (
    dept_id INT,
    department STRING,
    budget DECIMAL(12,2),
    headcount INT,
    sensitive_info STRING
) WITH ROW FILTER department_filter ON (department);

-- Create department-specific masking for budget
CREATE OR REPLACE FUNCTION budget_mask(budget DECIMAL(12,2))
RETURN 
    CASE 
        WHEN EXISTS(SELECT 1 FROM user_access_control 
                   WHERE username = current_user() 
                   AND access_level IN ('super_admin', 'admin')
                   AND department IN ('Management', 'Finance'))
        THEN budget
        ELSE 0.00
    END;

ALTER TABLE department_data ALTER COLUMN budget SET MASK budget_mask;
ALTER TABLE department_data ALTER COLUMN sensitive_info SET MASK 
    (CASE 
        WHEN EXISTS(SELECT 1 FROM user_access_control 
                   WHERE username = current_user() 
                   AND access_level = 'super_admin')
        THEN sensitive_info
        ELSE '[DEPARTMENT CONFIDENTIAL]'
    END);

INSERT INTO department_data VALUES
(1, 'Sales', 2500000.00, 25, 'Commission structure details'),
(2, 'Human Resource', 1800000.00, 15, 'Employee relations issues'),
(3, 'Finance', 1200000.00, 12, 'Audit findings'),
(4, 'Management', 3000000.00, 8, 'Strategic planning documents'),
(5, 'IT', 2200000.00, 20, 'Security incident reports');

-- ================================================================
-- STEP 8: TEST QUERIES AND EXAMPLES
-- ================================================================

-- Example queries to test different access patterns:

-- 1. View all employees (filtered by hierarchy)
-- SELECT * FROM employees;

-- 2. View customers (filtered by territory)
-- SELECT * FROM customers;

-- 3. View personal records (user can only see their own)
-- SELECT * FROM personal_records;

-- 4. View department data (filtered by department membership)
-- SELECT * FROM department_data;

-- 5. Complex join with multiple filters and masks
-- SELECT 
--     e.first_name,
--     e.last_name,
--     e.department,
--     e.salary,
--     e.ssn,
--     c.company_name,
--     c.account_value,
--     c.credit_score
-- FROM employees e
-- LEFT JOIN customers c ON e.email = c.assigned_sales_rep;

-- ================================================================
-- STEP 9: ADMINISTRATIVE QUERIES FOR TESTING
-- ================================================================

-- View current user context
-- SELECT current_user() as current_user;

-- Check user access levels
-- SELECT * FROM user_access_control WHERE username = current_user();

-- View department privileges
-- SELECT * FROM department_privileges;

-- ================================================================
-- STEP 10: CLEANUP COMMANDS (OPTIONAL)
-- ================================================================

-- To remove filters and masks for testing:
-- ALTER TABLE employees DROP ROW FILTER;
-- ALTER TABLE employees ALTER COLUMN ssn DROP MASK;
-- ALTER TABLE employees ALTER COLUMN salary DROP MASK;
-- ALTER TABLE employees ALTER COLUMN phone_number DROP MASK;
-- ALTER TABLE employees ALTER COLUMN address DROP MASK;
-- ALTER TABLE employees ALTER COLUMN emergency_contact DROP MASK;

-- ALTER TABLE customers DROP ROW FILTER;
-- ALTER TABLE customers ALTER COLUMN credit_score DROP MASK;

-- DROP FUNCTION IF EXISTS user_own_record_filter;
-- DROP FUNCTION IF EXISTS department_filter;
-- DROP FUNCTION IF EXISTS regional_access_filter;
-- DROP FUNCTION IF EXISTS hierarchical_filter;
-- DROP FUNCTION IF EXISTS sales_territory_filter;
-- DROP FUNCTION IF EXISTS ssn_mask;
-- DROP FUNCTION IF EXISTS salary_mask;
-- DROP FUNCTION IF EXISTS phone_mask;
-- DROP FUNCTION IF EXISTS address_mask;
-- DROP FUNCTION IF EXISTS emergency_contact_mask;
-- DROP FUNCTION IF EXISTS credit_score_mask;
-- DROP FUNCTION IF EXISTS budget_mask;

-- ================================================================
-- END OF DEMO SCRIPT
-- ================================================================
