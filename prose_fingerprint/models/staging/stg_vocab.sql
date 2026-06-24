-- One row per work × content-word term. Rename/cast over raw_vocab.
-- term_count carried for later frequency work; unused by Jaccard.
select
    cast(work_id as varchar)     as work_id,
    cast(term as varchar)        as term,
    cast(term_count as bigint)   as term_count,
    cast(loaded_at as timestamp) as loaded_at
from {{ source('raw', 'raw_vocab') }}
