CREATE OR REPLACE MATERIALIZED VIEW main.default.dbsql_cost_per_query
(statement_id string,
query_source_id string,
query_source_type string,
client_application string,
executed_by string,
warehouse_id string,
statement_text string,
workspace_id string,
statement_hour_bucket_costs array<struct<hour_bucket:timestamp,hour_attributed_cost:double,hour_attributed_dbus:double>>,
start_time timestamp,
end_time timestamp,
query_work_start_time timestamp,
query_work_end_time timestamp,
duration_seconds double,
query_work_duration_seconds double,
query_work_task_time_seconds double,
query_attributed_dollars_estimation double,
query_attributed_dbus_estimation double,
url_helper string,
query_profile_url string,
most_recent_billing_hour timestamp,
billing_record_check string,
query_start_hour timestamp
)
SCHEDULE EVERY 1 HOUR
PARTITIONED BY (query_start_hour, workspace_id)
TBLPROPERTIES ('pipelines.autoOptimize.zOrderCols' = 'warehouse_id')
AS
(
WITH 
-- Must make sure the time window the MV is built on has enough data from ALL 3 tables to generate accurate results (both starts and end time ranges)
table_boundaries AS (
SELECT 
(SELECT MAX(event_time) FROM system.compute.warehouse_events) AS max_events_ts,
(SELECT MAX(end_time) FROM system.query.history) AS max_query_end_ts,
(SELECT MAX(usage_end_time) FROM system.billing.usage) AS max_billing_ts,
(SELECT MIN(event_time) FROM system.compute.warehouse_events) AS min_event_ts,
(SELECT MIN(start_time) FROM system.query.history) AS min_query_start_ts,
(SELECT MIN(usage_end_time) FROM system.billing.usage) AS min_billing_ts,
date_trunc('HOUR', LEAST(max_events_ts, max_query_end_ts, max_billing_ts)) AS selected_end_time,
(date_trunc('HOUR', GREATEST(min_event_ts, min_query_start_ts, min_billing_ts)) + INTERVAL 1 HOUR)::timestamp AS selected_start_time
),

----===== Warehouse Level Calculations =====-----
cpq_warehouse_usage AS (
  SELECT
    usage_metadata.warehouse_id AS warehouse_id,
    *
  FROM
    system.billing.usage AS u
  WHERE
    usage_metadata.warehouse_id IS NOT NULL
    AND usage_start_time >= (SELECT MIN(selected_start_time) FROM table_boundaries)
    AND usage_end_time <= (SELECT MAX(selected_end_time) FROM table_boundaries)
),

prices AS (
  select coalesce(price_end_time, date_add(current_date, 1)) as coalesced_price_end_time, *
  from system.billing.list_prices
  where currency_code = 'USD'
),

filtered_warehouse_usage AS (
    -- Warehouse usage is aggregated hourly, that will be the base assumption and grain of allocation moving forward. 
    -- Assume no duplicate records
    SELECT 
      u.warehouse_id warehouse_id,
      date_trunc('HOUR',u.usage_start_time) AS usage_start_hour,
      date_trunc('HOUR',u.usage_end_time) AS usage_end_hour,
      u.usage_quantity AS dbus,
      (
        CAST(p.pricing.effective_list.default AS FLOAT) * dbus
      ) AS usage_dollars
    FROM
      cpq_warehouse_usage AS u
        left join prices as p
        on u.sku_name=p.sku_name
        and u.usage_unit=p.usage_unit
        and (u.usage_end_time between p.price_start_time and p.coalesced_price_end_time)
),

----===== Query Level Calculations =====-----
cpq_warehouse_query_history AS (
  SELECT
    account_id,
    workspace_id,
    statement_id,
    executed_by,
    statement_text,
    compute.warehouse_id AS warehouse_id,
    execution_status,
    COALESCE(client_application, 'Unknown') AS client_application,
    (COALESCE(CAST(total_task_duration_ms AS FLOAT) / 1000, 0) +
      COALESCE(CAST(result_fetch_duration_ms AS FLOAT) / 1000, 0) +
      COALESCE(CAST(compilation_duration_ms AS FLOAT) / 1000, 0)
    )  AS query_work_task_time,
    start_time,
    end_time,
    timestampadd(MILLISECOND , waiting_at_capacity_duration_ms + waiting_for_compute_duration_ms + compilation_duration_ms, start_time) AS query_work_start_time,
    timestampadd(MILLISECOND, result_fetch_duration_ms, end_time) AS query_work_end_time,
    -- NEW - Query source
    CASE
      WHEN query_source.job_info.job_id IS NOT NULL THEN 'JOB'
      WHEN query_source.legacy_dashboard_id IS NOT NULL THEN 'LEGACY DASHBOARD'
      WHEN query_source.dashboard_id IS NOT NULL THEN 'AI/BI DASHBOARD'
      WHEN query_source.alert_id IS NOT NULL THEN 'ALERT'
      WHEN query_source.notebook_id IS NOT NULL THEN 'NOTEBOOK'
      WHEN query_source.sql_query_id IS NOT NULL THEN 'SQL QUERY'
      WHEN query_source.genie_space_id IS NOT NULL THEN 'GENIE SPACE'
      WHEN client_application IS NOT NULL THEN client_application
      ELSE 'UNKNOWN'
    END AS query_source_type,
    COALESCE(
      query_source.job_info.job_id,
      query_source.legacy_dashboard_id,
      query_source.dashboard_id,
      query_source.alert_id,
      query_source.notebook_id,
      query_source.sql_query_id,
      query_source.genie_space_id,
      'UNKNOWN'
    ) AS query_source_id
  FROM
    system.query.history AS h
  WHERE
    statement_type IS NOT NULL
    -- If query touches the boundaries at all, we will divy it up
    AND start_time < (SELECT MAX(selected_end_time) FROM table_boundaries)
    AND end_time > (SELECT MIN(selected_start_time) FROM table_boundaries)
    AND total_task_duration_ms > 0 --exclude metadata operations
),

--- Warehouse + Query Level level allocation
window_events AS (
    SELECT
        warehouse_id,
        workspace_id,
        event_type,
        event_time,
        cluster_count AS cluster_count,
        CASE 
            WHEN cluster_count = 0 THEN 'OFF'
            WHEN cluster_count > 0 THEN 'ON'
        END AS warehouse_state
    FROM system.compute.warehouse_events AS we
    -- Only get window events for when we have query history, otherwise, not usable
    WHERE EXISTS (SELECT warehouse_id FROM cpq_warehouse_query_history ws WHERE we.warehouse_id = ws.warehouse_id)
    AND event_time BETWEEN (SELECT MIN(selected_start_time) FROM table_boundaries) AND (SELECT MAX(selected_end_time) FROM table_boundaries)
),

-- Get the most recent state of the warehouse before the event window
pre_window_event AS (
    SELECT 
        warehouse_id,
        workspace_id,
        event_type,
        event_time,
        cluster_count AS cluster_count,
        CASE 
            WHEN cluster_count = 0 THEN 'OFF'
            WHEN cluster_count > 0 THEN 'ON'
        END AS warehouse_state
    FROM system.compute.warehouse_events pwe
    WHERE 
    event_time < (SELECT MIN(selected_start_time) FROM table_boundaries)
    AND event_time >= DATE_SUB((SELECT MIN(selected_start_time) FROM table_boundaries), 1) -- Make 1 day lookback window 
        AND EXISTS (
            SELECT 1
            FROM window_events we 
            WHERE we.warehouse_id = pwe.warehouse_id
            AND we.workspace_id = pwe.workspace_id
        ) -- Filter for only warehouses that have events in the selected period, very important for performance
    QUALIFY ROW_NUMBER() OVER (PARTITION BY pwe.warehouse_id ORDER BY event_time DESC) = 1
),

-- Combine Pre-Window and Window Events
all_events AS (
    SELECT * FROM pre_window_event
    UNION ALL
    SELECT * FROM window_events
),

-- Create Event Windows for Each Warehouse
event_windows AS (
    SELECT /*+ REPARTITION(128, event_window_start) */
        warehouse_id,
        warehouse_state AS window_state,
        event_time AS event_window_start,
        LEAD(event_time, 1, (SELECT MAX(selected_end_time) FROM table_boundaries)) OVER (
            PARTITION BY warehouse_id
            ORDER BY event_time
        ) AS event_window_end
    FROM all_events
),

all_seconds AS (
    SELECT
        e.warehouse_id,
        e.window_state,
        CAST(second_chunk AS TIMESTAMP) AS second_chunk
    FROM event_windows e
    LATERAL VIEW explode(
        sequence(
            CAST(UNIX_TIMESTAMP(e.event_window_start) AS BIGINT),
            CAST(UNIX_TIMESTAMP(e.event_window_end) - 1 AS BIGINT), -- Subtract 1 to avoid off-by-one errors
            1
        )
    ) AS second_chunk
    WHERE CAST(UNIX_TIMESTAMP(e.event_window_start) AS BIGINT) < CAST(UNIX_TIMESTAMP(e.event_window_end) AS BIGINT)
),

-- Weave in Query History for Each Warehouse
raw_history AS (
    SELECT /*+ REPARTITION(128, query_second) */
        warehouse_id, 
        CAST(query_second AS TIMESTAMP) AS query_second, -- Convert back to TIMESTAMP
        COUNT(0) AS queries_active
    FROM (
        SELECT 
            warehouse_id,
            start_seconds + seq_index AS query_second
        FROM (
            SELECT 
                warehouse_id,
                CAST(UNIX_TIMESTAMP(date_trunc('SECOND', query_work_start_time)) AS BIGINT) AS start_seconds, -- For Photon compatability
                CAST(UNIX_TIMESTAMP(date_trunc('SECOND', query_work_end_time)) AS BIGINT) AS end_seconds,
                end_seconds - start_seconds AS duration_seconds
            FROM cpq_warehouse_query_history f
            WHERE 
                EXISTS (
                    SELECT warehouse_id 
                    FROM window_events we 
                    WHERE we.warehouse_id = f.warehouse_id
                )
        ) base
        LATERAL VIEW posexplode(sequence(0, duration_seconds)) AS seq_index, seq_value
    ) expanded
    GROUP BY warehouse_id, query_second
),


state_by_second AS (
    SELECT 
        s.warehouse_id,
        s.second_chunk,
        MAX(s.window_state) AS warehouse_state,
        COALESCE(MAX(rh.queries_active), 0) AS query_load, -- queries_active will be null on this join because there were no queries for that warehouse active in the second
        CASE 
            WHEN COALESCE(MAX(s.window_state), 'OFF') = 'OFF' THEN 'OFF'
            WHEN query_load > 0 THEN 'UTILIZED'
            WHEN query_load = 0 AND MAX(s.window_state) = 'ON' THEN 'ON_IDLE' -- queries_active will be null on this join because there were no queries for that warehouse active in the second
        END AS utilization_flag
    FROM all_seconds s
    LEFT JOIN raw_history rh
      ON s.warehouse_id = rh.warehouse_id
         AND s.second_chunk = rh.query_second
    WHERE s.second_chunk <= (SELECT MAX(selected_end_time) FROM table_boundaries) -- Make you only calculate utailization metrics up to the clean end-hour window
    GROUP BY
        s.warehouse_id,
        s.second_chunk
),

utilization_by_warehouse AS (
SELECT 
    warehouse_id,
    date_trunc('HOUR', second_chunk) AS warehouse_hour,
    COUNT(CASE WHEN utilization_flag = 'UTILIZED' THEN second_chunk END) AS utilized_seconds,
    COUNT(CASE WHEN utilization_flag = 'ON_IDLE' THEN second_chunk END) AS idle_seconds,
    COUNT(*) AS total_seconds,
   round(
        try_divide(
            COUNT(CASE WHEN utilization_flag = 'UTILIZED' THEN second_chunk END),
            (COUNT(CASE WHEN utilization_flag = 'UTILIZED' THEN second_chunk END)  + COUNT(CASE WHEN utilization_flag = 'ON_IDLE' THEN second_chunk END))
        ), 
        2
    ) AS utilization_proportion
FROM state_by_second
GROUP BY warehouse_id, date_trunc('HOUR', second_chunk)
),

cleaned_warehouse_info AS (
  SELECT
  wu.warehouse_id,
  wu.usage_start_hour AS hour_bucket,
  wu.dbus,
  wu.usage_dollars,
  ut.utilized_seconds,
  ut.idle_seconds,
  ut.total_seconds,
  ut.utilization_proportion
  FROM filtered_warehouse_usage wu
  LEFT JOIN utilization_by_warehouse AS ut ON wu.warehouse_id = ut.warehouse_id -- Join on calculation grain - warehouse/hour
    AND wu.usage_start_hour = ut.warehouse_hour
),

hour_intervals AS (
  -- Generate valid hourly buckets for each query
  SELECT
    statement_id,
    warehouse_id,
    query_work_start_time,
    query_work_end_time,
    query_work_task_time,
    explode(
      sequence(
        0,
        floor((UNIX_TIMESTAMP(query_work_end_time) - UNIX_TIMESTAMP(date_trunc('hour', query_work_start_time))) / 3600)
      )
    ) AS hours_interval,
    timestampadd(hour, hours_interval, date_trunc('hour', query_work_start_time)) AS hour_bucket
  FROM
    cpq_warehouse_query_history
),

statement_proportioned_work AS (
    SELECT * , 
        GREATEST(0,
          UNIX_TIMESTAMP(LEAST(query_work_end_time, timestampadd(hour, 1, hour_bucket))) -
          UNIX_TIMESTAMP(GREATEST(query_work_start_time, hour_bucket))
        ) AS overlap_duration,
      query_work_task_time * (overlap_duration / (CAST(query_work_end_time AS DOUBLE) - CAST(query_work_start_time AS DOUBLE))) AS proportional_query_work
    FROM hour_intervals
),


attributed_query_work_all AS (
    SELECT
      statement_id,
      hour_bucket,
      warehouse_id,
      SUM(proportional_query_work) AS attributed_query_work
    FROM
      statement_proportioned_work
    GROUP BY
      statement_id,
      warehouse_id,
      hour_bucket
),

--- Cost Attribution
warehouse_time as (
  select
    warehouse_id,
    hour_bucket,
    SUM(attributed_query_work) as total_work_done_on_warehouse
  from
    attributed_query_work_all
  group by
    warehouse_id, hour_bucket
),

-- Create statement_id / hour bucket allocated combinations
history AS (
  SELECT
    a.*,
    b.total_work_done_on_warehouse,
    CASE
      WHEN attributed_query_work = 0 THEN NULL
      ELSE attributed_query_work / total_work_done_on_warehouse
    END AS proportion_of_warehouse_time_used_by_query
  FROM attributed_query_work_all a
    inner join warehouse_time b on a.warehouse_id = b.warehouse_id
              AND a.hour_bucket = b.hour_bucket -- Will only run for completed hours from warehouse usage - nice clean boundary
),

history_with_pricing AS (
  SELECT
    h1.*,
    wh.dbus AS total_warehouse_period_dbus,
    wh.usage_dollars AS total_warehouse_period_dollars,
    wh.utilization_proportion AS warehouse_utilization_proportion,
    wh.hour_bucket AS warehouse_hour_bucket,
    MAX(wh.hour_bucket) OVER() AS warehouse_max_hour_bucket
  FROM
    history AS h1
    LEFT JOIN cleaned_warehouse_info AS wh ON h1.warehouse_id = wh.warehouse_id AND h1.hour_bucket = wh.hour_bucket
),

-- This is at the statement_id / hour grain (there will be duplicates for each statement for each hour bucket the query spans)
query_attribution AS (
  SELECT
    a.*,
    warehouse_max_hour_bucket AS most_recent_billing_hour,
    CASE WHEN warehouse_hour_bucket IS NOT NULL THEN 'Has Billing Reocrd' ELSE 'No Billing Record for this hour and warehouse yet available' END AS billing_record_check,
    CASE
      WHEN total_work_done_on_warehouse = 0 THEN NULL
      ELSE attributed_query_work / total_work_done_on_warehouse
    END AS query_task_time_proportion,

    (warehouse_utilization_proportion * total_warehouse_period_dollars) * query_task_time_proportion  AS query_attributed_dollars_estimation,
    (warehouse_utilization_proportion * total_warehouse_period_dbus) * query_task_time_proportion  AS query_attributed_dbus_estimation
  FROM
    history_with_pricing a
)

-- Final Output
select
      qq.statement_id,
      FIRST(qq.query_source_id) AS query_source_id,
      FIRST(qq.query_source_type) AS query_source_type,
      FIRST(qq.client_application) AS client_application,
      FIRST(qq.executed_by) AS executed_by,
      FIRST(qq.warehouse_id) AS warehouse_id,
      FIRST(qq.statement_text) AS statement_text,
      FIRST(qq.workspace_id) AS workspace_id,
      COLLECT_LIST(NAMED_STRUCT('hour_bucket', qa.hour_bucket, 'hour_attributed_cost', query_attributed_dollars_estimation, 'hour_attributed_dbus', query_attributed_dbus_estimation)) AS statement_hour_bucket_costs,
      FIRST(qq.start_time) AS start_time,
      FIRST(qq.end_time) AS end_time,
      FIRST(qq.query_work_start_time) AS query_work_start_time,
      FIRST(qq.query_work_end_time) AS query_work_end_time,
      COALESCE(timestampdiff(MILLISECOND, FIRST(qq.start_time), FIRST(qq.end_time))/1000, 0) AS duration_seconds,
      COALESCE(timestampdiff(MILLISECOND, FIRST(qq.query_work_start_time), FIRST(qq.query_work_end_time))/1000, 0) AS query_work_duration_seconds,
      FIRST(query_work_task_time) AS query_work_task_time_seconds,
      SUM(query_attributed_dollars_estimation) AS query_attributed_dollars_estimation,
      SUM(query_attributed_dbus_estimation) AS query_attributed_dbus_estimation,
      FIRST(CASE
        WHEN query_source_type = 'JOB' THEN CONCAT('/jobs/', query_source_id)
        WHEN query_source_type = 'SQL QUERY' THEN CONCAT('/sql/queries/', query_source_id)
        WHEN query_source_type = 'AI/BI DASHBOARD' THEN CONCAT('/sql/dashboardsv3/', query_source_id)
        WHEN query_source_type = 'LEGACY DASHBOARD' THEN CONCAT('/sql/dashboards/', query_source_id)
        WHEN query_source_type = 'ALERTS' THEN CONCAT('/sql/alerts/', query_source_id)
        WHEN query_source_type = 'GENIE SPACE' THEN CONCAT('/genie/rooms/', query_source_id)
        WHEN query_source_type = 'NOTEBOOK' THEN CONCAT('/editor/notebooks/', query_source_id)
        ELSE ''
      END) as url_helper,
      FIRST(CONCAT('/sql/history?uiQueryProfileVisible=true&queryId=', qq.statement_id)) AS query_profile_url,
       FIRST(most_recent_billing_hour) AS most_recent_billing_hour,
       FIRST(billing_record_check) AS billing_record_check,
       date_trunc('HOUR', FIRST(qq.start_time)) AS query_start_hour
      from query_attribution qa
      LEFT JOIN cpq_warehouse_query_history AS qq ON qa.statement_id = qq.statement_id -- creating dups of the objects but just re-aggregating
            AND qa.warehouse_id = qq.warehouse_id
      GROUP BY qq.statement_id
)