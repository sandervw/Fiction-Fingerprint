-- One row per work. Light rename/cast over raw_works; no business logic here.
select
    cast(work_id as varchar)    as work_id,
    cast(word_count as bigint)  as word_count
from {{ source('raw', 'raw_works') }}
