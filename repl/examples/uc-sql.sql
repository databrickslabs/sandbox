show tables in zacdav.default

describe table zacdav.default.stream_metrics_sink;

select * from samples.nyctaxi.trips limit 10

select
    window(tpep_pickup_datetime, "1 hour").start as pickup_hour,
    sum(fare_amount) as total_far_amount
from samples.nyctaxi.trips
where date(tpep_pickup_datetime) = '2016-01-16'
group by all
