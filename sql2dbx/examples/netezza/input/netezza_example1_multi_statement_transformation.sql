-- ==========================================
-- Netezza EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a table for product data, with a distribution key on ProductID
CREATE TABLE PRODUCTS (
    PRODUCTID INT,
    PRODUCTNAME VARCHAR(100),
    PRICE FLOAT,
    CREATEDAT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTE ON (PRODUCTID);

-- Insert some sample products
INSERT INTO PRODUCTS (PRODUCTID, PRODUCTNAME, PRICE)
VALUES
    (1001, 'NZA Widget', 15.75),
    (1002, 'NZA Gadget', 21.50),
    (1003, 'NZA Gizmo', 42.99);

-- Create a table for discount information
CREATE TABLE DISCOUNTS (
    PRODUCTID INT,
    DISCOUNTRATE FLOAT
)
DISTRIBUTE ON (PRODUCTID);

-- Insert discount rates
INSERT INTO DISCOUNTS (PRODUCTID, DISCOUNTRATE)
VALUES
    (1001, 0.20),
    (1003, 0.15);

-- Update product prices using a join
-- Note: Netezza allows an UPDATE with a FROM clause
UPDATE PRODUCTS AS p
SET p.PRICE = p.PRICE * (1 - d.DISCOUNTRATE)
FROM DISCOUNTS AS d
WHERE p.PRODUCTID = d.PRODUCTID;

-- Demonstrate a conditional DELETE:
-- Remove products older than 7 days that do not appear in DISCOUNTS
-- (Assume for example that items beyond 7 days with no discount are deprecated)
DELETE FROM PRODUCTS p
WHERE p.CREATEDAT < (CURRENT_TIMESTAMP - INTERVAL '7' DAY)
  AND p.PRODUCTID NOT IN (SELECT PRODUCTID FROM DISCOUNTS);

-- Final SELECT to confirm changes
SELECT * FROM PRODUCTS;

-- Clean up
DROP TABLE IF EXISTS DISCOUNTS;
DROP TABLE IF EXISTS PRODUCTS;
