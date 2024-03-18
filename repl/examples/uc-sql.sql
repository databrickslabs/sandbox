select * from samples.nyctaxi.trips limit 10

-- top 10 pickup hours by total fare volume
select
    window(tpep_pickup_datetime, "1 hour").start as pickup_hour,
    sum(fare_amount) as total_fares,
    avg(fare_amount) as avg_fare,
    count(1) as num_trips
from samples.nyctaxi.trips
where date(tpep_pickup_datetime) = '2016-01-16'
group by all
order by total_fares desc
limit 10
