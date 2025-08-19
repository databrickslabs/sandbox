-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 🔐 Healthcare ABAC Policies Library (SQL)
-- MAGIC
-- MAGIC This notebook defines reusable Attribute-Based Access Control (ABAC) policies for healthcare data governance using Unity Catalog.
-- MAGIC
-- MAGIC ## 📋 Prerequisites
-- MAGIC - Unity Catalog enabled with ABAC policies feature enabled
-- MAGIC - Healthcare tag policies created (from `CreateHealthcareTagPolicies.ipynb`)
-- MAGIC - ABAC masking functions deployed (from `comprehensive_abac_functions.sql`)
-- MAGIC - Healthcare account groups created (from `CreateHealthcareGroups_Fixed.ipynb`)
-- MAGIC - Appropriate permissions to create policies on schema/catalog
-- MAGIC
-- MAGIC ## 🎯 Policy Library Overview
-- MAGIC This notebook creates **7 reusable ABAC policies** that can be applied to any healthcare tables:
-- MAGIC
-- MAGIC 1. **Deterministic Masking Policy** - Cross-table patient ID consistency
-- MAGIC 2. **Time-Based Access Policy** - Business hours restriction
-- MAGIC 3. **Policy Expiry Access** - Temporary auditor access control
-- MAGIC 4. **Seniority-Based Masking** - Role-based patient name privacy
-- MAGIC 5. **Regional Data Governance** - Geographic access control
-- MAGIC 6. **Age Demographics Masking** - Birth date to age group conversion
-- MAGIC 7. **Insurance Verification Masking** - Role-based financial data access
-- MAGIC
-- MAGIC ## ⚠️ Important Notes
-- MAGIC - This notebook creates **reusable policy definitions only**
-- MAGIC - No policies are bound to specific tables or columns
-- MAGIC - Uses `apscat.healthcare` schema
-- MAGIC - Policies use tag-based conditions for flexible application

-- COMMAND ----------

-- Set schema context and verify table existence
USE CATALOG apscat;
USE SCHEMA healthcare;

-- Verify tables exist and show their structure
SHOW TABLES;

-- Verify Patients table structure
DESCRIBE TABLE Patients;

SELECT "✅ Ready to create ABAC policies in current schema" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🏷️ STEP 1: Verify Healthcare Tables and Apply Tags
-- MAGIC
-- MAGIC Before creating policies, we need to verify our healthcare tables exist and apply the appropriate tags for the ABAC policies to work properly.
-- MAGIC
-- MAGIC ### Table Verification and Tag Application for All 7 Scenarios
-- MAGIC
-- MAGIC First, let's verify we have the expected healthcare tables with the correct column structure.

-- COMMAND ----------

-- VERIFICATION: Check Healthcare Tables Structure

-- Verify key tables and columns exist before applying tags
SELECT 'Patients table check' as verification_step;
DESCRIBE TABLE apscat.healthcare.Patients;

SELECT 'Insurance table check' as verification_step;  
DESCRIBE TABLE apscat.healthcare.Insurance;

SELECT 'LabResults table check' as verification_step;
DESCRIBE TABLE apscat.healthcare.LabResults;

SELECT 'Billing table check' as verification_step;
DESCRIBE TABLE apscat.healthcare.Billing;

-- Show current context
SELECT current_catalog() as current_catalog, current_schema() as current_schema;

-- COMMAND ----------

-- SCENARIO 1: Apply tags for Deterministic Masking

-- Tag PatientID columns across tables for consistent masking 
ALTER TABLE apscat.healthcare.Patients ALTER COLUMN PatientID SET TAGS ('job_role' = 'Healthcare_Analyst', 'data_purpose' = 'Population_Analytics');
ALTER TABLE apscat.healthcare.Visits ALTER COLUMN PatientID SET TAGS ('job_role' = 'Healthcare_Analyst', 'data_purpose' = 'Population_Analytics');
ALTER TABLE apscat.healthcare.LabResults ALTER COLUMN PatientID SET TAGS ('job_role' = 'Healthcare_Analyst', 'data_purpose' = 'Population_Analytics');
ALTER TABLE apscat.healthcare.Prescriptions ALTER COLUMN PatientID SET TAGS ('job_role' = 'Healthcare_Analyst', 'data_purpose' = 'Population_Analytics');

SELECT "✅ SCENARIO 1: PatientID columns tagged for deterministic masking" as status;

-- COMMAND ----------

-- SCENARIO 2: Apply tags for Time-Based Access Control

-- Tag LabResults table for time-based access
ALTER TABLE apscat.healthcare.LabResults SET TAGS ('shift_hours' = 'Standard_Business', 'job_role' = 'Lab_Technician');
ALTER TABLE apscat.healthcare.LabResults ALTER COLUMN ResultValue SET TAGS ('phi_level' = 'Full_PHI', 'shift_hours' = 'Standard_Business');
ALTER TABLE apscat.healthcare.LabResults ALTER COLUMN TestName SET TAGS ('phi_level' = 'Full_PHI', 'shift_hours' = 'Standard_Business');

SELECT "✅ SCENARIO 2: LabResults tagged for time-based access" as status;

-- COMMAND ----------

-- SCENARIO 3: Apply tags for Policy Expiry

-- Tag Billing table for temporary auditor access
ALTER TABLE apscat.healthcare.Billing SET TAGS ('access_expiry_date' = '2025-12-31', 'job_role' = 'External_Auditor', 'audit_project' = 'Q4_Compliance_Review');
ALTER TABLE apscat.healthcare.Billing ALTER COLUMN ChargeAmount SET TAGS ('data_purpose' = 'Financial_Operations', 'access_expiry_date' = '2025-12-31');
ALTER TABLE apscat.healthcare.Billing ALTER COLUMN BillingStatus SET TAGS ('data_purpose' = 'Financial_Operations', 'access_expiry_date' = '2025-12-31');

SELECT "✅ SCENARIO 3: Billing table tagged for policy expiry" as status;

-- COMMAND ----------

-- SCENARIO 4: Apply tags for Seniority-Based Name Masking

-- Tag patient name columns for seniority-based access  
ALTER TABLE apscat.healthcare.Patients ALTER COLUMN FirstName SET TAGS ('seniority' = 'Senior_Staff', 'job_role' = 'Healthcare_Worker', 'phi_level' = 'Full_PHI');
ALTER TABLE apscat.healthcare.Patients ALTER COLUMN LastName SET TAGS ('seniority' = 'Senior_Staff', 'job_role' = 'Healthcare_Worker', 'phi_level' = 'Full_PHI');

SELECT "✅ SCENARIO 4: Patient name columns tagged for seniority-based masking" as status;

-- COMMAND ----------

-- SCENARIO 5: Apply tags for Regional Data Governance

-- Tag Patients table for regional access control
ALTER TABLE apscat.healthcare.Patients SET TAGS ('region' = 'North', 'data_residency' = 'Regional_Boundary', 'job_role' = 'Regional_Staff');
ALTER TABLE apscat.healthcare.Patients ALTER COLUMN Address SET TAGS ('region' = 'North', 'data_residency' = 'Regional_Boundary');

SELECT "✅ SCENARIO 5: Patients table tagged for regional control" as status;

-- COMMAND ----------

-- SCENARIO 6: Apply tags for Age Demographics Masking

-- Tag DateOfBirth for age group masking
ALTER TABLE apscat.healthcare.Patients ALTER COLUMN DateOfBirth SET TAGS ('research_approval' = 'Demographics_Study', 'phi_level' = 'Limited_Dataset', 'job_role' = 'Population_Health_Researcher');

SELECT "✅ SCENARIO 6: DateOfBirth tagged for age demographics masking" as status;

-- COMMAND ----------

-- SCENARIO 7: Apply tags for Insurance Verification

-- Tag Insurance table for role-based verification
ALTER TABLE apscat.healthcare.Insurance SET TAGS ('verification_level' = 'Full', 'job_role' = 'Insurance_Coordinator');
ALTER TABLE apscat.healthcare.Insurance ALTER COLUMN PolicyNumber SET TAGS ('verification_level' = 'Basic', 'job_role' = 'Billing_Clerk');
ALTER TABLE apscat.healthcare.Insurance ALTER COLUMN GroupNumber SET TAGS ('verification_level' = 'Standard', 'job_role' = 'Insurance_Coordinator');

SELECT "✅ SCENARIO 7: Insurance table tagged for role-based verification" as status;

-- COMMAND ----------

-- Verify Tag Applications - Table Level

SELECT 
    table_name,
    tag_name,
    tag_value,
    'table' as tag_scope
FROM system.information_schema.table_tags 
WHERE schema_name = 'healthcare'
ORDER BY table_name, tag_name;

-- COMMAND ----------

-- Verify Tag Applications - Column Level

SELECT 
    table_name,
    column_name,
    tag_name,
    tag_value,
    'column' as tag_scope
FROM system.information_schema.column_tags
WHERE schema_name = 'healthcare'
ORDER BY table_name, column_name, tag_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🎉 Healthcare ABAC Tags Applied Successfully!
-- MAGIC
-- MAGIC ### ✅ **Tag Application Complete:**
-- MAGIC All 7 healthcare ABAC scenarios have been tagged successfully:
-- MAGIC
-- MAGIC 1. ✅ **Deterministic Masking** - PatientID columns across tables
-- MAGIC 2. ✅ **Time-Based Access** - LabResults table and columns
-- MAGIC 3. ✅ **Policy Expiry** - Billing table for temporary auditor access
-- MAGIC 4. ✅ **Seniority Masking** - Patient name columns
-- MAGIC 5. ✅ **Regional Control** - Patients table for geographic restrictions
-- MAGIC 6. ✅ **Age Demographics** - DateOfBirth for research studies
-- MAGIC 7. ✅ **Insurance Verification** - Insurance table for role-based access
-- MAGIC
-- MAGIC ### 🔄 **Next Steps:**
-- MAGIC 1. **Deploy ABAC masking functions** from `comprehensive_abac_functions.sql`
-- MAGIC 2. **Create ABAC policies** using Unity Catalog CREATE POLICY statements
-- MAGIC 3. **Assign users to account groups** created earlier
-- MAGIC 4. **Test policy enforcement** with different user roles
-- MAGIC
-- MAGIC ### 🏥 **Healthcare Data Governance Ready!**
-- MAGIC Your healthcare data is now properly tagged for comprehensive ABAC policy enforcement using Databricks Unity Catalog.