# Databricks notebook source
# MAGIC %md
# MAGIC # teradata_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/teradata/input/teradata_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create Products table in Delta format
spark.sql("""
CREATE OR REPLACE TABLE Products (
    ProductID INT,
    ProductName STRING,
    Price DECIMAL(9,2),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
""")

# COMMAND ----------

# Note: PRIMARY INDEX is specific to Teradata and doesn't have a direct equivalent in Databricks

# Insert initial product records
spark.sql("""
INSERT INTO Products (ProductID, ProductName, Price)
VALUES (201, 'Gadget X', 15.00)
""")

# COMMAND ----------

spark.sql("""
INSERT INTO Products (ProductID, ProductName, Price)
VALUES (202, 'Gadget Y', 25.50)
""")

# COMMAND ----------

spark.sql("""
INSERT INTO Products (ProductID, ProductName, Price)
VALUES (203, 'Gadget Z', 40.00)
""")

# COMMAND ----------

# Create Discounts table
spark.sql("""
CREATE OR REPLACE TABLE Discounts (
    ProductID INT,
    DiscountRate DECIMAL(4,3)
)
""")

# COMMAND ----------

# Note: PRIMARY INDEX is specific to Teradata and ignored here

# Insert discount records
spark.sql("""
INSERT INTO Discounts (ProductID, DiscountRate)
VALUES (201, 0.10)
""")

# COMMAND ----------

spark.sql("""
INSERT INTO Discounts (ProductID, DiscountRate)
VALUES (203, 0.25)
""")

# COMMAND ----------

# Update product prices based on discount rates
# Databricks doesn't support UPDATE with FROM, so we use MERGE instead
spark.sql("""
MERGE INTO Products p
USING Discounts d
ON p.ProductID = d.ProductID
WHEN MATCHED THEN
  UPDATE SET p.Price = p.Price * (1 - d.DiscountRate)
""")

# COMMAND ----------

# Delete products older than 7 days that have no discount
spark.sql("""
DELETE FROM Products
WHERE CreatedAt < date_sub(current_timestamp(), 7)
AND ProductID NOT IN (SELECT ProductID FROM Discounts)
""")

# COMMAND ----------

# Display the contents of the Products table
products_df = spark.sql("SELECT * FROM Products")
display(products_df)

# COMMAND ----------

# Drop the tables
spark.sql("DROP TABLE IF EXISTS Discounts")
spark.sql("DROP TABLE IF EXISTS Products")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.