-- ==========================================
-- Netezza EXAMPLE #2: Stored Procedure with Transaction and Dynamic SQL
-- ==========================================

CREATE PROCEDURE DEMO_ADJUST_THRESHOLD(
    IN P_TABLENAME VARCHAR(128),
    IN P_THRESHOLD FLOAT DEFAULT 100.0
)
RETURNS INT
LANGUAGE NZPLSQL
AS
BEGIN_PROC
    DECLARE V_COUNT INT := 0;             -- Will store number of updated rows
    DECLARE V_ERRORMSG VARCHAR(500);      -- For capturing error details
    DECLARE V_SQL VARCHAR(1000);          -- For building dynamic SQL
    
BEGIN
    -- Begin a transaction for our updates
    BEGIN;
    
    RAISE NOTICE 'Starting threshold adjustment in table: % with threshold: %', P_TABLENAME, P_THRESHOLD;
    
    -- 1) Build dynamic SQL to cap values at a certain threshold
    --    Suppose the table has a column "METRICVALUE" that needs capping
    V_SQL := 'UPDATE ' || P_TABLENAME ||
             ' SET METRICVALUE = ' || P_THRESHOLD ||
             ' WHERE METRICVALUE > ' || P_THRESHOLD || ';';
    
    -- 2) Execute dynamic SQL
    EXECUTE IMMEDIATE V_SQL;
    
    -- 3) Check how many rows were updated
    V_SQL := 'SELECT COUNT(*) FROM ' || P_TABLENAME ||
             ' WHERE METRICVALUE = ' || P_THRESHOLD || ';';
    EXECUTE IMMEDIATE V_SQL INTO V_COUNT;
    
    RAISE NOTICE 'Number of rows updated to threshold: %', V_COUNT;
    
    -- Commit the transaction if all is well
    COMMIT;
    
    RETURN V_COUNT;

EXCEPTION
    WHEN OTHERS THEN
        -- Capture error message
        GET STACKED DIAGNOSTICS V_ERRORMSG = MESSAGE_TEXT;
        
        RAISE NOTICE 'Error in procedure DEMO_ADJUST_THRESHOLD: %', V_ERRORMSG;
        
        -- Roll back any partial changes
        IF GET_TRAN_COUNT() > 0 THEN
            ROLLBACK;
        END IF;
        
        -- Re-raise the error so that the caller is aware
        RAISE;
END;

END_PROC;
