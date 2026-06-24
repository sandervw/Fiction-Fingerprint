-- One row per work × metric (long form). Rename metric → metric_name, cast value.
select
    cast(work_id as varchar)     as work_id,
    cast(metric as varchar)      as metric_name,
    cast(value as double)        as value,
    cast(loaded_at as timestamp) as loaded_at
from {{ source('raw', 'raw_measurements') }}
