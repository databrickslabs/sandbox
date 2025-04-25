# Databricks notebook source
# MAGIC %md
# MAGIC # oracle_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/oracle/input/oracle_example2_stored_procedure.sql`

# COMMAND ----------

# Create a widget for the parameter with default value
dbutils.widgets.text("multiplier", "1.20", "Forecast Adjustment Multiplier")

# COMMAND ----------

# Get the parameter value
p_multiplier = float(dbutils.widgets.get("multiplier"))

# COMMAND ----------

# Create a table to hold threshold values (instead of a temp table)
spark.sql("""
CREATE OR REPLACE TABLE TempOutlierThreshold (
    LocationId STRING,
    ThresholdValue DECIMAL(10, 2)
)
""")

# COMMAND ----------

try:
    # Populate the threshold table
    spark.sql(f"""
    INSERT INTO TempOutlierThreshold (LocationId, ThresholdValue)
    SELECT LocationId, 1000 * {p_multiplier} 
    FROM SalesHistory
    WHERE SalesDate > add_months(current_date(), -12)
    """)
    
    # Create a view for forecasts that need updating
    spark.sql(f"""
    CREATE OR REPLACE TEMPORARY VIEW ForecastsToUpdate AS
    SELECT f.*
    FROM ForecastTable f
    JOIN TempOutlierThreshold t ON t.LocationId = f.LocationId
    WHERE f.ForecastValue > t.ThresholdValue * {p_multiplier}
    AND date_trunc('day', f.ForecastDate) = date_trunc('day', current_date())
    """)
    
    # First update - Save original forecast values
    spark.sql("""
    MERGE INTO ForecastTable target
    USING ForecastsToUpdate source
    ON target.LocationId = source.LocationId AND target.ForecastDate = source.ForecastDate
    WHEN MATCHED THEN UPDATE SET target.OriginalForecast = source.ForecastValue
    """)
    
    # Create a view with calculated thresholds
    spark.sql(f"""
    CREATE OR REPLACE TEMPORARY VIEW ForecastWithThresholds AS
    SELECT 
        f.*,
        t.ThresholdValue * {p_multiplier} as CalculatedThreshold
    FROM ForecastTable f
    JOIN TempOutlierThreshold t ON t.LocationId = f.LocationId
    WHERE f.ForecastValue > t.ThresholdValue * {p_multiplier}
    AND date_trunc('day', f.ForecastDate) = date_trunc('day', current_date())
    """)
    
    # Second update - Cap forecast values to threshold
    spark.sql("""
    MERGE INTO ForecastTable target
    USING ForecastWithThresholds source
    ON target.LocationId = source.LocationId AND target.ForecastDate = source.ForecastDate
    WHEN MATCHED THEN UPDATE SET target.ForecastValue = source.CalculatedThreshold
    """)
    
except Exception as e:
    print(f"Error in procedure AdjustSalesForecast: {str(e)}")
    raise e
finally:
    # Clean up temporary objects
    spark.sql("DROP TABLE IF EXISTS TempOutlierThreshold")
    spark.sql("DROP VIEW IF EXISTS ForecastsToUpdate")
    spark.sql("DROP VIEW IF EXISTS ForecastWithThresholds")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.