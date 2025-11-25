-- Create Demo Catalog and Schema
CREATE CATALOG IF NOT EXISTS enterprise_gov;
USE CATALOG enterprise_gov;

CREATE SCHEMA IF NOT EXISTS gov_admin;
USE SCHEMA gov_admin;

-- Crete Agent tool UC UDFs


CREATE OR REPLACE FUNCTION enterprise_gov.gov_admin.list_row_filter_column_masking(catalog_name STRING, schema_name STRING)
RETURNS TABLE (routine_catalog STRING, routine_schema STRING, routine_name STRING, comment STRING, full_data_type STRING, routine_definition STRING)
RETURN (
select routine_catalog, routine_schema, routine_name, comment, full_data_type, routine_definition
FROM system.information_schema.routines
WHERE routine_catalog = catalog_name
and routine_schema = schema_name
and routine_type = 'FUNCTION'
);


CREATE OR REPLACE FUNCTION enterprise_gov.gov_admin.describe_extended_table(catalog_name STRING, schema_name STRING, table_name STRING)
RETURNS TABLE (table_catalog STRING, table_schema STRING, table_name STRING, column_name STRING, data_type STRING, comment STRING)
RETURN (
  SELECT table_catalog,table_schema, table_name, column_name, data_type, comment
  FROM system.information_schema.columns
  WHERE table_catalog = catalog_name
    AND table_schema = schema_name
    AND table_name = table_name
);


CREATE OR REPLACE FUNCTION enterprise_gov.gov_admin.list_uc_tables(catalog_name STRING, schema_name STRING)
RETURNS TABLE (table_name STRING, table_type STRING, created TIMESTAMP)
RETURN (
  SELECT table_name, table_type, created
  FROM system.information_schema.tables
  WHERE table_catalog = catalog_name AND table_schema = schema_name
);


CREATE OR REPLACE FUNCTION enterprise_gov.gov_admin.get_table_tags(catalog_name STRING, schema_name STRING, table_name STRING)
RETURNS TABLE (table_name STRING, tag_name STRING, tag_value STRING)
RETURN (
  SELECT table_name, tag_name, tag_value
  FROM system.information_schema.table_tags
  WHERE catalog_name = catalog_name AND schema_name = schema_name AND table_name = table_name
);


CREATE OR REPLACE FUNCTION enterprise_gov.gov_admin.get_column_tags(catalog_name STRING, schema_name STRING, table_name STRING)
RETURNS TABLE (table_name STRING, column_name STRING, tag_name STRING, tag_value STRING)
RETURN (
  SELECT table_name, column_name, tag_name, tag_value
  FROM system.information_schema.column_tags
  WHERE catalog_name = catalog_name AND schema_name = schema_name AND table_name = table_name
);



