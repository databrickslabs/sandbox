-- ==========================================
-- EXAMPLE 1: Multi-Statement Data Transformation in Snowflake
-- ==========================================

-- Optional session-level statement (will be commented out or handled specially in Databricks)
ALTER SESSION SET TIMEZONE = 'America/Los_Angeles';

-- Create a table for customer data
CREATE TABLE CUSTOMERS (
    CUSTOMER_ID NUMBER(10, 0),
    FULL_NAME VARCHAR(100),
    STATUS VARCHAR(10),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Insert some initial data
INSERT INTO CUSTOMERS (CUSTOMER_ID, FULL_NAME, STATUS)
VALUES
    (1, 'Alice Smith', 'ACTIVE'),
    (2, 'Bob Jones', 'INACTIVE'),
    (3, 'Charlie Brown', 'ACTIVE');

-- Create a temporary table to store an address list
CREATE TEMPORARY TABLE TEMP_ADDRESSES (
    ADDRESS_ID NUMBER(10, 0),
    CUSTOMER_ID NUMBER(10, 0),
    ADDRESS_LINE VARCHAR(200)
);

-- Insert data into the temporary table
INSERT INTO TEMP_ADDRESSES (ADDRESS_ID, CUSTOMER_ID, ADDRESS_LINE)
VALUES
    (100, 1, '123 Maple Street'),
    (101, 2, '456 Oak Avenue'),
    (102, 3, '789 Pine Road');

-- Illustrate a simple UPDATE using a JOIN-like syntax (Snowflake allows FROM in UPDATE)
UPDATE CUSTOMERS
SET STATUS = 'PENDING'
FROM TEMP_ADDRESSES
WHERE CUSTOMERS.CUSTOMER_ID = TEMP_ADDRESSES.CUSTOMER_ID
  AND TEMP_ADDRESSES.ADDRESS_LINE LIKE '%Pine%';

-- Demonstrate a DELETE that references another table
-- (Snowflake can do: DELETE FROM <table> USING <other> WHERE ...)
DELETE FROM TEMP_ADDRESSES
USING CUSTOMERS
WHERE TEMP_ADDRESSES.CUSTOMER_ID = CUSTOMERS.CUSTOMER_ID
  AND CUSTOMERS.STATUS = 'INACTIVE';

-- Final SELECT to confirm transformations
SELECT * FROM CUSTOMERS;
SELECT * FROM TEMP_ADDRESSES;

-- Clean up
-- DROP TABLE IF EXISTS TEMP_ADDRESSES; -- Temp tables are automatically dropped at the end of the session
DROP TABLE IF EXISTS CUSTOMERS;
