# Databricks notebook source
# MAGIC %md
# MAGIC # netezza_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/netezza/input/netezza_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create PRODUCTS table (omitting DISTRIBUTE ON clause as it's not supported in Spark)
spark.sql("""
CREATE TABLE IF NOT EXISTS PRODUCTS (
    PRODUCTID INT, 
    PRODUCTNAME STRING, 
    PRICE FLOAT, 
    CREATEDAT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
""")

# COMMAND ----------

# Insert sample products
spark.sql("""
INSERT INTO PRODUCTS (PRODUCTID, PRODUCTNAME, PRICE) VALUES 
    (1001, 'NZA Widget', 15.75), 
    (1002, 'NZA Gadget', 21.50), 
    (1003, 'NZA Gizmo', 42.99)
""")

# COMMAND ----------

# Create DISCOUNTS table (omitting DISTRIBUTE ON clause)
spark.sql("""
CREATE TABLE IF NOT EXISTS DISCOUNTS (
    PRODUCTID INT,
    DISCOUNTRATE FLOAT
)
""")

# COMMAND ----------

# Insert discount data
spark.sql("""
INSERT INTO DISCOUNTS (PRODUCTID, DISCOUNTRATE) VALUES 
    (1001, 0.20), 
    (1003, 0.15)
""")

# COMMAND ----------

# Update product prices with discounts
# Databricks doesn't support UPDATE with FROM clause, so we use MERGE instead
spark.sql("""
MERGE INTO PRODUCTS t
USING DISCOUNTS s
ON t.PRODUCTID = s.PRODUCTID
WHEN MATCHED THEN
  UPDATE SET t.PRICE = t.PRICE * (1 - s.DISCOUNTRATE)
""")

# COMMAND ----------

# Delete old products not in discounts table
spark.sql("""
DELETE FROM PRODUCTS
WHERE CREATEDAT < date_sub(CURRENT_TIMESTAMP(), 7) 
AND PRODUCTID NOT IN (SELECT PRODUCTID FROM DISCOUNTS)
""")

# COMMAND ----------

# Display current products
products_df = spark.sql("SELECT * FROM PRODUCTS")
display(products_df)

# COMMAND ----------

# Clean up tables
spark.sql("DROP TABLE IF EXISTS DISCOUNTS")
spark.sql("DROP TABLE IF EXISTS PRODUCTS")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.