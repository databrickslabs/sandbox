# Databricks notebook source
# MAGIC %md
# MAGIC # mysql_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/mysql/input/mysql_example2_stored_procedure.sql`

# COMMAND ----------

# Create widgets for procedure input parameters
dbutils.widgets.text("table_name", "")
dbutils.widgets.text("threshold", "")

# COMMAND ----------

# Function to perform the threshold check and update
def demo_threshold_check():
    # Get parameters from widgets
    table_name = dbutils.widgets.get("table_name")
    
    try:
        threshold = float(dbutils.widgets.get("threshold"))
    except ValueError:
        print("Invalid threshold value")
        return -1
        
    if not table_name:
        print("Table name must be provided")
        return -1
    
    # For rollback simulation with Delta tables
    try:
        hist = spark.sql(f"DESCRIBE HISTORY {table_name} LIMIT 1").collect()[0]
        restore_timestamp = hist["timestamp"]
    except Exception as e:
        print(f"Warning: Could not get history for table {table_name}: {str(e)}")
        restore_timestamp = None
    
    rows_updated = -1
    
    try:
        # Create Delta table instead of temporary table
        spark.sql(f"""
            CREATE OR REPLACE TABLE TempData AS
            SELECT id, metric
            FROM {table_name}
            WHERE metric > {threshold}
        """)
        
        # Update the table with the threshold
        update_result = spark.sql(f"""
            UPDATE {table_name}
            SET metric = {threshold}
            WHERE metric > {threshold}
        """)
        
        # Get row count from the temp table
        rows_updated = spark.sql("SELECT COUNT(*) AS cnt FROM TempData").collect()[0]['cnt']
        
        # Clean up
        spark.sql("DROP TABLE IF EXISTS TempData")
        
        return rows_updated
        
    except Exception as e:
        # Simulate ROLLBACK
        if restore_timestamp:
            spark.sql(f"RESTORE TABLE {table_name} TO TIMESTAMP AS OF '{restore_timestamp}'")
            print(f"Error occurred: {str(e)}. Table restored to previous version.")
        else:
            print(f"Error occurred: {str(e)}. Could not restore table.")
        
        return -1

# COMMAND ----------

# Execute the function and display result
rows_updated = demo_threshold_check()
print(f"Rows updated: {rows_updated}")

# COMMAND ----------

# You can create an output DataFrame if you prefer to display the result that way
result_df = spark.createDataFrame([(rows_updated,)], ["rows_updated"])
display(result_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.