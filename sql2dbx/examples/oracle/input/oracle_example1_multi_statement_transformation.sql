-- ==========================================
-- ORACLE EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a table to hold product data
CREATE TABLE Products (
    ProductID         NUMBER(10, 0),
    ProductName       VARCHAR2(100),
    Price             NUMBER(10, 2),
    CreatedAt         DATE DEFAULT SYSDATE
);

-- Insert sample products
INSERT INTO Products (ProductID, ProductName, Price)
VALUES
    (201, 'Gizmo X', 14.50),
    (202, 'Gizmo Y', 21.99),
    (203, 'Gizmo Z', 38.25);

-- Create a Global Temporary Table (or a regular table if preferred)
-- to store discount information
CREATE GLOBAL TEMPORARY TABLE DiscountInfo (
    ProductID      NUMBER(10, 0),
    DiscountRate   NUMBER(5, 2)
) ON COMMIT PRESERVE ROWS;

-- Insert discount rates
INSERT INTO DiscountInfo (ProductID, DiscountRate)
VALUES
    (201, 0.15),
    (203, 0.30);

-- Update product prices to apply discounts (use a subquery or MERGE in Oracle)
UPDATE Products p
SET p.Price = p.Price * (1 - (
    SELECT d.DiscountRate
    FROM DiscountInfo d
    WHERE d.ProductID = p.ProductID
))
WHERE p.ProductID IN (
    SELECT d.ProductID
    FROM DiscountInfo d
);

-- Conditional DELETE:
-- Delete products older than 7 days, if they have no discount entry
DELETE FROM Products p
WHERE p.CreatedAt < (SYSDATE - 7)
  AND p.ProductID NOT IN (
      SELECT d.ProductID
      FROM DiscountInfo d
  );

-- Final SELECT to confirm changes
SELECT * FROM Products;

-- Clean up
-- DROP TABLE DiscountInfo; -- Global Temporary Tables are automatically dropped at the end of the session
DROP TABLE Products;
