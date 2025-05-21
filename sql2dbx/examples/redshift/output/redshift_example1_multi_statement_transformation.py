# Databricks notebook source
# MAGIC %md
# MAGIC # redshift_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/redshift/input/redshift_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create products table (removing Redshift-specific features)
spark.sql("""
CREATE TABLE IF NOT EXISTS products (
    product_id INT,
    product_name STRING,
    price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT current_timestamp()
)
""")

# COMMAND ----------

# Note: Removed Redshift-specific DISTKEY, SORTKEY and ENCODE options which aren't supported in Databricks

# Insert initial product data
spark.sql("""
INSERT INTO products (product_id, product_name, price)
VALUES 
    (201, 'Red Gadget', 15.50),
    (202, 'Blue Widget', 24.99),
    (203, 'Green Gizmo', 8.75)
""")

# COMMAND ----------

# Create temporary discount table
spark.sql("""
CREATE OR REPLACE TABLE temp_discounts (
    product_id INT,
    discount_pct FLOAT
)
""")

# COMMAND ----------

# Insert discount data
spark.sql("""
INSERT INTO temp_discounts (product_id, discount_pct)
VALUES 
    (201, 0.05),
    (203, 0.20)
""")

# COMMAND ----------

# Update prices using MERGE (Databricks doesn't support UPDATE...FROM)
spark.sql("""
MERGE INTO products p
USING temp_discounts d
ON p.product_id = d.product_id
WHEN MATCHED THEN
  UPDATE SET price = price * (1 - d.discount_pct)
""")

# COMMAND ----------

# Delete older products (rewriting the logic for Databricks)
spark.sql("""
DELETE FROM products 
WHERE created_at < date_sub(current_timestamp(), 7) 
AND product_id NOT IN (SELECT product_id FROM temp_discounts)
""")

# COMMAND ----------

# Display final products
display(spark.sql("SELECT * FROM products"))

# COMMAND ----------

# Clean up tables
spark.sql("DROP TABLE IF EXISTS products")
spark.sql("DROP TABLE IF EXISTS temp_discounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.