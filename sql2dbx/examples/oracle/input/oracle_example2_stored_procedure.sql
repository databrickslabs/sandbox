-- ==========================================
-- ORACLE EXAMPLE #2: Stored Procedure with Outlier Capping
-- ==========================================

CREATE OR REPLACE PROCEDURE AdjustSalesForecast(
    p_multiplier IN NUMBER DEFAULT 1.20
) AS
    -- Variables
    v_today          DATE;
    v_error_message  VARCHAR2(4000);
    v_proc_name      VARCHAR2(128) := 'AdjustSalesForecast';

    -- Temporary table to hold threshold data
    -- (In Oracle, you can also use Global Temporary Tables if desired)
BEGIN
    -- Example: create a temporary structure
    EXECUTE IMMEDIATE '
        CREATE TABLE TempOutlierThreshold (
            LocationId       VARCHAR2(10),
            ThresholdValue   NUMBER(10, 2)
        )
    ';

    BEGIN
        -- 1) Get the current date
        SELECT SYSDATE INTO v_today FROM DUAL;

        -- 2) Insert threshold data (e.g., 99th percentile) for each location
        --    We'll simulate it here with a fixed approach for brevity
        INSERT INTO TempOutlierThreshold (LocationId, ThresholdValue)
        SELECT
            LocationId,
            1000 * p_multiplier  -- pretend we computed a high threshold
        FROM SalesHistory
        WHERE SalesDate > ADD_MONTHS(v_today, -12);

        -- 3) Update ForecastTable to store original forecast if it exceeds threshold
        UPDATE ForecastTable f
        SET f.OriginalForecast = f.ForecastValue
        WHERE f.ForecastValue >
              (SELECT t.ThresholdValue FROM TempOutlierThreshold t
               WHERE t.LocationId = f.LocationId)
            * p_multiplier
          AND TRUNC(f.ForecastDate) = TRUNC(v_today);

        -- 4) Cap those outliers at threshold * multiplier
        UPDATE ForecastTable f
        SET f.ForecastValue =
              (SELECT t.ThresholdValue FROM TempOutlierThreshold t
               WHERE t.LocationId = f.LocationId)
            * p_multiplier
        WHERE f.ForecastValue >
              (SELECT t.ThresholdValue FROM TempOutlierThreshold t
               WHERE t.LocationId = f.LocationId)
            * p_multiplier
          AND TRUNC(f.ForecastDate) = TRUNC(v_today);

        -- Commit transaction
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            -- Capture error info
            v_error_message := SQLERRM;
            DBMS_OUTPUT.put_line('Error in procedure ' || v_proc_name || ': ' || v_error_message);

            -- Roll back any changes
            ROLLBACK;

            -- Optionally re-raise the exception
            RAISE;
    END;

    -- Cleanup
    -- EXECUTE IMMEDIATE 'DROP TABLE TempOutlierThreshold'; -- Temp tables are automatically dropped at the end of the session
END;
/
