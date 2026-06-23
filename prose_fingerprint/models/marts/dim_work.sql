-- One row per work (51). The catalog (seed_authors) is the spine; word_count is a
-- measured enrichment joined in. LEFT JOIN so a catalogued work that never got
-- measured surfaces with a null word_count (caught by a not_null test) instead of
-- silently dropping out. author_key matches dim_author (same hash input) -> FK.
select
    {{ dbt_utils.generate_surrogate_key(['work_id']) }} as work_key,
    {{ dbt_utils.generate_surrogate_key(['author']) }}  as author_key,  -- FK -> dim_author
    work_id,
    a.title,
    w.word_count,
    case
        when w.word_count < 10000 then 'short-story'
        when w.word_count < 40000 then 'novella'
        else 'novel'
    end as prose_type
from {{ ref('seed_authors') }} a
left join {{ ref('stg_works') }} w using (work_id)
