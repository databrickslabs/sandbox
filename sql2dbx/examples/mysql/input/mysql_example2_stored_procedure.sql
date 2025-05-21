-- ==========================================
-- MySQL EXAMPLE #2: Stored Procedure with Threshold Checking
-- ==========================================

DELIMITER $$

CREATE PROCEDURE DemoThresholdCheck(
    IN p_table_name VARCHAR(64),
    IN p_threshold DECIMAL(10,2),
    OUT p_rows_updated INT
)
BEGIN
    -- Declare a handler to catch any SQL errors, then roll back
    DECLARE EXIT HANDLER FOR SQLEXCEPTION 
    BEGIN
        ROLLBACK;
        SET p_rows_updated = -1;
    END;

    -- Start a transaction
    START TRANSACTION;

    -- 1) Create a temporary table that captures rows above the threshold
    --    We'll build this query dynamically based on p_table_name
    SET @sql = CONCAT(
        'CREATE TEMPORARY TABLE TempData AS ',
        'SELECT id, metric ',
        'FROM ', p_table_name, ' ',
        'WHERE metric > ', p_threshold
    );

    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

    -- 2) Update the original table to cap values at the threshold
    SET @sql = CONCAT(
        'UPDATE ', p_table_name, ' ',
        'SET metric = ', p_threshold, ' ',
        'WHERE metric > ', p_threshold
    );

    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    SET p_rows_updated = ROW_COUNT();  -- track how many rows changed
    DEALLOCATE PREPARE stmt;

    -- DROP TEMPORARY TABLE IF EXISTS TempData; -- Temp tables are automatically dropped at the end of the session

    -- Commit the transaction
    COMMIT;
END $$

DELIMITER ;
