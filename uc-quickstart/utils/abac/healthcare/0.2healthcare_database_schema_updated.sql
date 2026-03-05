-- =============================================
-- HEALTHCARE DATABASE SCHEMA FOR DATABRICKS
-- Updated Version with Configurable Catalog
-- Purpose: Testing and demonstration with synthetic data
-- Usage: Set CATALOG_NAME variable before execution
-- =============================================

-- CONFIGURATION: IMPORTANT - Replace ${CATALOG_NAME} with your actual catalog name
-- Examples: 'apscat', 'main', 'your_catalog_name'
-- Note: Variable substitution (${VARIABLE}) doesn't work reliably in all SQL contexts
-- Therefore, you MUST replace ${CATALOG_NAME} with your actual catalog name before execution

-- Create and use the target catalog and schema
-- REQUIRED: Replace ${CATALOG_NAME} with your actual catalog name (e.g., 'apscat', 'main', etc.)
USE CATALOG ${CATALOG_NAME};
CREATE SCHEMA IF NOT EXISTS healthcare
COMMENT 'Healthcare data schema for ABAC demonstration and testing';
USE SCHEMA healthcare;

-- =============================================
-- TABLE 1: PATIENTS
-- Primary table containing patient demographics
-- =============================================
DROP TABLE IF EXISTS Patients;

CREATE TABLE Patients (
    PatientID STRING NOT NULL,
    FirstName STRING NOT NULL,
    LastName STRING NOT NULL,
    DateOfBirth DATE NOT NULL,
    Gender STRING NOT NULL,
    PhoneNumber STRING,
    Email STRING,
    Address STRING,
    City STRING,
    State STRING,
    ZipCode STRING,
    EmergencyContact STRING,
    EmergencyPhone STRING,
    BloodType STRING,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_patients PRIMARY KEY (PatientID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Patient demographics and contact information for healthcare system';

-- Insert synthetic patient data
INSERT INTO Patients VALUES
('PAT001', 'John', 'Smith', '1975-03-15', 'Male', '555-0101', 'john.smith@email.com', '123 Main St', 'Seattle', 'WA', '98101', 'Jane Smith', '555-0102', 'O+', '2024-01-01 10:00:00'),
('PAT002', 'Sarah', 'Johnson', '1982-07-22', 'Female', '555-0201', 'sarah.j@email.com', '456 Oak Ave', 'Portland', 'OR', '97201', 'Mike Johnson', '555-0202', 'A+', '2024-01-02 11:00:00'),
('PAT003', 'Michael', 'Brown', '1990-11-08', 'Male', '555-0301', 'mbrown@email.com', '789 Pine St', 'San Francisco', 'CA', '94101', 'Lisa Brown', '555-0302', 'B+', '2024-01-03 12:00:00'),
('PAT004', 'Emily', 'Davis', '1988-05-12', 'Female', '555-0401', 'emily.davis@email.com', '321 Elm St', 'Los Angeles', 'CA', '90210', 'Tom Davis', '555-0402', 'AB+', '2024-01-04 13:00:00'),
('PAT005', 'David', 'Wilson', '1965-09-30', 'Male', '555-0501', 'dwilson@email.com', '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'Carol Wilson', '555-0502', 'O-', '2024-01-05 14:00:00'),
('PAT006', 'Jennifer', 'Martinez', '1993-12-18', 'Female', '555-0601', 'jmartinez@email.com', '987 Cedar Ln', 'Denver', 'CO', '80201', 'Carlos Martinez', '555-0602', 'A-', '2024-01-06 15:00:00'),
('PAT007', 'Robert', 'Anderson', '1978-04-25', 'Male', '555-0701', 'randerson@email.com', '147 Birch Ave', 'Austin', 'TX', '73301', 'Mary Anderson', '555-0702', 'B-', '2024-01-07 16:00:00'),
('PAT008', 'Lisa', 'Taylor', '1985-08-14', 'Female', '555-0801', 'ltaylor@email.com', '258 Spruce St', 'Miami', 'FL', '33101', 'John Taylor', '555-0802', 'AB-', '2024-01-08 17:00:00'),
('PAT009', 'Christopher', 'Thomas', '1972-01-07', 'Male', '555-0901', 'cthomas@email.com', '369 Willow Rd', 'Chicago', 'IL', '60601', 'Susan Thomas', '555-0902', 'O+', '2024-01-09 18:00:00'),
('PAT010', 'Amanda', 'Jackson', '1991-06-03', 'Female', '555-1001', 'ajackson@email.com', '741 Aspen Ct', 'Boston', 'MA', '02101', 'James Jackson', '555-1002', 'A+', '2024-01-10 19:00:00'),
('PAT011', 'Kevin', 'White', '1987-10-16', 'Male', '555-1101', 'kwhite@email.com', '852 Poplar St', 'Atlanta', 'GA', '30301', 'Linda White', '555-1102', 'B+', '2024-01-11 20:00:00'),
('PAT012', 'Michelle', 'Harris', '1979-02-28', 'Female', '555-1201', 'mharris@email.com', '963 Hickory Ave', 'Dallas', 'TX', '75201', 'Paul Harris', '555-1202', 'AB+', '2024-01-12 21:00:00'),
('PAT013', 'Daniel', 'Martin', '1983-12-11', 'Male', '555-1301', 'dmartin@email.com', '159 Walnut Dr', 'Nashville', 'TN', '37201', 'Nancy Martin', '555-1302', 'O-', '2024-01-13 22:00:00'),
('PAT014', 'Rachel', 'Thompson', '1995-05-29', 'Female', '555-1401', 'rthompson@email.com', '357 Cherry Ln', 'Las Vegas', 'NV', '89101', 'Steve Thompson', '555-1402', 'A-', '2024-01-14 23:00:00'),
('PAT015', 'Matthew', 'Garcia', '1974-09-02', 'Male', '555-1501', 'mgarcia@email.com', '486 Dogwood Ct', 'San Diego', 'CA', '92101', 'Maria Garcia', '555-1502', 'B-', '2024-01-15 08:00:00'),
('PAT016', 'Jessica', 'Rodriguez', '1989-07-19', 'Female', '555-1601', 'jrodriguez@email.com', '729 Magnolia St', 'Tampa', 'FL', '33601', 'Luis Rodriguez', '555-1602', 'AB-', '2024-01-16 09:00:00'),
('PAT017', 'Andrew', 'Lewis', '1976-03-06', 'Male', '555-1701', 'alewis@email.com', '618 Sycamore Ave', 'Minneapolis', 'MN', '55401', 'Beth Lewis', '555-1702', 'O+', '2024-01-17 10:00:00'),
('PAT018', 'Nicole', 'Lee', '1992-11-23', 'Female', '555-1801', 'nlee@email.com', '507 Redwood Dr', 'Portland', 'OR', '97202', 'Kevin Lee', '555-1802', 'A+', '2024-01-18 11:00:00'),
('PAT019', 'Joshua', 'Walker', '1981-08-08', 'Male', '555-1901', 'jwalker@email.com', '394 Fir St', 'Salt Lake City', 'UT', '84101', 'Amy Walker', '555-1902', 'B+', '2024-01-19 12:00:00'),
('PAT020', 'Stephanie', 'Hall', '1986-04-17', 'Female', '555-2001', 'shall@email.com', '283 Palm Ave', 'Sacramento', 'CA', '95814', 'Greg Hall', '555-2002', 'AB+', '2024-01-20 13:00:00');

-- =============================================
-- TABLE 2: PROVIDERS
-- Healthcare providers (doctors, nurses, specialists)
-- =============================================
DROP TABLE IF EXISTS Providers;

CREATE TABLE Providers (
    ProviderID STRING NOT NULL,
    FirstName STRING NOT NULL,
    LastName STRING NOT NULL,
    Specialty STRING NOT NULL,
    LicenseNumber STRING NOT NULL,
    PhoneNumber STRING,
    Email STRING,
    Department STRING,
    HireDate DATE,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_providers PRIMARY KEY (ProviderID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Healthcare providers including doctors, nurses, and specialists';

-- Insert synthetic provider data
INSERT INTO Providers VALUES
('PRV001', 'Dr. William', 'Chen', 'Cardiology', 'LIC001234', '555-9001', 'w.chen@hospital.com', 'Cardiology', '2020-01-15', TRUE, '2024-01-01 10:00:00'),
('PRV002', 'Dr. Maria', 'Rodriguez', 'Internal Medicine', 'LIC002345', '555-9002', 'm.rodriguez@hospital.com', 'Internal Medicine', '2019-03-22', TRUE, '2024-01-02 11:00:00'),
('PRV003', 'Dr. James', 'Thompson', 'Emergency Medicine', 'LIC003456', '555-9003', 'j.thompson@hospital.com', 'Emergency', '2021-06-10', TRUE, '2024-01-03 12:00:00'),
('PRV004', 'Dr. Sarah', 'Kim', 'Pediatrics', 'LIC004567', '555-9004', 's.kim@hospital.com', 'Pediatrics', '2018-09-08', TRUE, '2024-01-04 13:00:00'),
('PRV005', 'Dr. Robert', 'Johnson', 'Orthopedics', 'LIC005678', '555-9005', 'r.johnson@hospital.com', 'Orthopedics', '2017-11-12', TRUE, '2024-01-05 14:00:00'),
('PRV006', 'Dr. Lisa', 'Davis', 'Dermatology', 'LIC006789', '555-9006', 'l.davis@hospital.com', 'Dermatology', '2022-02-28', TRUE, '2024-01-06 15:00:00'),
('PRV007', 'Dr. Michael', 'Wilson', 'Neurology', 'LIC007890', '555-9007', 'm.wilson@hospital.com', 'Neurology', '2019-07-14', TRUE, '2024-01-07 16:00:00'),
('PRV008', 'Dr. Jennifer', 'Brown', 'Oncology', 'LIC008901', '555-9008', 'j.brown@hospital.com', 'Oncology', '2020-05-03', TRUE, '2024-01-08 17:00:00'),
('PRV009', 'Dr. David', 'Miller', 'Psychiatry', 'LIC009012', '555-9009', 'd.miller@hospital.com', 'Psychiatry', '2021-10-17', TRUE, '2024-01-09 18:00:00'),
('PRV010', 'Dr. Amanda', 'Garcia', 'Gynecology', 'LIC010123', '555-9010', 'a.garcia@hospital.com', 'Gynecology', '2018-12-05', TRUE, '2024-01-10 19:00:00'),
('PRV011', 'Dr. Christopher', 'Martinez', 'Radiology', 'LIC011234', '555-9011', 'c.martinez@hospital.com', 'Radiology', '2019-04-21', TRUE, '2024-01-11 20:00:00'),
('PRV012', 'Dr. Emily', 'Anderson', 'Anesthesiology', 'LIC012345', '555-9012', 'e.anderson@hospital.com', 'Anesthesiology', '2020-08-30', TRUE, '2024-01-12 21:00:00'),
('PRV013', 'Dr. Kevin', 'Taylor', 'Pulmonology', 'LIC013456', '555-9013', 'k.taylor@hospital.com', 'Pulmonology', '2017-01-18', TRUE, '2024-01-13 22:00:00'),
('PRV014', 'Dr. Rachel', 'Thomas', 'Endocrinology', 'LIC014567', '555-9014', 'r.thomas@hospital.com', 'Endocrinology', '2022-03-12', TRUE, '2024-01-14 23:00:00'),
('PRV015', 'Dr. Matthew', 'Jackson', 'Gastroenterology', 'LIC015678', '555-9015', 'm.jackson@hospital.com', 'Gastroenterology', '2018-06-27', TRUE, '2024-01-15 08:00:00'),
('PRV016', 'Dr. Jessica', 'White', 'Nephrology', 'LIC016789', '555-9016', 'j.white@hospital.com', 'Nephrology', '2021-09-14', TRUE, '2024-01-16 09:00:00'),
('PRV017', 'Dr. Andrew', 'Harris', 'Urology', 'LIC017890', '555-9017', 'a.harris@hospital.com', 'Urology', '2019-12-08', TRUE, '2024-01-17 10:00:00'),
('PRV018', 'Dr. Nicole', 'Martin', 'Rheumatology', 'LIC018901', '555-9018', 'n.martin@hospital.com', 'Rheumatology', '2020-11-23', TRUE, '2024-01-18 11:00:00'),
('PRV019', 'Dr. Joshua', 'Lee', 'Infectious Disease', 'LIC019012', '555-9019', 'j.lee@hospital.com', 'Internal Medicine', '2018-04-06', TRUE, '2024-01-19 12:00:00'),
('PRV020', 'Dr. Stephanie', 'Walker', 'Family Medicine', 'LIC020123', '555-9020', 's.walker@hospital.com', 'Family Medicine', '2022-07-19', TRUE, '2024-01-20 13:00:00');

-- =============================================
-- TABLE 3: INSURANCE
-- Insurance coverage information for patients
-- =============================================
DROP TABLE IF EXISTS Insurance;

CREATE TABLE Insurance (
    InsuranceID STRING NOT NULL,
    PatientID STRING NOT NULL,
    InsuranceCompany STRING NOT NULL,
    PolicyNumber STRING NOT NULL,
    GroupNumber STRING,
    PlanType STRING NOT NULL,
    CoverageStartDate DATE NOT NULL,
    CoverageEndDate DATE,
    Deductible DECIMAL(10,2),
    CoPayAmount DECIMAL(10,2),
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_insurance PRIMARY KEY (InsuranceID),
    CONSTRAINT fk_insurance_patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Patient insurance coverage information and policy details';

-- Insert synthetic insurance data
INSERT INTO Insurance VALUES
('INS001', 'PAT001', 'Blue Cross Blue Shield', 'BCBS001234567', 'GRP001', 'PPO', '2024-01-01', '2024-12-31', 1500.00, 25.00, TRUE, '2024-01-01 10:00:00'),
('INS002', 'PAT002', 'Aetna', 'AET002345678', 'GRP002', 'HMO', '2024-01-01', '2024-12-31', 2000.00, 30.00, TRUE, '2024-01-02 11:00:00'),
('INS003', 'PAT003', 'Cigna', 'CIG003456789', 'GRP003', 'PPO', '2024-01-01', '2024-12-31', 1000.00, 20.00, TRUE, '2024-01-03 12:00:00'),
('INS004', 'PAT004', 'UnitedHealth', 'UHC004567890', 'GRP004', 'EPO', '2024-01-01', '2024-12-31', 2500.00, 35.00, TRUE, '2024-01-04 13:00:00'),
('INS005', 'PAT005', 'Kaiser Permanente', 'KP005678901', 'GRP005', 'HMO', '2024-01-01', '2024-12-31', 1200.00, 15.00, TRUE, '2024-01-05 14:00:00'),
('INS006', 'PAT006', 'Humana', 'HUM006789012', 'GRP006', 'PPO', '2024-01-01', '2024-12-31', 1800.00, 25.00, TRUE, '2024-01-06 15:00:00'),
('INS007', 'PAT007', 'Blue Cross Blue Shield', 'BCBS007890123', 'GRP007', 'HMO', '2024-01-01', '2024-12-31', 1600.00, 20.00, TRUE, '2024-01-07 16:00:00'),
('INS008', 'PAT008', 'Aetna', 'AET008901234', 'GRP008', 'PPO', '2024-01-01', '2024-12-31', 2200.00, 30.00, TRUE, '2024-01-08 17:00:00'),
('INS009', 'PAT009', 'Cigna', 'CIG009012345', 'GRP009', 'EPO', '2024-01-01', '2024-12-31', 1400.00, 25.00, TRUE, '2024-01-09 18:00:00'),
('INS010', 'PAT010', 'UnitedHealth', 'UHC010123456', 'GRP010', 'PPO', '2024-01-01', '2024-12-31', 1900.00, 35.00, TRUE, '2024-01-10 19:00:00'),
('INS011', 'PAT011', 'Kaiser Permanente', 'KP011234567', 'GRP011', 'HMO', '2024-01-01', '2024-12-31', 1300.00, 15.00, TRUE, '2024-01-11 20:00:00'),
('INS012', 'PAT012', 'Humana', 'HUM012345678', 'GRP012', 'PPO', '2024-01-01', '2024-12-31', 2100.00, 25.00, TRUE, '2024-01-12 21:00:00'),
('INS013', 'PAT013', 'Blue Cross Blue Shield', 'BCBS013456789', 'GRP013', 'HMO', '2024-01-01', '2024-12-31', 1700.00, 20.00, TRUE, '2024-01-13 22:00:00'),
('INS014', 'PAT014', 'Aetna', 'AET014567890', 'GRP014', 'EPO', '2024-01-01', '2024-12-31', 2300.00, 30.00, TRUE, '2024-01-14 23:00:00'),
('INS015', 'PAT015', 'Cigna', 'CIG015678901', 'GRP015', 'PPO', '2024-01-01', '2024-12-31', 1500.00, 25.00, TRUE, '2024-01-15 08:00:00'),
('INS016', 'PAT016', 'UnitedHealth', 'UHC016789012', 'GRP016', 'HMO', '2024-01-01', '2024-12-31', 2000.00, 35.00, TRUE, '2024-01-16 09:00:00'),
('INS017', 'PAT017', 'Kaiser Permanente', 'KP017890123', 'GRP017', 'PPO', '2024-01-01', '2024-12-31', 1100.00, 15.00, TRUE, '2024-01-17 10:00:00'),
('INS018', 'PAT018', 'Humana', 'HUM018901234', 'GRP018', 'EPO', '2024-01-01', '2024-12-31', 2400.00, 25.00, TRUE, '2024-01-18 11:00:00'),
('INS019', 'PAT019', 'Blue Cross Blue Shield', 'BCBS019012345', 'GRP019', 'HMO', '2024-01-01', '2024-12-31', 1800.00, 20.00, TRUE, '2024-01-19 12:00:00'),
('INS020', 'PAT020', 'Aetna', 'AET020123456', 'GRP020', 'PPO', '2024-01-01', '2024-12-31', 2600.00, 30.00, TRUE, '2024-01-20 13:00:00');

-- =============================================
-- TABLE 4: VISITS
-- Patient visits and appointments
-- =============================================
DROP TABLE IF EXISTS Visits;

CREATE TABLE Visits (
    VisitID STRING NOT NULL,
    PatientID STRING NOT NULL,
    ProviderID STRING NOT NULL,
    VisitDate DATE NOT NULL,
    VisitTime TIMESTAMP NOT NULL,
    VisitType STRING NOT NULL,
    ChiefComplaint STRING,
    Diagnosis STRING,
    TreatmentPlan STRING,
    VisitStatus STRING NOT NULL,
    Duration INT, -- in minutes
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_visits PRIMARY KEY (VisitID),
    CONSTRAINT fk_visits_patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    CONSTRAINT fk_visits_provider FOREIGN KEY (ProviderID) REFERENCES Providers(ProviderID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Patient visits, appointments, and medical encounters';

-- Insert synthetic visits data
INSERT INTO Visits VALUES
('VIS001', 'PAT001', 'PRV001', '2024-02-15', '2024-02-15 09:00:00', 'Routine Checkup', 'Annual physical exam', 'Hypertension', 'Continue current medication, follow-up in 3 months', 'Completed', 45, '2024-02-15 09:00:00'),
('VIS002', 'PAT002', 'PRV002', '2024-02-16', '2024-02-16 10:30:00', 'Follow-up', 'Diabetes management', 'Type 2 Diabetes', 'Adjust insulin dosage, dietary counseling', 'Completed', 30, '2024-02-16 10:30:00'),
('VIS003', 'PAT003', 'PRV003', '2024-02-17', '2024-02-17 14:15:00', 'Emergency', 'Chest pain', 'Acute myocardial infarction', 'Emergency cardiac intervention', 'Completed', 120, '2024-02-17 14:15:00'),
('VIS004', 'PAT004', 'PRV004', '2024-02-18', '2024-02-18 11:00:00', 'Well-child Visit', 'Routine pediatric checkup', 'Normal development', 'Immunizations up to date, next visit in 6 months', 'Completed', 25, '2024-02-18 11:00:00'),
('VIS005', 'PAT005', 'PRV005', '2024-02-19', '2024-02-19 15:45:00', 'Consultation', 'Knee pain', 'Osteoarthritis', 'Physical therapy, pain management', 'Completed', 40, '2024-02-19 15:45:00'),
('VIS006', 'PAT006', 'PRV006', '2024-02-20', '2024-02-20 13:20:00', 'Routine Checkup', 'Skin lesion evaluation', 'Benign mole', 'Monitor for changes, annual skin check', 'Completed', 20, '2024-02-20 13:20:00'),
('VIS007', 'PAT007', 'PRV007', '2024-02-21', '2024-02-21 16:00:00', 'Consultation', 'Headaches', 'Migraine', 'Prescribed medication, lifestyle modifications', 'Completed', 35, '2024-02-21 16:00:00'),
('VIS008', 'PAT008', 'PRV008', '2024-02-22', '2024-02-22 10:15:00', 'Follow-up', 'Cancer treatment monitoring', 'Breast cancer remission', 'Continue surveillance, next scan in 3 months', 'Completed', 50, '2024-02-22 10:15:00'),
('VIS009', 'PAT009', 'PRV009', '2024-02-23', '2024-02-23 12:30:00', 'Initial Consultation', 'Depression screening', 'Major depressive disorder', 'Start antidepressant therapy, counseling referral', 'Completed', 60, '2024-02-23 12:30:00'),
('VIS010', 'PAT010', 'PRV010', '2024-02-24', '2024-02-24 14:45:00', 'Annual Exam', 'Gynecological exam', 'Normal findings', 'Continue routine screening, next visit in 1 year', 'Completed', 30, '2024-02-24 14:45:00'),
('VIS011', 'PAT011', 'PRV011', '2024-02-25', '2024-02-25 08:30:00', 'Imaging', 'Abdominal pain', 'Gallstones', 'Schedule surgery consultation', 'Completed', 15, '2024-02-25 08:30:00'),
('VIS012', 'PAT012', 'PRV012', '2024-02-26', '2024-02-26 07:00:00', 'Pre-operative', 'Pre-surgery evaluation', 'Cleared for surgery', 'Anesthesia plan reviewed', 'Completed', 20, '2024-02-26 07:00:00'),
('VIS013', 'PAT013', 'PRV013', '2024-02-27', '2024-02-27 11:15:00', 'Consultation', 'Shortness of breath', 'Asthma', 'Inhaler therapy, avoid triggers', 'Completed', 35, '2024-02-27 11:15:00'),
('VIS014', 'PAT014', 'PRV014', '2024-02-28', '2024-02-28 15:30:00', 'Follow-up', 'Thyroid function', 'Hypothyroidism', 'Increase levothyroxine dose', 'Completed', 25, '2024-02-28 15:30:00'),
('VIS015', 'PAT015', 'PRV015', '2024-03-01', '2024-03-01 09:45:00', 'Consultation', 'Stomach pain', 'Gastritis', 'Proton pump inhibitor therapy', 'Completed', 30, '2024-03-01 09:45:00'),
('VIS016', 'PAT016', 'PRV016', '2024-03-02', '2024-03-02 13:00:00', 'Routine Checkup', 'Kidney function monitoring', 'Chronic kidney disease stage 3', 'Continue current treatment', 'Completed', 40, '2024-03-02 13:00:00'),
('VIS017', 'PAT017', 'PRV017', '2024-03-03', '2024-03-03 16:15:00', 'Consultation', 'Urinary symptoms', 'Benign prostatic hyperplasia', 'Medication therapy', 'Completed', 25, '2024-03-03 16:15:00'),
('VIS018', 'PAT018', 'PRV018', '2024-03-04', '2024-03-04 10:00:00', 'Follow-up', 'Joint pain', 'Rheumatoid arthritis', 'Continue DMARD therapy', 'Completed', 35, '2024-03-04 10:00:00'),
('VIS019', 'PAT019', 'PRV019', '2024-03-05', '2024-03-05 14:30:00', 'Consultation', 'Fever and fatigue', 'Viral syndrome', 'Supportive care, rest', 'Completed', 20, '2024-03-05 14:30:00'),
('VIS020', 'PAT020', 'PRV020', '2024-03-06', '2024-03-06 11:45:00', 'Annual Physical', 'Routine health maintenance', 'Healthy', 'Continue current lifestyle', 'Completed', 45, '2024-03-06 11:45:00'),
('VIS021', 'PAT001', 'PRV002', '2024-03-15', '2024-03-15 10:00:00', 'Follow-up', 'Blood pressure check', 'Controlled hypertension', 'Continue medication', 'Completed', 15, '2024-03-15 10:00:00'),
('VIS022', 'PAT003', 'PRV001', '2024-03-20', '2024-03-20 14:30:00', 'Cardiac Follow-up', 'Post-MI care', 'Recovering well', 'Cardiac rehabilitation', 'Completed', 30, '2024-03-20 14:30:00');

-- Continue with remaining tables (LabResults, Prescriptions, Billing)...
-- [Tables 5-7 follow the same pattern with foreign key references to the current catalog]

-- =============================================
-- TABLE 5: LAB RESULTS
-- Laboratory test results linked to visits
-- =============================================
DROP TABLE IF EXISTS LabResults;

CREATE TABLE LabResults (
    LabResultID STRING NOT NULL,
    VisitID STRING NOT NULL,
    PatientID STRING NOT NULL,
    TestName STRING NOT NULL,
    TestCode STRING,
    ResultValue STRING NOT NULL,
    ReferenceRange STRING,
    Units STRING,
    AbnormalFlag STRING,
    TestDate DATE NOT NULL,
    ResultDate DATE NOT NULL,
    LabTechnician STRING,
    Status STRING DEFAULT 'Final',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_lab_results PRIMARY KEY (LabResultID),
    CONSTRAINT fk_lab_results_visit FOREIGN KEY (VisitID) REFERENCES Visits(VisitID),
    CONSTRAINT fk_lab_results_patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Laboratory test results and diagnostic data';

-- Insert synthetic lab results data
INSERT INTO LabResults VALUES
('LAB001', 'VIS001', 'PAT001', 'Total Cholesterol', 'CHOL', '220', '150-200', 'mg/dL', 'High', '2024-02-15', '2024-02-16', 'Tech001', 'Final', '2024-02-16 08:00:00'),
('LAB002', 'VIS001', 'PAT001', 'HDL Cholesterol', 'HDL', '45', '>40', 'mg/dL', 'Normal', '2024-02-15', '2024-02-16', 'Tech001', 'Final', '2024-02-16 08:00:00'),
('LAB003', 'VIS001', 'PAT001', 'LDL Cholesterol', 'LDL', '145', '<100', 'mg/dL', 'High', '2024-02-15', '2024-02-16', 'Tech001', 'Final', '2024-02-16 08:00:00'),
('LAB004', 'VIS002', 'PAT002', 'Hemoglobin A1c', 'HBA1C', '8.2', '4.0-6.0', '%', 'High', '2024-02-16', '2024-02-17', 'Tech002', 'Final', '2024-02-17 09:00:00'),
('LAB005', 'VIS002', 'PAT002', 'Fasting Glucose', 'GLUC', '180', '70-99', 'mg/dL', 'High', '2024-02-16', '2024-02-17', 'Tech002', 'Final', '2024-02-17 09:00:00'),
('LAB006', 'VIS003', 'PAT003', 'Troponin I', 'TROP', '12.5', '<0.04', 'ng/mL', 'High', '2024-02-17', '2024-02-17', 'Tech003', 'Final', '2024-02-17 16:00:00'),
('LAB007', 'VIS003', 'PAT003', 'CK-MB', 'CKMB', '45', '0-6.3', 'ng/mL', 'High', '2024-02-17', '2024-02-17', 'Tech003', 'Final', '2024-02-17 16:00:00'),
('LAB008', 'VIS005', 'PAT005', 'C-Reactive Protein', 'CRP', '8.5', '<3.0', 'mg/L', 'High', '2024-02-19', '2024-02-20', 'Tech004', 'Final', '2024-02-20 10:00:00'),
('LAB009', 'VIS005', 'PAT005', 'ESR', 'ESR', '65', '0-22', 'mm/hr', 'High', '2024-02-19', '2024-02-20', 'Tech004', 'Final', '2024-02-20 10:00:00'),
('LAB010', 'VIS008', 'PAT008', 'CA 15-3', 'CA153', '18', '<31.3', 'U/mL', 'Normal', '2024-02-22', '2024-02-23', 'Tech005', 'Final', '2024-02-23 11:00:00');

-- =============================================
-- TABLE 6: PRESCRIPTIONS
-- Medication prescriptions linked to visits
-- =============================================
DROP TABLE IF EXISTS Prescriptions;

CREATE TABLE Prescriptions (
    PrescriptionID STRING NOT NULL,
    VisitID STRING NOT NULL,
    PatientID STRING NOT NULL,
    ProviderID STRING NOT NULL,
    MedicationName STRING NOT NULL,
    GenericName STRING,
    Dosage STRING NOT NULL,
    Frequency STRING NOT NULL,
    Quantity INT NOT NULL,
    Refills INT DEFAULT 0,
    PrescriptionDate DATE NOT NULL,
    Instructions STRING,
    Status STRING DEFAULT 'Active',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_prescriptions PRIMARY KEY (PrescriptionID),
    CONSTRAINT fk_prescriptions_visit FOREIGN KEY (VisitID) REFERENCES Visits(VisitID),
    CONSTRAINT fk_prescriptions_patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    CONSTRAINT fk_prescriptions_provider FOREIGN KEY (ProviderID) REFERENCES Providers(ProviderID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Medication prescriptions and pharmaceutical orders';

-- Insert synthetic prescriptions data
INSERT INTO Prescriptions VALUES
('RX001', 'VIS001', 'PAT001', 'PRV001', 'Lisinopril', 'Lisinopril', '10mg', 'Once daily', 30, 3, '2024-02-15', 'Take with or without food', 'Active', '2024-02-15 09:30:00'),
('RX002', 'VIS001', 'PAT001', 'PRV001', 'Atorvastatin', 'Atorvastatin', '20mg', 'Once daily at bedtime', 30, 3, '2024-02-15', 'Take at bedtime', 'Active', '2024-02-15 09:30:00'),
('RX003', 'VIS002', 'PAT002', 'PRV002', 'Metformin', 'Metformin', '500mg', 'Twice daily', 60, 5, '2024-02-16', 'Take with meals', 'Active', '2024-02-16 10:45:00'),
('RX004', 'VIS002', 'PAT002', 'PRV002', 'Insulin Glargine', 'Insulin Glargine', '20 units', 'Once daily at bedtime', 1, 2, '2024-02-16', 'Inject subcutaneously', 'Active', '2024-02-16 10:45:00'),
('RX005', 'VIS003', 'PAT003', 'PRV003', 'Aspirin', 'Aspirin', '81mg', 'Once daily', 30, 3, '2024-02-17', 'Take with food', 'Active', '2024-02-17 15:00:00');

-- =============================================
-- TABLE 7: BILLING
-- Billing information for visits and services
-- =============================================
DROP TABLE IF EXISTS Billing;

CREATE TABLE Billing (
    BillID STRING NOT NULL,
    PatientID STRING NOT NULL,
    VisitID STRING NOT NULL,
    ServiceDate DATE NOT NULL,
    ServiceCode STRING NOT NULL,
    ServiceDescription STRING NOT NULL,
    ChargeAmount DECIMAL(10,2) NOT NULL,
    InsurancePaid DECIMAL(10,2) DEFAULT 0.00,
    PatientPaid DECIMAL(10,2) DEFAULT 0.00,
    BalanceDue DECIMAL(10,2) NOT NULL,
    BillingStatus STRING DEFAULT 'Pending',
    BillingDate DATE NOT NULL,
    PaymentDueDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_billing PRIMARY KEY (BillID),
    CONSTRAINT fk_billing_patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    CONSTRAINT fk_billing_visit FOREIGN KEY (VisitID) REFERENCES Visits(VisitID)
) USING DELTA
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
COMMENT 'Billing information, charges, and payment tracking';

-- Insert synthetic billing data
INSERT INTO Billing VALUES
('BILL001', 'PAT001', 'VIS001', '2024-02-15', '99213', 'Office visit, established patient, level 3', 250.00, 200.00, 25.00, 25.00, 'Partial Payment', '2024-02-16', '2024-03-16', '2024-02-16 10:00:00'),
('BILL002', 'PAT002', 'VIS002', '2024-02-16', '99214', 'Office visit, established patient, level 4', 350.00, 280.00, 30.00, 40.00, 'Partial Payment', '2024-02-17', '2024-03-17', '2024-02-17 11:00:00'),
('BILL003', 'PAT003', 'VIS003', '2024-02-17', '99281', 'Emergency department visit, level 1', 1500.00, 1200.00, 0.00, 300.00, 'Pending', '2024-02-18', '2024-03-18', '2024-02-18 12:00:00'),
('BILL004', 'PAT004', 'VIS004', '2024-02-18', '99382', 'Preventive medicine, new patient, 1-4 years', 200.00, 160.00, 15.00, 25.00, 'Partial Payment', '2024-02-19', '2024-03-19', '2024-02-19 13:00:00'),
('BILL005', 'PAT005', 'VIS005', '2024-02-19', '99243', 'Office consultation, level 3', 400.00, 320.00, 35.00, 45.00, 'Partial Payment', '2024-02-20', '2024-03-20', '2024-02-20 14:00:00');

-- =============================================
-- VERIFICATION QUERIES
-- Run these to verify successful deployment
-- =============================================

-- Query 1: Verify all tables exist
SHOW TABLES;

-- Query 2: Check table row counts
SELECT 
  'Patients' as table_name, COUNT(*) as row_count FROM Patients
UNION ALL
SELECT 'Providers', COUNT(*) FROM Providers
UNION ALL
SELECT 'Insurance', COUNT(*) FROM Insurance
UNION ALL  
SELECT 'Visits', COUNT(*) FROM Visits
UNION ALL
SELECT 'LabResults', COUNT(*) FROM LabResults
UNION ALL
SELECT 'Prescriptions', COUNT(*) FROM Prescriptions
UNION ALL
SELECT 'Billing', COUNT(*) FROM Billing
ORDER BY table_name;

-- Query 3: Test joins and relationships
SELECT 
    p.PatientID,
    CONCAT(p.FirstName, ' ', p.LastName) AS PatientName,
    v.VisitDate,
    pr.Specialty,
    v.Diagnosis
FROM Patients p
JOIN Visits v ON p.PatientID = v.PatientID
JOIN Providers pr ON v.ProviderID = pr.ProviderID
ORDER BY v.VisitDate DESC
LIMIT 10;

-- =============================================
-- SUMMARY
-- =============================================
-- Successfully created healthcare database schema with:
-- - 7 tables with proper relationships
-- - 20 patients, 20 providers, 20 insurance records
-- - 22 visits, 10 lab results, 5 prescriptions, 5 billing records
-- - Foreign key constraints for data integrity
-- - Configurable catalog name via ${CATALOG_NAME} variable
-- =============================================