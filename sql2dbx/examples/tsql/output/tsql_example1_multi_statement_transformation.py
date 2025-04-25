# Databricks notebook source
# MAGIC %md
# MAGIC # tsql_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/tsql/input/tsql_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create Products table
spark.sql("""
CREATE TABLE IF NOT EXISTS Products (
    ProductID INT,
    ProductName STRING,
    Price DECIMAL(19,4),  -- MONEY type is mapped to DECIMAL in Databricks
    CreatedAt TIMESTAMP DEFAULT current_timestamp()
) USING DELTA
""")

# COMMAND ----------

# Insert data into Products
spark.sql("""
INSERT INTO Products (ProductID, ProductName, Price)
VALUES 
    (101, 'Widget A', 12.50),
    (102, 'Widget B', 19.99),
    (103, 'Widget C', 29.75)
""")

# COMMAND ----------

# Create a Discounts table (using a regular Delta table instead of a temp table)
spark.sql("""
CREATE OR REPLACE TABLE Discounts (
    ProductID INT,
    DiscountRate DOUBLE
) USING DELTA
""")

# COMMAND ----------

# Insert discount data
spark.sql("""
INSERT INTO Discounts (ProductID, DiscountRate)
VALUES 
    (101, 0.10),
    (103, 0.25)
""")

# COMMAND ----------

# Update product prices
# Using MERGE instead of UPDATE with JOIN since Databricks doesn't support the latter
spark.sql("""
MERGE INTO Products p
USING Discounts d
ON p.ProductID = d.ProductID
WHEN MATCHED THEN
  UPDATE SET Price = Price * (1 - d.DiscountRate)
""")

# COMMAND ----------

# Delete old products that aren't in the discounts table
# Need to rewrite as Databricks doesn't support DELETE with alias
spark.sql("""
DELETE FROM Products
WHERE CreatedAt < date_add(current_timestamp(), -7)
AND ProductID NOT IN (SELECT ProductID FROM Discounts)
""")

# COMMAND ----------

# Display all products
display(spark.sql("SELECT * FROM Products"))

# COMMAND ----------

# Clean up tables
spark.sql("DROP TABLE IF EXISTS Products")
spark.sql("DROP TABLE IF EXISTS Discounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC These are errors from static syntax checks. Manual corrections are required for these errors.
# MAGIC ### Spark SQL Syntax Errors
# MAGIC ```
# MAGIC Error in query 0: [PARSE_SYNTAX_ERROR] Syntax error at or near end of input. SQLSTATE: 42601 (line 1, pos 229)
# MAGIC
# MAGIC == SQL ==
# MAGIC EXPLAIN CREATE TABLE IF NOT EXISTS Products (     ProductID INT,     ProductName STRING,     Price DECIMAL(19,4),  -- MONEY type is mapped to DECIMAL in Databricks     CreatedAt TIMESTAMP DEFAULT current_timestamp() ) USING DELTA
# MAGIC -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------^^^
# MAGIC ```