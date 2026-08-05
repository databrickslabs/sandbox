CREATE TABLE Encounters (
  EncounterID     BIGINT        COMMENT 'Unique encounter identifier',
  PatientID       BIGINT        COMMENT 'FK to Patients',
  EncounterDate   TIMESTAMP     COMMENT 'Date/time of encounter',
  EncounterType   STRING        COMMENT 'INPATIENT, OUTPATIENT, EMERGENCY',
  DiagnosisCode   STRING        COMMENT 'ICD-10 diagnosis code',
  DiagnosisDesc   STRING        COMMENT 'Full diagnosis description',
  TreatmentNotes  STRING        COMMENT 'Free-text clinical notes',
  AttendingDoc    STRING        COMMENT 'Attending physician name',
  FacilityRegion  STRING        COMMENT 'Hospital region: US_EAST, US_WEST, EU'
);
