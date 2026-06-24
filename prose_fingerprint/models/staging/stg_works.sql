-- One row per work. Rename/cast over raw_works.
select
    cast(work_id as varchar)     as work_id,
    cast(word_count as bigint)   as word_count,
    cast(loaded_at as timestamp) as loaded_at
from {{ source('raw', 'raw_works') }}
