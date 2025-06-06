# Databricks notebook source
# MAGIC %md
# MAGIC # postgresql_example1_multi_statement_transformation
# MAGIC This notebook was automatically converted from the script below. It may contain errors, so use it as a starting point and make necessary corrections.
# MAGIC
# MAGIC Source script: `/Workspace/Users/hiroyuki.nakazato@databricks.com/.bundle/sql2dbx/dev/files/examples/postgresql/input/postgresql_example1_multi_statement_transformation.sql`

# COMMAND ----------

# Create products table
spark.sql("""
CREATE TABLE IF NOT EXISTS products (
    product_id INT,
    product_name STRING,
    price DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
""")

# COMMAND ----------

# Insert initial product data
spark.sql("""
INSERT INTO products (product_id, product_name, price) 
VALUES 
    (201, 'Gadget Alpha', 14.99),
    (202, 'Gadget Beta', 25.50),
    (203, 'Gadget Gamma', 32.00)
""")

# COMMAND ----------

# Create a Delta table as a temporary substitute
spark.sql("""
CREATE OR REPLACE TABLE temp_discounts (
    product_id INT,
    discount_rate FLOAT
)
""")

# COMMAND ----------

# Insert discount data
spark.sql("""
INSERT INTO temp_discounts (product_id, discount_rate) 
VALUES 
    (201, 0.15),
    (203, 0.30)
""")

# COMMAND ----------

# Update prices based on discounts (using MERGE instead of UPDATE FROM)
spark.sql("""
MERGE INTO products p
USING temp_discounts d
ON p.product_id = d.product_id
WHEN MATCHED THEN
  UPDATE SET price = price * (1 - d.discount_rate)
""")

# COMMAND ----------

# DELETE with complex condition needs to be rewritten
spark.sql("""
DELETE FROM products 
WHERE created_at < date_sub(current_timestamp(), 7) 
AND product_id NOT IN (SELECT product_id FROM temp_discounts)
""")

# COMMAND ----------

# Display final products
products_df = spark.sql("SELECT * FROM products")
display(products_df)

# COMMAND ----------

# Cleanup
spark.sql("DROP TABLE IF EXISTS products")
spark.sql("DROP TABLE IF EXISTS temp_discounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Static Syntax Check Results
# MAGIC No syntax errors were detected during the static check.
# MAGIC However, please review the code carefully as some issues may only be detected during runtime.