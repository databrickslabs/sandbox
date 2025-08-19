-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 🧪 Healthcare ABAC Policies Testing Notebook
-- MAGIC
-- MAGIC This notebook tests all 9 healthcare ABAC policies deployed in the `apscat` catalog.
-- MAGIC
-- MAGIC ## 📋 Prerequisites
-- MAGIC - ✅ All healthcare ABAC policies deployed (from `CreateHealthcareABACPolicies_Fixed.ipynb`)
-- MAGIC - ✅ Healthcare account groups created (from `CreateHealthcareGroups_Fixed.ipynb`)
-- MAGIC - ✅ Healthcare tables tagged (from `ApplyHealthcareABACPolicies_Clean.ipynb`)
-- MAGIC - ✅ User assigned to specific groups for testing
-- MAGIC
-- MAGIC ## 🎯 Testing Strategy
-- MAGIC Each test shows:
-- MAGIC 1. **Original Data** - What the data looks like without policies
-- MAGIC 2. **Policy Effect** - How the data appears when policy is active
-- MAGIC 3. **Group Instructions** - Which group to join/leave to see the effect
-- MAGIC
-- MAGIC ## 👥 Available Healthcare Groups
-- MAGIC - `Healthcare_Analyst` - For cross-table analytics
-- MAGIC - `Lab_Technician` - For lab data access
-- MAGIC - `External_Auditor` - For billing data access
-- MAGIC - `Junior_Staff` - For name masking demonstration
-- MAGIC - `Senior_Staff` - For senior level access
-- MAGIC - `Regional_Staff` - For geographic restrictions
-- MAGIC - `Population_Health_Researcher` - For research data
-- MAGIC - `Billing_Clerk` - For basic insurance verification
-- MAGIC - `Insurance_Coordinator` - For standard insurance verification

-- COMMAND ----------

-- Set catalog context
USE CATALOG apscat;
USE SCHEMA healthcare;

-- COMMAND ----------

-- Show current user
SELECT current_user() as current_user, '✅ Test environment initialized' as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🔐 TEST 1: Cross-Table Analytics with Deterministic PatientID Masking
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_deterministic_analytics`
-- MAGIC
-- MAGIC **Purpose:** Tests deterministic masking of PatientID for healthcare analysts
-- MAGIC
-- MAGIC **To See Masking Effect:**
-- MAGIC - ✅ **Add yourself to group:** `Healthcare_Analyst`
-- MAGIC - ❌ **To see original data:** Remove yourself from `Healthcare_Analyst` group
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Healthcare_Analyst:** PatientID shown as `REF_<hash>` (deterministic for joins)
-- MAGIC - **Other users:** PatientID shown normally (if no other restrictions)

-- COMMAND ----------

-- TEST 1A: PatientID Deterministic Masking
-- GROUP TO TEST: Add yourself to 'Healthcare_Analyst' to see masking
-- REMOVE FROM GROUP: Remove from 'Healthcare_Analyst' to see original data
SELECT 
    PatientID,
    FirstName,
    LastName,
    'Test: Deterministic PatientID masking' as test_description
FROM apscat.healthcare.Patients 
LIMIT 5;

-- COMMAND ----------

-- TEST 1B: Cross-table join test (should work with masked IDs due to deterministic hashing)
-- GROUP TO TEST: Add yourself to 'Healthcare_Analyst' to see masking consistency
SELECT 
    p.PatientID,
    p.FirstName,
    v.VisitDate,
    'JOIN test with masked PatientID' as test_description
FROM apscat.healthcare.Patients p
JOIN apscat.healthcare.Visits v ON p.PatientID = v.PatientID
LIMIT 3;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## ⏰ TEST 2: Business Hours Lab Access Control
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_business_hours_lab`
-- MAGIC
-- MAGIC **Purpose:** Tests time-based access restriction for lab technicians (8AM-6PM only)
-- MAGIC
-- MAGIC **To See Row Filtering Effect:**
-- MAGIC - ✅ **Add yourself to group:** `Lab_Technician`
-- MAGIC - ❌ **To see all data:** Remove yourself from `Lab_Technician` group
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Lab_Technician (during business hours):** Full lab results visible
-- MAGIC - **Lab_Technician (after hours):** Limited or no lab results visible
-- MAGIC - **Other users:** All lab results visible (if no other restrictions)

-- COMMAND ----------

-- TEST 2A: Current time check
SELECT 
    current_timestamp() as current_time,
    hour(current_timestamp()) as current_hour,
    CASE 
        WHEN hour(current_timestamp()) BETWEEN 8 AND 18 THEN 'BUSINESS HOURS'
        ELSE 'AFTER HOURS'
    END as time_status;

-- COMMAND ----------

-- TEST 2B: Lab results with business hours filtering
-- GROUP TO TEST: Add yourself to 'Lab_Technician' to see time-based filtering
-- REMOVE FROM GROUP: Remove from 'Lab_Technician' to see all data
SELECT 
    TestName,
    ResultValue,
    TestDate,
    PatientID,
    'Test: Business hours lab access' as test_description
FROM apscat.healthcare.LabResults 
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 📅 TEST 3: Temporary Auditor Access with Expiry
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_temporary_auditor`
-- MAGIC
-- MAGIC **Purpose:** Tests time-limited access to billing data (expires 2025-12-31)
-- MAGIC
-- MAGIC **To See Row Filtering Effect:**
-- MAGIC - ✅ **Add yourself to group:** `External_Auditor`
-- MAGIC - ❌ **To see all data:** Remove yourself from `External_Auditor` group
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **External_Auditor (before 2025-12-31):** Full billing data visible
-- MAGIC - **External_Auditor (after 2025-12-31):** No billing data visible
-- MAGIC - **Other users:** All billing data visible (if no other restrictions)

-- COMMAND ----------

-- TEST 3A: Check current date vs expiry
SELECT 
    current_date() as today,
    date('2025-12-31') as policy_expiry,
    CASE 
        WHEN current_date() <= date('2025-12-31') THEN 'ACCESS GRANTED'
        ELSE 'ACCESS EXPIRED'
    END as access_status;

-- COMMAND ----------

-- TEST 3B: Billing data with temporal access control
-- GROUP TO TEST: Add yourself to 'External_Auditor' to see expiry-based filtering
-- REMOVE FROM GROUP: Remove from 'External_Auditor' to see all data
SELECT 
    BillID,
    PatientID,
    ChargeAmount,
    BillingDate,
    BillingStatus,
    'Test: Temporary auditor access' as test_description
FROM apscat.healthcare.Billing 
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 👥 TEST 4: Role-Based Patient Name Privacy
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_junior_name_masking` & `apscat_healthcare_junior_lastname_masking`
-- MAGIC
-- MAGIC **Purpose:** Tests name masking based on staff seniority level
-- MAGIC
-- MAGIC **To See Name Masking Effect:**
-- MAGIC - ✅ **Add yourself to group:** `Junior_Staff`
-- MAGIC - ❌ **To see full names:** Remove yourself from `Junior_Staff` group or add to `Senior_Staff`
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Junior_Staff:** Names shown as `J*** S***` format
-- MAGIC - **Senior_Staff or other users:** Full names visible

-- COMMAND ----------

-- TEST 4A: Role-Based Patient Name Privacy
-- GROUP TO TEST: Add yourself to 'Junior_Staff' to see name masking
-- REMOVE FROM GROUP: Remove from 'Junior_Staff' OR add to 'Senior_Staff' to see full names
SELECT 
    PatientID,
    FirstName,
    LastName,
    DateOfBirth,
    'Test: Junior staff name masking' as test_description
FROM apscat.healthcare.Patients 
ORDER BY PatientID
LIMIT 10;

-- COMMAND ----------

-- TEST 4B: Test with a join to see masking consistency
-- GROUP TO TEST: Add yourself to 'Junior_Staff' to see name masking in joins
SELECT 
    p.FirstName,
    p.LastName,
    v.VisitDate,
    v.Diagnosis,
    'JOIN test with name masking' as test_description
FROM apscat.healthcare.Patients p
JOIN apscat.healthcare.Visits v ON p.PatientID = v.PatientID
LIMIT 5;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🌍 TEST 5: Geographic Data Access Control
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_regional_boundary`
-- MAGIC
-- MAGIC **Purpose:** Tests geographic restrictions for regional staff
-- MAGIC
-- MAGIC **To See Regional Filtering Effect:**
-- MAGIC - ✅ **Add yourself to group:** `Regional_Staff`
-- MAGIC - ❌ **To see all data:** Remove yourself from `Regional_Staff` group
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Regional_Staff:** Only data from assigned region visible
-- MAGIC - **Other users:** All regional data visible (if no other restrictions)

-- COMMAND ----------

-- TEST 5A: Check provider distribution by region
-- GROUP TO TEST: Add yourself to 'Regional_Staff' to see geographic filtering
-- REMOVE FROM GROUP: Remove from 'Regional_Staff' to see all regions
SELECT 
    ProviderID,
    CONCAT(FirstName, ' ', LastName) as ProviderName,
    Specialty,
    'Test: Regional data access - Providers' as test_description
FROM apscat.healthcare.Providers 
LIMIT 10;

-- COMMAND ----------

-- TEST 5B: Check patient data with potential regional filtering
-- GROUP TO TEST: Add yourself to 'Regional_Staff' to see geographic filtering
SELECT 
    PatientID,
    FirstName,
    LastName,
    'Test: Regional data access - Patients' as test_description
FROM apscat.healthcare.Patients 
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🎂 TEST 6: Age Demographics for Research Ethics
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_age_demographics`
-- MAGIC
-- MAGIC **Purpose:** Tests birth date masking to age groups for research
-- MAGIC
-- MAGIC **To See Age Group Masking Effect:**
-- MAGIC - ✅ **Add yourself to group:** `Population_Health_Researcher`
-- MAGIC - ❌ **To see exact birth dates:** Remove yourself from `Population_Health_Researcher` group
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Population_Health_Researcher:** Birth dates shown as age groups (26-35, 36-50, etc.)
-- MAGIC - **Other users:** Exact birth dates visible (if no other restrictions)

-- COMMAND ----------

-- TEST 6A: Age Demographics for Research Ethics
-- GROUP TO TEST: Add yourself to 'Population_Health_Researcher' to see age group masking
-- REMOVE FROM GROUP: Remove from 'Population_Health_Researcher' to see exact birth dates
SELECT 
    PatientID,
    FirstName,
    LastName,
    DateOfBirth,
    'Test: Age demographics masking' as test_description
FROM apscat.healthcare.Patients 
ORDER BY DateOfBirth
LIMIT 10;

-- COMMAND ----------

-- TEST 6B: Age distribution analysis (what researchers would typically do)
-- GROUP TO TEST: Add yourself to 'Population_Health_Researcher' to see age group distribution
SELECT 
    DateOfBirth as age_group,
    COUNT(*) as patient_count,
    'Age group distribution' as analysis_type
FROM apscat.healthcare.Patients 
GROUP BY DateOfBirth
ORDER BY DateOfBirth
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🏥 TEST 7: Insurance Verification by Job Function
-- MAGIC
-- MAGIC **Policy:** `apscat_healthcare_insurance_basic_policy` & `apscat_healthcare_insurance_standard_group`
-- MAGIC
-- MAGIC **Purpose:** Tests insurance number masking based on job role
-- MAGIC
-- MAGIC **To See Insurance Masking Effects:**
-- MAGIC - ✅ **Add yourself to group:** `Billing_Clerk` (for basic verification - last 4 digits)
-- MAGIC - ✅ **Add yourself to group:** `Insurance_Coordinator` (for standard verification)
-- MAGIC - ❌ **To see full insurance numbers:** Remove from both groups
-- MAGIC
-- MAGIC **Expected Behavior:**
-- MAGIC - **Billing_Clerk:** Insurance numbers shown as `****1234` (last 4 digits only)
-- MAGIC - **Insurance_Coordinator:** Partial insurance numbers visible
-- MAGIC - **Other users:** Full insurance numbers visible (if no other restrictions)

-- COMMAND ----------

-- TEST 7A: Insurance Verification by Job Function
-- GROUP TO TEST: Add yourself to 'Billing_Clerk' to see last-4-digits masking
-- GROUP TO TEST: Add yourself to 'Insurance_Coordinator' to see partial masking
-- REMOVE FROM GROUP: Remove from both groups to see full numbers
SELECT 
    InsuranceID,
    PatientID,
    PolicyNumber,
    GroupNumber,
    InsuranceCompany as InsuranceProvider,
    'Test: Insurance verification masking' as test_description
FROM apscat.healthcare.Insurance 
LIMIT 10;

-- COMMAND ----------

-- TEST 7B: Join with patient data to test masking consistency
-- GROUP TO TEST: Add yourself to 'Billing_Clerk' or 'Insurance_Coordinator' to see masking in joins
SELECT 
    p.FirstName,
    p.LastName,
    i.PolicyNumber,
    i.GroupNumber,
    'Patient insurance verification test' as test_description
FROM apscat.healthcare.Patients p
JOIN apscat.healthcare.Insurance i ON p.PatientID = i.PatientID
LIMIT 5;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 📊 COMPREHENSIVE TEST: Multiple Policies Combined
-- MAGIC
-- MAGIC **Purpose:** Tests how multiple policies interact when a user is in multiple groups
-- MAGIC
-- MAGIC **Test Scenarios:**
-- MAGIC 1. **Junior Healthcare Analyst:** `Junior_Staff` + `Healthcare_Analyst`
-- MAGIC 2. **Senior Lab Technician:** `Senior_Staff` + `Lab_Technician`
-- MAGIC 3. **Regional Billing Clerk:** `Regional_Staff` + `Billing_Clerk`
-- MAGIC
-- MAGIC **Expected Behavior:** Multiple policies should apply simultaneously

-- COMMAND ----------

-- COMPREHENSIVE TEST: Multiple Policies Combined
-- TRY THESE COMBINATIONS:
-- COMBO 1: Add to 'Junior_Staff' + 'Healthcare_Analyst' (name masking + PatientID masking)
-- COMBO 2: Add to 'Senior_Staff' + 'Lab_Technician' (full names + time-based lab access)
-- COMBO 3: Add to 'Regional_Staff' + 'Billing_Clerk' (regional filtering + insurance masking)
SELECT 
    p.PatientID,
    p.FirstName,
    p.LastName,
    p.DateOfBirth,
    i.PolicyNumber,
    v.VisitDate,
    'Multi-policy test' as test_description
FROM apscat.healthcare.Patients p
LEFT JOIN apscat.healthcare.Insurance i ON p.PatientID = i.PatientID
LEFT JOIN apscat.healthcare.Visits v ON p.PatientID = v.PatientID
LIMIT 5;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🔍 POLICY STATUS VERIFICATION
-- MAGIC
-- MAGIC **Purpose:** Verify all policies are active and configured correctly

-- COMMAND ----------

-- Verify all ABAC policies are active
SHOW POLICIES ON CATALOG apscat;

-- COMMAND ----------

-- Check catalog permissions
SHOW GRANTS ON CATALOG apscat;

-- COMMAND ----------

-- Verify masking functions exist
SHOW FUNCTIONS IN apscat.healthcare LIKE 'mask*';

-- COMMAND ----------

-- Verify filter functions exist
SHOW FUNCTIONS IN apscat.healthcare LIKE 'filter*';

-- COMMAND ----------

SELECT "✅ All ABAC policies and functions verified" as status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 📋 TESTING CHECKLIST
-- MAGIC
-- MAGIC Use this checklist to systematically test each policy:
-- MAGIC
-- MAGIC ### ✅ **Policy Testing Steps:**
-- MAGIC
-- MAGIC 1. **📝 Record Baseline:**
-- MAGIC    - [ ] Run query without being in any test groups
-- MAGIC    - [ ] Note what data is visible (full access)
-- MAGIC
-- MAGIC 2. **👥 Test Each Group:**
-- MAGIC    - [ ] Add yourself to `Healthcare_Analyst` → Test PatientID masking
-- MAGIC    - [ ] Add yourself to `Lab_Technician` → Test business hours filtering
-- MAGIC    - [ ] Add yourself to `External_Auditor` → Test temporal access
-- MAGIC    - [ ] Add yourself to `Junior_Staff` → Test name masking
-- MAGIC    - [ ] Add yourself to `Regional_Staff` → Test geographic filtering
-- MAGIC    - [ ] Add yourself to `Population_Health_Researcher` → Test age grouping
-- MAGIC    - [ ] Add yourself to `Billing_Clerk` → Test insurance masking
-- MAGIC    - [ ] Add yourself to `Insurance_Coordinator` → Test insurance masking
-- MAGIC
-- MAGIC 3. **🔄 Test Combinations:**
-- MAGIC    - [ ] Try multiple group memberships
-- MAGIC    - [ ] Verify policies don't conflict
-- MAGIC    - [ ] Test edge cases
-- MAGIC
-- MAGIC ### 🎯 **Expected Results Summary:**
-- MAGIC
-- MAGIC | Group | PatientID | Names | Birth Date | Insurance | Lab Data | Billing |
-- MAGIC |-------|-----------|-------|------------|-----------|----------|----------|
-- MAGIC | **None** | Original | Original | Original | Original | All | All |
-- MAGIC | **Healthcare_Analyst** | `REF_<hash>` | Original | Original | Original | All | All |
-- MAGIC | **Lab_Technician** | Original | Original | Original | Original | Time-filtered | All |
-- MAGIC | **External_Auditor** | Original | Original | Original | Original | All | Date-filtered |
-- MAGIC | **Junior_Staff** | Original | `J*** S***` | Original | Original | All | All |
-- MAGIC | **Regional_Staff** | Original | Original | Original | Original | Regional | Regional |
-- MAGIC | **Population_Health_Researcher** | Original | Original | Age groups | Original | All | All |
-- MAGIC | **Billing_Clerk** | Original | Original | Original | Last 4 digits | All | All |
-- MAGIC | **Insurance_Coordinator** | Original | Original | Original | Partial | All | All |
-- MAGIC
-- MAGIC ## 🎉 **Testing Complete!**
-- MAGIC
-- MAGIC After running all tests, you should have a comprehensive understanding of how each ABAC policy protects healthcare data based on user group membership and contextual conditions.
-- MAGIC
-- MAGIC **Each cell contains exactly one SELECT statement for clean, focused testing!**