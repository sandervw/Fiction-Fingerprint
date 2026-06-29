-- One row per work × metric (long form). Rename metric → metric_name, cast value.
select
    cast(work_id as {{ dbt.type_string() }})      as work_id,
    cast(metric as {{ dbt.type_string() }})       as metric_name,
    cast(value as decimal(18,6))                  as value,
    cast(loaded_at as {{ dbt.type_timestamp() }}) as loaded_at
from {{ source('raw', 'raw_measurements') }}
