# Databricks notebook source
# MAGIC %md
# MAGIC # snowflake_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/snowflake/input/snowflake_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Set timezone 
# Note: In Databricks, timezone is configured differently than Snowflake
spark.sql("SET spark.sql.session.timeZone=America/Los_Angeles")

# COMMAND ----------

# Create CUSTOMERS table 
spark.sql("""
CREATE TABLE IF NOT EXISTS CUSTOMERS (
  CUSTOMER_ID INT,
  FULL_NAME STRING,
  STATUS STRING,
  CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
""")

# COMMAND ----------

# Insert data into CUSTOMERS table
spark.sql("""
INSERT INTO CUSTOMERS (CUSTOMER_ID, FULL_NAME, STATUS)
VALUES 
  (1, 'Alice Smith', 'ACTIVE'),
  (2, 'Bob Jones', 'INACTIVE'),
  (3, 'Charlie Brown', 'ACTIVE')
""")

# COMMAND ----------

# Create a table for addresses (we don't use temporary tables in Databricks the same way)
spark.sql("""
CREATE OR REPLACE TABLE TEMP_ADDRESSES (
  ADDRESS_ID INT,
  CUSTOMER_ID INT,
  ADDRESS_LINE STRING
)
""")

# COMMAND ----------

# Insert data into TEMP_ADDRESSES
spark.sql("""
INSERT INTO TEMP_ADDRESSES (ADDRESS_ID, CUSTOMER_ID, ADDRESS_LINE)
VALUES
  (100, 1, '123 Maple Street'),
  (101, 2, '456 Oak Avenue'),
  (102, 3, '789 Pine Road')
""")

# COMMAND ----------

# Update CUSTOMERS - Databricks doesn't support UPDATE FROM syntax
# Instead, we'll use MERGE INTO
spark.sql("""
MERGE INTO CUSTOMERS c
USING (
  SELECT CUSTOMER_ID 
  FROM TEMP_ADDRESSES 
  WHERE ADDRESS_LINE LIKE '%Pine%'
) a
ON c.CUSTOMER_ID = a.CUSTOMER_ID
WHEN MATCHED THEN UPDATE SET STATUS = 'PENDING'
""")

# COMMAND ----------

# Delete from TEMP_ADDRESSES - Databricks doesn't support DELETE USING syntax
# We'll identify records to keep and rewrite the table
spark.sql("""
CREATE OR REPLACE TABLE TEMP_ADDRESSES AS
SELECT t.*
FROM TEMP_ADDRESSES t
LEFT JOIN CUSTOMERS c ON t.CUSTOMER_ID = c.CUSTOMER_ID AND c.STATUS = 'INACTIVE'
WHERE c.CUSTOMER_ID IS NULL
""")

# COMMAND ----------

# Select all data from CUSTOMERS
display(spark.sql("SELECT * FROM CUSTOMERS"))

# COMMAND ----------

# Select all data from TEMP_ADDRESSES
display(spark.sql("SELECT * FROM TEMP_ADDRESSES"))

# COMMAND ----------

# Drop CUSTOMERS table
spark.sql("DROP TABLE IF EXISTS CUSTOMERS")

# COMMAND ----------

# Also drop the TEMP_ADDRESSES table since it was meant to be temporary
spark.sql("DROP TABLE IF EXISTS TEMP_ADDRESSES")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.