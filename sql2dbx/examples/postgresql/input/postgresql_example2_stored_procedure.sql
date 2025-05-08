-- ==========================================
-- PostgreSQL EXAMPLE #2: Stored Procedure with Outlier Checking
-- ==========================================

CREATE OR REPLACE PROCEDURE demo_forecast_outlier_check_update(
    _schema_name       TEXT,
    _outlier_multiplier NUMERIC(5,2) DEFAULT 1.30
)
LANGUAGE plpgsql
AS $$
DECLARE
    _errmsg         TEXT;
    _current_date   DATE;
BEGIN
    -- Create a temporary table to store outlier thresholds
    CREATE TEMP TABLE temp_outlier_info (
        location_id       VARCHAR(10),
        outlier_threshold NUMERIC(8,2)
    );

    -- Begin a transaction
    BEGIN
        -- 1) Retrieve current date from a table in the given schema
        EXECUTE format(
            'SELECT system_date FROM %I.system_date_table LIMIT 1',
            _schema_name
        )
        INTO _current_date;

        IF _current_date IS NULL THEN
            RAISE NOTICE 'No valid date found in system_date_table; exiting.';
            RETURN;
        END IF;

        -- 2) Insert outlier thresholds based on 99th percentile from "historical_data_table"
        EXECUTE format(
            'INSERT INTO temp_outlier_info (location_id, outlier_threshold)
             SELECT d.location_id,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY d.metric_value)
             FROM %I.historical_data_table d
             WHERE CAST(d.target_date AS DATE) >= %L::DATE - INTERVAL ''1 YEAR''
             GROUP BY d.location_id',
            _schema_name, _current_date
        );

        -- 3) Update "forecast_table" to store original forecast values that exceed outlier_threshold * multiplier
        EXECUTE format(
            'UPDATE %I.forecast_table f
             SET original_forecast_value = forecast_value
             FROM temp_outlier_info t
             WHERE f.location_id = t.location_id
               AND CAST(f.forecast_date AS DATE) = %L::DATE
               AND f.forecast_value > t.outlier_threshold * %s',
            _schema_name,
            _current_date,
            _outlier_multiplier
        );

        -- 4) Cap outlier forecast values at threshold * multiplier
        EXECUTE format(
            'UPDATE %I.forecast_table f
             SET forecast_value = t.outlier_threshold * %s
             FROM temp_outlier_info t
             WHERE f.location_id = t.location_id
               AND CAST(f.forecast_date AS DATE) = %L::DATE
               AND f.forecast_value > t.outlier_threshold * %s',
            _schema_name,
            _outlier_multiplier,
            _current_date,
            _outlier_multiplier
        );

        -- Commit the transaction
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            _errmsg := SQLERRM;
            RAISE NOTICE 'Error occurred: %', _errmsg;

            -- Always rollback on error
            ROLLBACK;

            -- Re-raise the error
            RAISE;
    END;

    RETURN;
END;
$$;