-- ==========================================
-- T-SQL EXAMPLE #2: Stored Procedure with Outlier Checking
-- ==========================================

CREATE PROCEDURE [dbo].[DEMO_FORECAST_OUTLIER_CHECK_UPDATE]
    @SchemaName         NVARCHAR(128),
    @OutlierMultiplier  DECIMAL(5,2) = 1.30
AS
BEGIN
    -- Variable declarations
    DECLARE @Result           INT           = 0;
    DECLARE @ErrorMsg         NVARCHAR(MAX);
    DECLARE @CurrentDate      DATE;
    DECLARE @ErrorProcName    NVARCHAR(128) = OBJECT_NAME(@@PROCID);

    -- Create a temporary table to store outlier thresholds
    CREATE TABLE #TEMP_OUTLIER_INFO (
          LocationId       NVARCHAR(10),
          OutlierThreshold DECIMAL(8,2)
    );

    BEGIN TRY
        BEGIN TRAN FORECAST_OUTLIER_CHECK;

        -- 1) Retrieve current date from a "SystemDateTable" in the given schema
        DECLARE @SQL NVARCHAR(MAX);
        SET @SQL = N'
            SELECT @CurrentDateOut = SystemDate
            FROM ' + QUOTENAME(@SchemaName) + N'.SystemDateTable;
        ';

        EXEC sp_executesql
            @SQL,
            N'@CurrentDateOut DATE OUTPUT',
            @CurrentDateOut = @CurrentDate OUTPUT;

        -- 2) Insert outlier thresholds (99th percentile) from "HistoricalDataTable"
        SET @SQL = N'
            INSERT INTO #TEMP_OUTLIER_INFO (LocationId, OutlierThreshold)
            SELECT
                d.LocationId,
                CONVERT(DECIMAL(8,2),
                    PERCENTILE_CONT(0.99)
                    WITHIN GROUP (ORDER BY d.MetricValue)
                    OVER (PARTITION BY d.LocationId)
                )
            FROM ' + QUOTENAME(@SchemaName) + N'.HistoricalDataTable d
            WHERE CONVERT(DATE, d.TargetDate) >= DATEADD(YEAR, -1, @CurrentDateParam)
        ';

        EXEC sp_executesql
            @SQL,
            N'@CurrentDateParam DATE',
            @CurrentDateParam = @CurrentDate;

        -- 3) Save original forecast values above threshold in "ForecastTable"
        SET @SQL = N'
            UPDATE f
            SET f.OriginalForecastValue = f.ForecastValue
            FROM ' + QUOTENAME(@SchemaName) + N'.ForecastTable f
            INNER JOIN #TEMP_OUTLIER_INFO t ON f.LocationId = t.LocationId
            WHERE CONVERT(DATE, f.ForecastDate) = @CurrentDateParam
              AND f.ForecastValue > t.OutlierThreshold * @Multiplier
        ';

        EXEC sp_executesql
            @SQL,
            N'@CurrentDateParam DATE, @Multiplier DECIMAL(5,2)',
            @CurrentDateParam = @CurrentDate,
            @Multiplier = @OutlierMultiplier;

        -- 4) Update outlier values to cap them at threshold * multiplier
        SET @SQL = N'
            UPDATE f
            SET f.ForecastValue = t.OutlierThreshold * @Multiplier
            FROM ' + QUOTENAME(@SchemaName) + N'.ForecastTable f
            INNER JOIN #TEMP_OUTLIER_INFO t ON f.LocationId = t.LocationId
            WHERE CONVERT(DATE, f.ForecastDate) = @CurrentDateParam
              AND f.ForecastValue > t.OutlierThreshold * @Multiplier
        ';

        EXEC sp_executesql
            @SQL,
            N'@CurrentDateParam DATE, @Multiplier DECIMAL(5,2)',
            @CurrentDateParam = @CurrentDate,
            @Multiplier = @OutlierMultiplier;

        COMMIT TRAN FORECAST_OUTLIER_CHECK;
    END TRY
    BEGIN CATCH
        SET @Result = 2;
        SET @ErrorMsg = ERROR_MESSAGE();
        PRINT('Error: ' + @ErrorMsg);

        IF (@@TRANCOUNT > 0)
            ROLLBACK TRAN FORECAST_OUTLIER_CHECK;

        -- Log the error (simplified):
        EXEC [dbo].[LogError]
            @ProcName     = @ErrorProcName,
            @ErrorMessage = @ErrorMsg;

        -- Re-throw the error
        THROW;
    END CATCH;

    -- DROP TABLE IF EXISTS #TEMP_OUTLIER_INFO; -- Temp tables are automatically dropped at the end of the session

    RETURN @Result;
END;
GO
