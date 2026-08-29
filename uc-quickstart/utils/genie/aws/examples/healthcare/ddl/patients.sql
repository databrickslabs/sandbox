CREATE TABLE Patients (
  PatientID       BIGINT        COMMENT 'Unique patient identifier',
  MRN             STRING        COMMENT 'Medical Record Number',
  FirstName       STRING        COMMENT 'Patient first name',
  LastName        STRING        COMMENT 'Patient last name',
  DateOfBirth     DATE          COMMENT 'Date of birth',
  SSN             STRING        COMMENT 'Social Security Number',
  Email           STRING        COMMENT 'Contact email',
  Phone           STRING        COMMENT 'Contact phone number',
  Address         STRING        COMMENT 'Home address',
  InsuranceID     STRING        COMMENT 'Insurance policy number',
  PrimaryCareDoc  STRING        COMMENT 'Assigned physician name',
  FacilityRegion  STRING        COMMENT 'Hospital region: US_EAST, US_WEST, EU'
);
