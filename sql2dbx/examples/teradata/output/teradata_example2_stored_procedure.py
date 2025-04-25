# Databricks notebook source
# MAGIC %md
# MAGIC # teradata_example2_stored_procedure
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/teradata/input/teradata_example2_stored_procedure.sql`

# COMMAND ----------

# Setup widgets for parameters
dbutils.widgets.text("pLocationId", "")
dbutils.widgets.text("pThreshold", "")
dbutils.widgets.text("pResultCode", "0")  # Output parameter initialized to 0

# COMMAND ----------

# Get input parameter values
location_id = dbutils.widgets.get("pLocationId")
threshold = float(dbutils.widgets.get("pThreshold"))
result_code = 0  # Initialize result code

# COMMAND ----------

# Get current table state for potential rollback
try:
    hist = spark.sql("DESCRIBE HISTORY Inventory LIMIT 1").collect()[0]
    restore_ts = hist["timestamp"]
except:
    restore_ts = None

# COMMAND ----------

# Main procedure logic with error handling
try:
    # Create temporary table (equivalent to VOLATILE TABLE)
    spark.sql("""
    CREATE OR REPLACE TABLE VolatileHighStock (
        ItemId INT,
        LocationId STRING,
        StockLevel DECIMAL(8,2)
    )
    """)
    
    # Insert high stock items into temporary table
    spark.sql(f"""
    INSERT INTO VolatileHighStock (ItemId, LocationId, StockLevel)
    SELECT 
        i.ItemId, 
        i.LocationId, 
        i.StockLevel
    FROM Inventory i
    WHERE 
        i.LocationId = '{location_id}' AND 
        i.StockLevel > {threshold}
    """)
    
    # Update inventory levels to threshold
    # Note: Databricks doesn't support UPDATE with FROM clause directly, using MERGE instead
    spark.sql(f"""
    MERGE INTO Inventory inv
    USING VolatileHighStock v
    ON inv.ItemId = v.ItemId AND inv.LocationId = v.LocationId
    WHEN MATCHED THEN
        UPDATE SET inv.StockLevel = {threshold}
    """)
    
    # Set successful result code
    result_code = 0
    
except Exception as e:
    # Error handling - set error code and rollback
    result_code = 2
    
    # Attempt to restore table to prior state
    if restore_ts is not None:
        spark.sql(f"RESTORE TABLE Inventory TO TIMESTAMP AS OF '{restore_ts}'")
    
    print(f"Error executing procedure: {str(e)}")
    
finally:
    # Always clean up temporary table
    spark.sql("DROP TABLE IF EXISTS VolatileHighStock")
    
    # Set output parameter
    dbutils.widgets.remove("pResultCode")
    dbutils.widgets.text("pResultCode", str(result_code))

# COMMAND ----------

# Return result code for notebook
dbutils.notebook.exit(str(result_code))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.