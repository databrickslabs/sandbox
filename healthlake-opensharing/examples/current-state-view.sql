-- Current state of one FHIR resource type, as the FHIR API sees it.
--
-- HealthLake's analytics tables only append. A FHIR delete adds a row that has
-- only id and meta.lastUpdated set, and the resource's earlier row stays. Keep
-- the newest row per id and drop it if that row is the delete marker.
--
-- Shared catalogs are read-only, so create the view in a catalog you own.
-- Verified against the FHIR API on the test data store: 51 rows, 49 patients.

CREATE OR REPLACE VIEW <your_catalog>.<your_schema>.patient_current AS
SELECT *
FROM healthlake_<data_store>.fhir.patient
QUALIFY row_number() OVER (PARTITION BY id ORDER BY CAST(meta.lastUpdated AS TIMESTAMP) DESC) = 1
    AND meta.versionId IS NOT NULL;
