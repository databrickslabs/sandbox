# Databricks notebook source
# MAGIC %md
# MAGIC # redshift_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/redshift/input/redshift_example2_stored_procedure.sql`

# COMMAND ----------

# Create widget for parameter with default value
dbutils.widgets.text("threshold_multiplier", "1.25")

# COMMAND ----------

# Convert parameter
threshold_multiplier = float(dbutils.widgets.get("threshold_multiplier"))

# COMMAND ----------

# Define temporary table name (we'll use Delta table)
temp_table_name = "temp_outlier_thresholds"

# COMMAND ----------

# Track latest timestamp for potential rollback
try:
    hist = spark.sql("DESCRIBE HISTORY sales_forecast LIMIT 1").collect()[0]
    restore_ts = hist["timestamp"]
except:
    restore_ts = None

# COMMAND ----------

try:
    # Create temporary table
    spark.sql(f"""
        CREATE OR REPLACE TABLE {temp_table_name} (
            product_id INT,
            outlier_threshold DECIMAL(10,2)
        )
    """)
    
    # Calculate the outlier thresholds using percentile_cont
    spark.sql(f"""
        INSERT INTO {temp_table_name}
        SELECT 
            product_id,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY forecast_price) OVER (PARTITION BY product_id) AS outlier_threshold
        FROM sales_forecast
        WHERE forecast_date >= date_sub(current_date(), 365)
    """)
    
    # Update the sales_forecast table with capped values
    update_result = spark.sql(f"""
        MERGE INTO sales_forecast f
        USING {temp_table_name} t
        ON f.product_id = t.product_id
        WHEN MATCHED AND f.forecast_price > t.outlier_threshold * {threshold_multiplier} THEN
          UPDATE SET forecast_price = t.outlier_threshold * {threshold_multiplier}
    """)
    
    # Get count of updated rows
    row_count = update_result.count() if hasattr(update_result, 'count') else 0
    print(f"Rows updated: {row_count}")
    print(f"Procedure completed with multiplier {threshold_multiplier}")
    
except Exception as e:
    print(f"Error occurred: {str(e)}")
    
    # Attempt rollback if we have a timestamp
    if restore_ts:
        spark.sql(f"RESTORE TABLE sales_forecast TO TIMESTAMP AS OF '{restore_ts}'")
        print("Rollback via table restore completed.")
    raise e

finally:
    # Clean up temporary table
    spark.sql(f"DROP TABLE IF EXISTS {temp_table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.