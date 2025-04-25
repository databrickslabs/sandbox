# Databricks notebook source
# MAGIC %md
# MAGIC # oracle_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/oracle/input/oracle_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create Products table
spark.sql("""
CREATE TABLE IF NOT EXISTS Products (
  ProductID INT,
  ProductName STRING,
  Price DECIMAL(10, 2),
  CreatedAt DATE DEFAULT current_date()
)
""")

# COMMAND ----------

# Insert product data
spark.sql("""
INSERT INTO Products (ProductID, ProductName, Price)
VALUES 
  (201, 'Gizmo X', 14.50),
  (202, 'Gizmo Y', 21.99),
  (203, 'Gizmo Z', 38.25)
""")

# COMMAND ----------

# Create a table to replace the global temporary table
spark.sql("""
CREATE OR REPLACE TABLE DiscountInfo (
  ProductID INT,
  DiscountRate DECIMAL(5, 2)
)
""")

# COMMAND ----------

# Insert discount data
spark.sql("""
INSERT INTO DiscountInfo (ProductID, DiscountRate)
VALUES
  (201, 0.15),
  (203, 0.30)
""")

# COMMAND ----------

# Update product prices based on discount rates
# Using MERGE since Databricks may not support subquery in SET clause
spark.sql("""
MERGE INTO Products p
USING (
  SELECT p.ProductID, p.Price * (1 - d.DiscountRate) AS NewPrice
  FROM Products p
  JOIN DiscountInfo d ON p.ProductID = d.ProductID
) src
ON p.ProductID = src.ProductID
WHEN MATCHED THEN UPDATE SET p.Price = src.NewPrice
""")

# COMMAND ----------

# Delete old products that don't have discounts
spark.sql("""
DELETE FROM Products
WHERE CreatedAt < date_sub(current_date(), 7)
AND ProductID NOT IN (SELECT ProductID FROM DiscountInfo)
""")

# COMMAND ----------

# Select all products
result = spark.sql("SELECT * FROM Products")
display(result)

# COMMAND ----------

# Clean up (drop tables)
spark.sql("DROP TABLE IF EXISTS Products")
spark.sql("DROP TABLE IF EXISTS DiscountInfo")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.