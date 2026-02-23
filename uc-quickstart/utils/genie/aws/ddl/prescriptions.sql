CREATE TABLE Prescriptions (
  PrescriptionID  BIGINT        COMMENT 'Unique prescription identifier',
  PatientID       BIGINT        COMMENT 'FK to Patients',
  EncounterID     BIGINT        COMMENT 'FK to Encounters',
  DrugName        STRING        COMMENT 'Medication name',
  Dosage          STRING        COMMENT 'Dosage instructions',
  Quantity        INT           COMMENT 'Number of units prescribed',
  PrescribingDoc  STRING        COMMENT 'Prescribing physician',
  PrescribedDate  DATE          COMMENT 'Date prescribed'
);
