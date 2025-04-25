# Databricks notebook source
# MAGIC %md
# MAGIC # mysql_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/mysql/input/mysql_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create the Orders table
spark.sql("""
CREATE TABLE Orders (
    OrderID INT, 
    CustomerName STRING, 
    OrderDate TIMESTAMP DEFAULT current_timestamp(), 
    OrderTotal DECIMAL(10,2)
)
""")

# COMMAND ----------

# Insert data into Orders table
spark.sql("""
INSERT INTO Orders (OrderID, CustomerName, OrderTotal)
VALUES 
    (101, 'Alice', 200.00),
    (102, 'Bob', 350.75),
    (103, 'Charlie', 99.99)
""")

# COMMAND ----------

# Create "temporary" table as Delta table
spark.sql("""
CREATE OR REPLACE TABLE TempOrderStatus (
    OrderID INT,
    Status STRING
)
""")

# COMMAND ----------

# Insert data into temporary status table
spark.sql("""
INSERT INTO TempOrderStatus (OrderID, Status)
VALUES 
    (101, 'PROCESSING'),
    (102, 'SHIPPED'),
    (104, 'CANCELLED')
""")

# COMMAND ----------

# Update Orders using MERGE pattern since Databricks doesn't support JOIN in UPDATE
spark.sql("""
MERGE INTO Orders o
USING (SELECT * FROM TempOrderStatus WHERE Status = 'SHIPPED') t
ON o.OrderID = t.OrderID
WHEN MATCHED THEN
  UPDATE SET o.OrderTotal = o.OrderTotal * 0.90
""")

# COMMAND ----------

# Delete old orders not in the status table
spark.sql("""
DELETE FROM Orders 
WHERE OrderDate < date_sub(current_timestamp(), 90) 
AND OrderID NOT IN (SELECT OrderID FROM TempOrderStatus)
""")

# COMMAND ----------

# Query the results
orders_df = spark.sql("SELECT * FROM Orders")
display(orders_df)

# COMMAND ----------

# Clean up tables
spark.sql("DROP TABLE IF EXISTS Orders")
spark.sql("DROP TABLE IF EXISTS TempOrderStatus")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.