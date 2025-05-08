# Databricks notebook source
# MAGIC %md
# MAGIC # netezza_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/netezza/input/netezza_example2_stored_procedure.sql`

# COMMAND ----------

# Create input widgets for parameters
dbutils.widgets.text("TableName", "")
dbutils.widgets.text("Threshold", "100.0")

# COMMAND ----------

# Function to implement the procedure
def demo_adjust_threshold():
    # Get parameter values
    table_name = dbutils.widgets.get("TableName")
    threshold = float(dbutils.widgets.get("Threshold"))
    
    # Validate table name
    if not table_name:
        print("ERROR: Table name cannot be empty")
        return -1
    
    # Get current version info for rollback if needed
    try:
        hist = spark.sql(f"DESCRIBE HISTORY {table_name} LIMIT 1").collect()[0]
        restore_ts = hist["timestamp"]
    except Exception as e:
        print(f"Warning: Could not get history for {table_name}. Rollback may not be possible.")
        restore_ts = None
    
    # Execute the update with transaction simulation
    try:
        print(f"Starting threshold adjustment in table: {table_name} with threshold: {threshold}")
        
        # Update query
        spark.sql(f"""
        UPDATE {table_name} 
        SET METRICVALUE = {threshold} 
        WHERE METRICVALUE > {threshold}
        """)
        
        # Count affected rows
        result_df = spark.sql(f"""
        SELECT COUNT(*) AS count 
        FROM {table_name} 
        WHERE METRICVALUE = {threshold}
        """)
        
        count = result_df.collect()[0]["count"]
        print(f"Number of rows updated to threshold: {count}")
        
        return count
        
    except Exception as e:
        print(f"Error in procedure DEMO_ADJUST_THRESHOLD: {str(e)}")
        
        # Rollback if possible
        if restore_ts:
            print(f"Attempting to restore {table_name} to previous version")
            spark.sql(f"RESTORE TABLE {table_name} TO TIMESTAMP AS OF '{restore_ts}'")
        
        raise e

# COMMAND ----------

# Execute procedure
result = demo_adjust_threshold()
print(f"Result: {result}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.