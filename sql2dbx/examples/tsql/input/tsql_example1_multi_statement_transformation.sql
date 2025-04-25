-- ==========================================
-- T-SQL EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a table for product data
CREATE TABLE Products (
    ProductID INT,
    ProductName VARCHAR(100),
    Price MONEY,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- Insert some sample products
INSERT INTO Products (ProductID, ProductName, Price)
VALUES
    (101, 'Widget A', 12.50),
    (102, 'Widget B', 19.99),
    (103, 'Widget C', 29.75);

-- Create a temporary table to capture discounted items
CREATE TABLE #Discounts (
    ProductID INT,
    DiscountRate FLOAT
);

-- Insert discount rates
INSERT INTO #Discounts (ProductID, DiscountRate)
VALUES
    (101, 0.10),
    (103, 0.25);

-- Update product prices where a discount is applicable
-- (T-SQL allows an UPDATE with a FROM clause)
UPDATE p
SET p.Price = p.Price * (1 - d.DiscountRate)
FROM Products AS p
INNER JOIN #Discounts AS d ON p.ProductID = d.ProductID;

-- Demonstrate a conditional DELETE
-- Suppose we delete any product older than 7 days with no discounts
-- (Pretend we have some reason to prune old, non-discounted items)
DELETE p
FROM Products p
WHERE p.CreatedAt < DATEADD(DAY, -7, GETDATE())
  AND p.ProductID NOT IN (SELECT ProductID FROM #Discounts);

-- Final SELECT to confirm changes
SELECT * FROM Products;

-- Clean up permanent table only
-- DROP TABLE IF EXISTS #Discounts; -- Temp tables are automatically dropped at the end of the session
DROP TABLE IF EXISTS Products;
