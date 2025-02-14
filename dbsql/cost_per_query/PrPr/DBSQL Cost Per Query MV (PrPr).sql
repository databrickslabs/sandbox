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

table_bound_expld AS 
(
select timestampadd(hour, h, selected_start_time) as selected_hours
  from table_boundaries
  join lateral explode(sequence(0, timestampdiff(hour, selected_start_time, selected_end_time), 1)) as t (h)
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
    timestampadd(MILLISECOND, coalesce(result_fetch_duration_ms, 0), end_time) AS query_work_end_time,
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
    AND start_time < (SELECT selected_end_time FROM table_boundaries)
    AND end_time > (SELECT selected_start_time FROM table_boundaries)
    AND total_task_duration_ms > 0 --exclude metadata operations
     and compute.warehouse_id is not null -- = 'd13162f928a069c7'
)
  ,  cte_warehouse as
(
  select warehouse_id, min(query_work_start_time) as min_start_time
    from cpq_warehouse_query_history
group by warehouse_id
)
,
--- Warehouse + Query Level level allocation
window_events AS (
    SELECT
        warehouse_id,
        event_type,
        event_time,
        cluster_count AS cluster_count,
        CASE
            WHEN cluster_count = 0 THEN 'OFF'
            WHEN cluster_count > 0 THEN 'ON'
        END AS warehouse_state
    FROM system.compute.warehouse_events AS we
    -- Only get window events for when we have query history, otherwise, not usable
    WHERE warehouse_id in (SELECT warehouse_id FROM cte_warehouse)
    AND event_time >= (SELECT timestampadd(day, -1, selected_start_time) FROM table_boundaries)
    AND event_time <= (SELECT selected_end_time FROM table_boundaries)
)
  ,  cte_agg_events_prep as
(
select warehouse_id
     , warehouse_state
     , event_time
     , row_number() over W1
     - row_number() over W2 as grp
  from window_events
window W1 as (partition by warehouse_id                  order by event_time asc)
     , W2 as (partition by warehouse_id, warehouse_state order by event_time asc)
)
  ,  cte_agg_events as
(
  select warehouse_id
       , warehouse_state                                    as window_state
       , min(event_time)                                    as event_window_start
       , lead(min(event_time), 1, selected_end_time) over W as event_window_end
    from cte_agg_events_prep
    join table_boundaries
group by warehouse_id
       , warehouse_state
       , grp
       , selected_end_time
  window W as (partition by warehouse_id order by min(event_time) asc)
)
  ,  cte_all_events as
(
select warehouse_id
     , window_state
     , date_trunc('second', event_window_start) as event_window_start
     , date_trunc('second', event_window_end  ) as event_window_end
  from cte_agg_events
 where date_trunc('second', event_window_start) < date_trunc('second', event_window_end)
 --and date_trunc('second', event_window_start) >= timestamp '2024-11-14 09:00:00'
)
  ,  cte_queries_event_cnt as
(
  select warehouse_id
       , case num
           when 1
           then date_trunc('second', query_work_start_time)
           else timestampadd(second, case when date_trunc('second', query_work_start_time) = date_trunc('second', query_work_end_time) then 1 else 0 end, date_trunc('second', query_work_end_time))
         end as query_event_time
       , sum(num) as num_queries
    from cpq_warehouse_query_history
    join lateral explode(array(1, -1)) as t (num)
group by 1, 2
)
  ,  cte_raw_history as
(
select warehouse_id
     , query_event_time                                    as query_start
     , lead(query_event_time, 1, selected_end_time) over W as query_end
     , sum(num_queries) over W as queries_active
  from cte_queries_event_cnt
  join table_boundaries
window W as (partition by warehouse_id order by query_event_time asc)
)
  ,  cte_raw_history_byday as
(
  select /*+ repartition(64, warehouse_id, query_start_dt) */
         warehouse_id
       , case num
           when 0
           then query_start
           else timestampadd(day, num, query_start::date)
         end::date as query_start_dt
       , case num
           when 0
           then query_start
           else timestampadd(day, num, query_start::date)
         end as query_start
       , case num
           when timestampdiff(day, query_start::date, query_end::date)
           then query_end
           else timestampadd(day, num + 1, query_start::date)
         end as query_end
       , queries_active
    from cte_raw_history
    join lateral explode(sequence(0, timestampdiff(day, query_start::date, query_end::date), 1)) as t (num)
)
  ,  cte_all_time_union as
(
select warehouse_id
     , case num when 1 then event_window_start else event_window_end end ts_start
  from cte_all_events
  join lateral explode(array(1, -1)) as t (num)
 union 
select warehouse_id
     , case num when 1 then query_start else query_end end
  from cte_raw_history_byday
  join lateral explode(array(1, -1)) as t (num)
 union
select warehouse_id, selected_hours
  from cte_warehouse
  join table_bound_expld on true
-- where selected_hours >= timestampadd(day, -1, min_start_time)
)
  ,  cte_periods as
(
select /*+ repartition(64, warehouse_id, dt_start) */
       warehouse_id
     , ts_start::date as dt_start
     , ts_start
     , lead(ts_start, 1, selected_end_time) over W as ts_end
  from cte_all_time_union
  join table_boundaries
window W as (partition by warehouse_id order by ts_start asc)
)
  ,  cte_merge_periods as
(
    select /*+ broadcast(r) */
           p.warehouse_id
         , date_trunc('hour', p.ts_start) as ts_hour
         , sum(timestampdiff(second, p.ts_start, p.ts_end)) as duration
         , case
             when e.window_state = 'OFF'
               or e.window_state is null
             then 'OFF'
             when r.queries_active > 0
             then 'UTILIZED'
             else 'ON_IDLE'
           end as utilization_flag
      from cte_periods           as p
 left join cte_all_events        as e  on e.warehouse_id       = p.warehouse_id
                                      and e.event_window_start < p.ts_end
                                      and e.event_window_end   > p.ts_start
 left join cte_raw_history_byday as r  on r.warehouse_id       = p.warehouse_id
                                      and r.query_start_dt     = p.dt_start
                                      and r.query_start        < p.ts_end
                                      and r.query_end          > p.ts_start
                                      and r.queries_active     > 0
                                      and e.window_state      <> 'OFF'
     where p.ts_start < p.ts_end
  group by all
),

utilization_by_warehouse AS (
  select warehouse_id
       , ts_hour as warehouse_hour
       , coalesce(sum(duration) filter(where utilization_flag = 'UTILIZED'), 0) as utilized_seconds
       , coalesce(sum(duration) filter(where utilization_flag = 'ON_IDLE' ), 0) as idle_seconds
       , coalesce(sum(duration) filter(where utilization_flag = 'OFF'     ), 0) as off_seconds
       , coalesce(sum(duration), 0) as total_seconds
       , try_divide(utilized_seconds, utilized_seconds + idle_seconds)::decimal(3,2) as utilization_proportion
    from cte_merge_periods
group by warehouse_id
       , ts_hour
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
        CASE WHEN CAST(query_work_end_time AS DOUBLE) - CAST(query_work_start_time AS DOUBLE) = 0
        THEN 0
        ELSE query_work_task_time * (overlap_duration / (CAST(query_work_end_time AS DOUBLE) - CAST(query_work_start_time AS DOUBLE)))
        END AS proportional_query_work
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
    CASE WHEN warehouse_hour_bucket IS NOT NULL THEN 'Has Billing Record' ELSE 'No Billing Record for this hour and warehouse yet available' END AS billing_record_check,
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