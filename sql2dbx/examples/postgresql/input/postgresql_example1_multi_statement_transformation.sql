-- ==========================================
-- PostgreSQL EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a table for product data
CREATE TABLE products (
    product_id      INT,
    product_name    VARCHAR(100),
    price           NUMERIC(8,2),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Insert some sample products
INSERT INTO products (product_id, product_name, price)
VALUES
    (201, 'Gadget Alpha', 14.99),
    (202, 'Gadget Beta', 25.50),
    (203, 'Gadget Gamma', 32.00);

-- Create a temporary table to capture discount information
CREATE TEMP TABLE temp_discounts (
    product_id    INT,
    discount_rate FLOAT
);

-- Insert discount rates
INSERT INTO temp_discounts (product_id, discount_rate)
VALUES
    (201, 0.15),
    (203, 0.30);

-- Update product prices where a discount applies
-- PostgreSQL supports an UPDATE with FROM syntax
UPDATE products p
SET price = price * (1 - d.discount_rate)
FROM temp_discounts d
WHERE p.product_id = d.product_id;

-- Demonstrate a conditional DELETE
-- For example, remove products older than 7 days with no discount
DELETE FROM products p
USING temp_discounts d
WHERE p.created_at < (NOW() - INTERVAL '7 days')
  AND p.product_id NOT IN (
      SELECT product_id FROM temp_discounts
  );

-- Final SELECT to confirm changes
SELECT * FROM products;

-- Clean up
-- DROP TABLE IF EXISTS temp_discounts; -- Temp tables are automatically dropped at the end of the session
DROP TABLE IF EXISTS products;
