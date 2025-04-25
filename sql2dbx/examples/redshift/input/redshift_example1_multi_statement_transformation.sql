--------------------------------------------------------------------------------
-- Redshift EXAMPLE #1: Multi-Statement Data Transformation in Amazon Redshift
--------------------------------------------------------------------------------

-- Create a table for product data with Redshift-specific attributes
CREATE TABLE products
(
    product_id   INT,
    product_name VARCHAR(100),
    price        DECIMAL(10,2),
    created_at   TIMESTAMP DEFAULT SYSDATE
)
DISTKEY(product_id)
SORTKEY(product_id)
ENCODE ZSTD;

-- Insert some sample products
INSERT INTO products (product_id, product_name, price)
VALUES
    (201, 'Red Gadget', 15.50),
    (202, 'Blue Widget', 24.99),
    (203, 'Green Gizmo', 8.75);

-- Create a temporary table for discount rates
CREATE TEMP TABLE temp_discounts
(
    product_id   INT,
    discount_pct FLOAT
);

-- Insert discount rates
INSERT INTO temp_discounts (product_id, discount_pct)
VALUES
    (201, 0.05),
    (203, 0.20);

-- Update product prices to reflect applicable discounts
-- Redshift supports UPDATE with a FROM clause (similar to T-SQL)
UPDATE products AS p
SET price = price * (1 - d.discount_pct)
FROM temp_discounts d
WHERE p.product_id = d.product_id;

-- Conditionally delete products older than 7 days with no discounts
DELETE FROM products p
USING temp_discounts d
WHERE p.created_at < (SYSDATE - INTERVAL '7' DAY)
  AND p.product_id NOT IN (SELECT product_id FROM temp_discounts);

-- Final SELECT to verify changes
SELECT * FROM products;

-- Clean up
-- DROP TABLE IF EXISTS temp_discounts; -- Temp tables are automatically dropped at the end of the session
DROP TABLE IF EXISTS products;
