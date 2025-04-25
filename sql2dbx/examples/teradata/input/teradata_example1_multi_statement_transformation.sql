-- ==========================================
-- TERADATA EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a MULTISET table to hold product data
CREATE MULTISET TABLE Products (
    ProductID       INTEGER,
    ProductName     VARCHAR(100),
    Price           DECIMAL(9,2),
    CreatedAt       TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP(0)
)
PRIMARY INDEX (ProductID);

-- Insert some sample products
INSERT INTO Products (ProductID, ProductName, Price)
VALUES (201, 'Gadget X', 15.00);

INSERT INTO Products (ProductID, ProductName, Price)
VALUES (202, 'Gadget Y', 25.50);

INSERT INTO Products (ProductID, ProductName, Price)
VALUES (203, 'Gadget Z', 40.00);

-- Create a MULTISET table to capture special discount rates
CREATE MULTISET TABLE Discounts (
    ProductID       INTEGER,
    DiscountRate    DECIMAL(4,3)
)
PRIMARY INDEX (ProductID);

-- Insert discount data
INSERT INTO Discounts (ProductID, DiscountRate)
VALUES (201, 0.10);

INSERT INTO Discounts (ProductID, DiscountRate)
VALUES (203, 0.25);

-- Update products based on Discounts
-- Teradata allows the "FROM" clause in UPDATE syntax:
UPDATE Products p
FROM Discounts d
SET p.Price = p.Price * (1 - d.DiscountRate)
WHERE p.ProductID = d.ProductID;

-- Demonstrate a conditional DELETE:
-- Example: remove items older than 7 days which are not discounted
DELETE FROM Products p
WHERE p.CreatedAt < (CURRENT_TIMESTAMP(0) - INTERVAL '7' DAY)
  AND p.ProductID NOT IN (
        SELECT d.ProductID FROM Discounts d
     );

-- Final SELECT to confirm changes
SEL * FROM Products;

-- Clean up
DROP TABLE Discounts;
DROP TABLE Products;
