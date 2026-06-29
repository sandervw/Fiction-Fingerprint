-- One row per work × content-word term. Rename/cast over raw_vocab.
-- term_count carried for later frequency work; unused by Jaccard.
select
    cast(work_id as {{ dbt.type_string() }})      as work_id,
    cast(term as {{ dbt.type_string() }})         as term,
    cast(term_count as {{ dbt.type_bigint() }})   as term_count,
    cast(loaded_at as {{ dbt.type_timestamp() }}) as loaded_at
from {{ source('raw', 'raw_vocab') }}
