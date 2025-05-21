# Databricks notebook source
# MAGIC %md
# MAGIC # snowflake_example2_javascript_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/snowflake/input/snowflake_example2_javascript_procedure.sql`

# COMMAND ----------

# Define widgets to accept parameters
dbutils.widgets.text("SCHEMA_NAME", "")
dbutils.widgets.text("OUTLIER_MULTIPLIER", "1.30")

# COMMAND ----------

# Get widget values
schema_name = dbutils.widgets.get("SCHEMA_NAME")
outlier_multiplier = float(dbutils.widgets.get("OUTLIER_MULTIPLIER"))

# COMMAND ----------

# For Delta table rollback if needed
try:
    hist_forecast = spark.sql(f"DESCRIBE HISTORY `{schema_name}`.ForecastTable LIMIT 1").collect()[0]
    forecast_restore_ts = hist_forecast["timestamp"]
except:
    forecast_restore_ts = None

# COMMAND ----------

# Main procedure logic
try:
    # 1) Retrieve current date from SystemDateTable
    date_df = spark.sql(f"SELECT SystemDate FROM `{schema_name}`.SystemDateTable")
    if date_df.count() == 0:
        raise ValueError("Failed to retrieve system date")
    
    current_date = date_df.collect()[0]["SystemDate"]
    
    # 2 & 3) Calculate outlier thresholds using window functions
    # Instead of creating a temp table, we'll create a temporary view
    spark.sql(f"""
    CREATE OR REPLACE TEMPORARY VIEW TEMP_OUTLIER_INFO AS
    SELECT 
        d.LocationId,
        percentile_cont(0.99) WITHIN GROUP (ORDER BY d.MetricValue) 
        OVER (PARTITION BY d.LocationId) AS OutlierThreshold
    FROM `{schema_name}`.HistoricalDataTable d
    WHERE TO_DATE(d.TargetDate) >= DATE_SUB(TO_DATE('{current_date}'), 365)
    """)
    
    # 4) Save original forecast values above threshold
    spark.sql(f"""
    UPDATE `{schema_name}`.ForecastTable f
    SET OriginalForecastValue = ForecastValue
    WHERE EXISTS (
        SELECT 1 
        FROM TEMP_OUTLIER_INFO t 
        WHERE f.LocationId = t.LocationId 
        AND TO_DATE(f.ForecastDate) = TO_DATE('{current_date}')
        AND f.ForecastValue > t.OutlierThreshold * {outlier_multiplier}
    )
    """)
    
    # 5) Update outlier values to cap them at threshold * multiplier
    spark.sql(f"""
    MERGE INTO `{schema_name}`.ForecastTable f
    USING TEMP_OUTLIER_INFO t
    ON f.LocationId = t.LocationId 
       AND TO_DATE(f.ForecastDate) = TO_DATE('{current_date}')
       AND f.ForecastValue > t.OutlierThreshold * {outlier_multiplier}
    WHEN MATCHED THEN
      UPDATE SET f.ForecastValue = t.OutlierThreshold * {outlier_multiplier}
    """)
    
    # Success
    result = "0"
    
except Exception as e:
    # Error handling - restore forecast table if we have a timestamp
    if forecast_restore_ts is not None:
        spark.sql(f"RESTORE TABLE `{schema_name}`.ForecastTable TO TIMESTAMP AS OF '{forecast_restore_ts}'")
    
    # Log error (simplified)
    error_msg = str(e).replace("'", "''")
    try:
        spark.sql(f"CALL LogError('DEMO_FORECAST_OUTLIER_CHECK_UPDATE', '{error_msg}')")
    except:
        # Silently handle logging errors
        pass
    
    # Re-raise the error
    result = "2"
    raise Exception(f"Error in procedure: {error_msg}")

# COMMAND ----------

# Clean up the temporary view
spark.sql("DROP VIEW IF EXISTS TEMP_OUTLIER_INFO")

# COMMAND ----------

# Return the result
print(f"Result: {result}")
dbutils.notebook.exit(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.