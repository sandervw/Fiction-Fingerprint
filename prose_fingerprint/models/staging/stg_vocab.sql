-- One row per work × content-word term. Light rename/cast over raw_vocab.
-- Feeds the dbt-side Jaccard overlap (metric 15); term_count carried for
-- later frequency work (TF-IDF / weighted overlap), unused by Jaccard itself.
select
    cast(work_id as varchar)     as work_id,
    cast(term as varchar)        as term,
    cast(term_count as bigint)   as term_count,
    cast(loaded_at as timestamp) as loaded_at  -- batch load stamp (UTC)
from {{ source('raw', 'raw_vocab') }}
