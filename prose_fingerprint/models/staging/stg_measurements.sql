-- One row per work × metric (tidy/long). Rename `metric` → `metric_name` to
-- match the dimensional model; cast value to double. No logic here.
select
    cast(work_id as varchar)  as work_id,
    cast(metric as varchar)   as metric_name,
    cast(value as double)     as value
from {{ source('raw', 'raw_measurements') }}
