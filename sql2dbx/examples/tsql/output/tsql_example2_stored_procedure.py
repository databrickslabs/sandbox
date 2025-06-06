# Databricks notebook source
# MAGIC %md
# MAGIC # tsql_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/tsql/input/tsql_example2_stored_procedure.sql`

# COMMAND ----------

# Create widgets for input parameters
dbutils.widgets.text("SchemaName", "")
dbutils.widgets.text("OutlierMultiplier", "1.30")

# COMMAND ----------

# Get parameter values
schema_name = dbutils.widgets.get("SchemaName")
outlier_multiplier = float(dbutils.widgets.get("OutlierMultiplier"))

# COMMAND ----------

# Create a temporary Delta table to replace #TEMP_OUTLIER_INFO
spark.sql("DROP TABLE IF EXISTS TEMP_OUTLIER_INFO")
spark.sql("""
CREATE TABLE TEMP_OUTLIER_INFO (
    LocationId STRING,
    OutlierThreshold DECIMAL(8,2)
)
""")

# COMMAND ----------

# Set up variables
error_proc_name = "DEMO_FORECAST_OUTLIER_CHECK_UPDATE"
result = 0

# COMMAND ----------

# Capture table state for potential rollback
try:
    forecast_hist = spark.sql(f"DESCRIBE HISTORY {schema_name}.ForecastTable LIMIT 1").collect()[0]
    forecast_restore_ts = forecast_hist["timestamp"]
except:
    forecast_restore_ts = None

# COMMAND ----------

try:
    # Get current date from system table
    current_date_df = spark.sql(f"SELECT SystemDate FROM {schema_name}.SystemDateTable")
    current_date = current_date_df.first()["SystemDate"]
    
    # Calculate outlier thresholds and insert into temporary table
    # Note: Using percentile instead of PERCENTILE_CONT with WITHIN GROUP
    spark.sql(f"""
    INSERT INTO TEMP_OUTLIER_INFO (LocationId, OutlierThreshold)
    SELECT 
        d.LocationId,
        CAST(percentile(d.MetricValue, 0.99) AS DECIMAL(8,2)) AS OutlierThreshold
    FROM {schema_name}.HistoricalDataTable d
    WHERE CAST(d.TargetDate AS DATE) >= date_add('{current_date}', -365)
    GROUP BY d.LocationId
    """)
    
    # Update original forecast values
    # Using MERGE instead of UPDATE with JOIN
    spark.sql(f"""
    MERGE INTO {schema_name}.ForecastTable f
    USING (
        SELECT 
            f.LocationId, 
            f.ForecastValue,
            t.OutlierThreshold
        FROM {schema_name}.ForecastTable f
        INNER JOIN TEMP_OUTLIER_INFO t ON f.LocationId = t.LocationId
        WHERE CAST(f.ForecastDate AS DATE) = '{current_date}'
        AND f.ForecastValue > t.OutlierThreshold * {outlier_multiplier}
    ) src
    ON f.LocationId = src.LocationId AND CAST(f.ForecastDate AS DATE) = '{current_date}'
    WHEN MATCHED THEN
      UPDATE SET f.OriginalForecastValue = f.ForecastValue
    """)
    
    # Update forecast values to threshold
    spark.sql(f"""
    MERGE INTO {schema_name}.ForecastTable f
    USING (
        SELECT 
            f.LocationId, 
            t.OutlierThreshold * {outlier_multiplier} AS AdjustedValue
        FROM {schema_name}.ForecastTable f
        INNER JOIN TEMP_OUTLIER_INFO t ON f.LocationId = t.LocationId
        WHERE CAST(f.ForecastDate AS DATE) = '{current_date}'
        AND f.ForecastValue > t.OutlierThreshold * {outlier_multiplier}
    ) src
    ON f.LocationId = src.LocationId AND CAST(f.ForecastDate AS DATE) = '{current_date}'
    WHEN MATCHED THEN
      UPDATE SET f.ForecastValue = src.AdjustedValue
    """)

except Exception as e:
    # Error handling
    result = 2
    error_msg = str(e)
    print(f"Error: {error_msg}")
    
    # Rollback using Delta table restore
    if forecast_restore_ts is not None:
        spark.sql(f"RESTORE TABLE {schema_name}.ForecastTable TO TIMESTAMP AS OF '{forecast_restore_ts}'")
    
    # Log error - assuming LogError exists as another procedure
    try:
        spark.sql(f"""
        CALL dbo.LogError('{error_proc_name}', '{error_msg.replace("'", "''")}')
        """)
    except:
        print(f"Failed to log error. Original error: {error_msg}")
    
    raise e

finally:
    # Clean up temporary table
    spark.sql("DROP TABLE IF EXISTS TEMP_OUTLIER_INFO")

# COMMAND ----------

# Return result code
dbutils.notebook.exit(str(result))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.