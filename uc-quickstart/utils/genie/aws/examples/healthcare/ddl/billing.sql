CREATE TABLE Billing (
  BillingID       BIGINT        COMMENT 'Unique billing identifier',
  PatientID       BIGINT        COMMENT 'FK to Patients',
  EncounterID     BIGINT        COMMENT 'FK to Encounters',
  TotalAmount     DECIMAL(18,2) COMMENT 'Total billed amount',
  InsurancePaid   DECIMAL(18,2) COMMENT 'Amount covered by insurance',
  PatientOwed     DECIMAL(18,2) COMMENT 'Patient responsibility',
  BillingCode     STRING        COMMENT 'CPT/HCPCS billing code',
  InsuranceID     STRING        COMMENT 'Insurance policy used'
);
