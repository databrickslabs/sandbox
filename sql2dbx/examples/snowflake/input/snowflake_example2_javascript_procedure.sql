-- ==========================================
-- SNOWFLAKE EXAMPLE #2: Stored Procedure with Outlier Checking
-- ==========================================

CREATE OR REPLACE PROCEDURE PUBLIC.DEMO_FORECAST_OUTLIER_CHECK_UPDATE(
    SCHEMA_NAME VARCHAR,
    OUTLIER_MULTIPLIER FLOAT DEFAULT 1.30
)
RETURNS VARCHAR
LANGUAGE JAVASCRIPT
AS
$$
// Variable declarations
var result = 0;
var errorMsg = null;
var currentDate = null;
var errorProcName = "DEMO_FORECAST_OUTLIER_CHECK_UPDATE";

try {
    // Begin transaction
    snowflake.execute({sqlText: 'BEGIN'});
    
    // 1) Retrieve current date from a "SystemDateTable" in the given schema
    var sqlGetDate = `
        SELECT SystemDate
        FROM "${SCHEMA_NAME}".SystemDateTable;
    `;
    
    var rsDate = snowflake.execute({sqlText: sqlGetDate});
    if (rsDate.next()) {
        currentDate = rsDate.getColumnValue(1);
    } else {
        throw new Error("Failed to retrieve system date");
    }
    
    // 2) Create a temporary table to store outlier thresholds
    snowflake.execute({sqlText: `
        CREATE TEMPORARY TABLE TEMP_OUTLIER_INFO (
            LocationId VARCHAR(10),
            OutlierThreshold DECIMAL(8,2)
        );
    `});
    
    // 3) Insert outlier thresholds (99th percentile) from "HistoricalDataTable"
    var sqlInsertThresholds = `
        INSERT INTO TEMP_OUTLIER_INFO (LocationId, OutlierThreshold)
        SELECT
            d.LocationId,
            PERCENTILE_CONT(0.99)
            WITHIN GROUP (ORDER BY d.MetricValue)
            OVER (PARTITION BY d.LocationId)
        FROM "${SCHEMA_NAME}".HistoricalDataTable d
        WHERE TO_DATE(d.TargetDate) >= DATEADD(YEAR, -1, TO_DATE('${currentDate}'));
    `;
    
    snowflake.execute({sqlText: sqlInsertThresholds});
    
    // 4) Save original forecast values above threshold in "ForecastTable"
    var sqlSaveOriginals = `
        UPDATE "${SCHEMA_NAME}".ForecastTable f
        SET f.OriginalForecastValue = f.ForecastValue
        FROM TEMP_OUTLIER_INFO t
        WHERE f.LocationId = t.LocationId
          AND TO_DATE(f.ForecastDate) = TO_DATE('${currentDate}')
          AND f.ForecastValue > t.OutlierThreshold * ${OUTLIER_MULTIPLIER};
    `;
    
    snowflake.execute({sqlText: sqlSaveOriginals});
    
    // 5) Update outlier values to cap them at threshold * multiplier
    var sqlUpdateOutliers = `
        UPDATE "${SCHEMA_NAME}".ForecastTable f
        SET f.ForecastValue = t.OutlierThreshold * ${OUTLIER_MULTIPLIER}
        FROM TEMP_OUTLIER_INFO t
        WHERE f.LocationId = t.LocationId
          AND TO_DATE(f.ForecastDate) = TO_DATE('${currentDate}')
          AND f.ForecastValue > t.OutlierThreshold * ${OUTLIER_MULTIPLIER};
    `;
    
    snowflake.execute({sqlText: sqlUpdateOutliers});
    
    // Commit transaction
    snowflake.execute({sqlText: 'COMMIT'});
    
} catch (err) {
    result = 2;
    errorMsg = err.message;
    
    // Rollback if transaction is still open
    snowflake.execute({sqlText: 'ROLLBACK'});
    
    // Log the error (simplified):
    var logSql = `
        CALL LogError(
            '${errorProcName}',
            '${errorMsg.replace(/'/g, "''")}'
        );
    `;
    
    try {
        snowflake.execute({sqlText: logSql});
    } catch (logErr) {
        // Silently handle logging errors
    }
    
    // Re-throw the error with details
    throw new Error("Error in procedure: " + errorMsg);
}

return result.toString();
$$;