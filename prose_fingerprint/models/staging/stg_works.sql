-- One row per work. Rename/cast over raw_works.
select
    cast(work_id as {{ dbt.type_string() }})      as work_id,
    cast(word_count as {{ dbt.type_bigint() }})   as word_count,
    cast(loaded_at as {{ dbt.type_timestamp() }}) as loaded_at
from {{ source('raw', 'raw_works') }}
