-- One row per work. seed_authors is the spine; LEFT JOIN word_count from stg_works
-- so an unmeasured work surfaces with a null word_count instead of dropping out.
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
