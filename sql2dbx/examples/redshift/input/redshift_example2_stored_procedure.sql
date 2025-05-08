--------------------------------------------------------------------------------
-- Redshift EXAMPLE #2: Stored Procedure with Basic Transaction Handling in Redshift
--------------------------------------------------------------------------------

-- Create a stored procedure to update outlier prices in a "sales_forecast" table
-- based on a multiplier threshold
CREATE OR REPLACE PROCEDURE public.update_outlier_prices(
    threshold_multiplier DECIMAL(5,2) DEFAULT 1.25
)
LANGUAGE plpgsql
AS $$
DECLARE
    row_count INT := 0;
    temp_table_name TEXT := 'temp_outlier_thresholds';
BEGIN
    -- Create a temporary table to store threshold data
    EXECUTE 'CREATE TEMP TABLE ' || temp_table_name || ' (
        product_id INT,
        outlier_threshold DECIMAL(10,2)
    )';

    -- Begin transaction
    BEGIN
        -- Insert threshold data (example: fixed or from another table)
        EXECUTE 'INSERT INTO ' || temp_table_name || '
                 SELECT product_id,
                        PERCENTILE_CONT(0.99)
                        WITHIN GROUP (ORDER BY forecast_price)
                        OVER (PARTITION BY product_id)
                 FROM sales_forecast
                 WHERE forecast_date >= current_date - 365';

        -- Update outlier forecast prices (cap them at threshold * multiplier)
        EXECUTE 'UPDATE sales_forecast f
                 SET forecast_price = t.outlier_threshold * ' || threshold_multiplier || '
                 FROM ' || temp_table_name || ' t
                 WHERE f.product_id = t.product_id
                   AND f.forecast_price > t.outlier_threshold * ' || threshold_multiplier;

        GET DIAGNOSTICS row_count = ROW_COUNT;  -- Example of checking row count
        RAISE NOTICE 'Rows updated: %', row_count;

        COMMIT;  -- Commit if all goes well
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Error occurred: %', SQLERRM;
            ROLLBACK;
            RETURN;
    END;

    -- Clean up the temporary table
    -- EXECUTE 'DROP TABLE IF EXISTS ' || temp_table_name || ';'; -- Temp tables are automatically dropped at the end of the session

    -- Optional return or message
    RAISE NOTICE 'Procedure completed with multiplier %', threshold_multiplier;
END;
$$;
