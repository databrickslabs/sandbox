# Databricks notebook source
# MAGIC %md
# MAGIC # postgresql_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/postgresql/input/postgresql_example2_stored_procedure.sql`

# COMMAND ----------

# Create widgets for the procedure parameters
dbutils.widgets.text("_schema_name", "")
dbutils.widgets.text("_outlier_multiplier", "1.30")

# COMMAND ----------

# Get parameter values
schema_name = dbutils.widgets.get("_schema_name")
outlier_multiplier = float(dbutils.widgets.get("_outlier_multiplier"))

# COMMAND ----------

# Create temporary Delta table for outlier info
spark.sql("""
CREATE OR REPLACE TABLE temp_outlier_info (
    location_id STRING,
    outlier_threshold DECIMAL(8,2)
)
""")

# COMMAND ----------

# Try-except block for transaction-like behavior
try:
    # Get current date from system date table
    current_date_df = spark.sql(f"SELECT system_date FROM {schema_name}.system_date_table LIMIT 1")
    
    if current_date_df.count() == 0:
        print("No valid date found in system_date_table; exiting.")
        dbutils.notebook.exit("No valid date found")
    
    current_date = current_date_df.collect()[0][0]
    
    # Calculate outlier thresholds and insert into temp table
    spark.sql(f"""
    INSERT INTO temp_outlier_info (location_id, outlier_threshold)
    SELECT 
        d.location_id, 
        percentile(d.metric_value, 0.99) as outlier_threshold
    FROM {schema_name}.historical_data_table d
    WHERE CAST(d.target_date AS DATE) >= date_sub('{current_date}', 365)
    GROUP BY d.location_id
    """)
    
    # Update forecast table: first backup original values
    # Using MERGE instead of UPDATE FROM since Databricks doesn't support UPDATE FROM
    spark.sql(f"""
    MERGE INTO {schema_name}.forecast_table f
    USING temp_outlier_info t
    ON f.location_id = t.location_id 
       AND CAST(f.forecast_date AS DATE) = '{current_date}'
       AND f.forecast_value > t.outlier_threshold * {outlier_multiplier}
    WHEN MATCHED THEN
      UPDATE SET original_forecast_value = f.forecast_value
    """)
    
    # Update forecast table: cap values at threshold
    spark.sql(f"""
    MERGE INTO {schema_name}.forecast_table f
    USING temp_outlier_info t
    ON f.location_id = t.location_id 
       AND CAST(f.forecast_date AS DATE) = '{current_date}'
       AND f.forecast_value > t.outlier_threshold * {outlier_multiplier}
    WHEN MATCHED THEN
      UPDATE SET forecast_value = t.outlier_threshold * {outlier_multiplier}
    """)
    
except Exception as e:
    print(f"Error occurred: {str(e)}")
    # In a real Delta Lake scenario, you might want to restore the table to a previous version
    # spark.sql(f"RESTORE TABLE {schema_name}.forecast_table TO VERSION AS OF <timestamp>")
    raise e
    
finally:
    # Drop the temporary table
    spark.sql("DROP TABLE IF EXISTS temp_outlier_info")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.