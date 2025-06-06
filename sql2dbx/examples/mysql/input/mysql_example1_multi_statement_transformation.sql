-- ==========================================
-- MySQL EXAMPLE #1: Multi-Statement Data Transformation
-- ==========================================

-- Create a table for orders
CREATE TABLE Orders (
    OrderID INT,
    CustomerName VARCHAR(100),
    OrderDate DATETIME DEFAULT NOW(),
    OrderTotal DECIMAL(10,2)
);

-- Insert some sample orders
INSERT INTO Orders (OrderID, CustomerName, OrderTotal)
VALUES
    (101, 'Alice', 200.00),
    (102, 'Bob', 350.75),
    (103, 'Charlie', 99.99);

-- Create a temporary table for order statuses
CREATE TEMPORARY TABLE TempOrderStatus (
    OrderID INT,
    Status VARCHAR(50)
);

-- Insert statuses
INSERT INTO TempOrderStatus (OrderID, Status)
VALUES
    (101, 'PROCESSING'),
    (102, 'SHIPPED'),
    (104, 'CANCELLED');

-- Update orders with a discount if they appear in the temporary status table
-- Demonstrates MySQL's UPDATE with JOIN syntax
UPDATE Orders AS o
JOIN TempOrderStatus AS t ON o.OrderID = t.OrderID
SET o.OrderTotal = o.OrderTotal * 0.90  -- 10% discount
WHERE t.Status = 'SHIPPED';

-- Delete any order older than 90 days if not referenced in TempOrderStatus
DELETE o
FROM Orders AS o
WHERE o.OrderDate < DATE_SUB(NOW(), INTERVAL 90 DAY)
  AND o.OrderID NOT IN (SELECT OrderID FROM TempOrderStatus);

-- Final check
SELECT * FROM Orders;

-- Clean up
-- DROP TABLE IF EXISTS TempOrderStatus; -- Temp tables are automatically dropped at the end of the session
DROP TABLE IF EXISTS Orders;
