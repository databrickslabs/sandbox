-- ==========================================
-- TERADATA EXAMPLE #2: Stored Procedure with Basic Error Handling
-- ==========================================

REPLACE PROCEDURE CheckInventoryLevels (
    IN pLocationId   VARCHAR(10),
    IN pThreshold    DECIMAL(8,2),
    OUT pResultCode  INTEGER
)
L1: BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET pResultCode = 2; -- Indicate error
        -- In a real scenario, you might log or handle the error differently
        ROLLBACK;
        LEAVE L1;
    END;

    -- Default result code
    SET pResultCode = 0;

    -- Begin a Teradata transaction
    BT;

    -- Create a VOLATILE TABLE to store items that exceed the given threshold
    CREATE VOLATILE TABLE VolatileHighStock (
        ItemId      INTEGER,
        LocationId  VARCHAR(10),
        StockLevel  DECIMAL(8,2)
    ) ON COMMIT PRESERVE ROWS;

    -- Insert data into the volatile table (simplified example).
    -- We assume we have a permanent table Inventory with columns ItemId, LocationId, StockLevel
    INSERT INTO VolatileHighStock (ItemId, LocationId, StockLevel)
    SELECT i.ItemId, i.LocationId, i.StockLevel
    FROM Inventory i
    WHERE i.LocationId = pLocationId
      AND i.StockLevel > pThreshold;

    -- Suppose we adjust stock values in the main Inventory table if they exceed threshold
    UPDATE Inventory inv
    FROM VolatileHighStock v
    SET inv.StockLevel = pThreshold
    WHERE inv.ItemId = v.ItemId
      AND inv.LocationId = v.LocationId;

    -- Commit the transaction
    ET;

    -- Drop the volatile table
    DROP TABLE VolatileHighStock;

END;
