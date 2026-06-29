-- mart_style_long
-- Report-serving OBT: fact_style_measurement denormalized against its dims, kept
-- LONG (one row per work x child series, 8,505). Pre-joins the dims and precomputes
-- series_label so Evidence pages select-and-filter without re-joining the star.
-- The star schema stays the source of truth; this is the flat serving layer on top.

with fact as (
    select * from {{ ref('fact_style_measurement') }}
)

select
    -- work
    f.work_key,
    w.work_id,
    w.title,
    w.prose_type,
    w.word_count,

    -- author
    f.author_key,
    a.name as author,
    a.tradition,
    a.era,
    a.is_self,

    -- metric
    f.metric_key,
    f.metric_name,                       -- child series, e.g. funcword_the
    dm.metric_name as concept_name,      -- parent concept, e.g. function_word_frequency
    dm.display_name,
    dm.description,
    dm.category,
    dm.is_multivalue,
    case dm.metric_name                  -- child label with the family prefix stripped
        when 'function_word_frequency' then replace(f.metric_name, 'funcword_', '')
        when 'sentence_type_mix'       then replace(f.metric_name, 'senttype_', '')
        when 'punctuation_frequency'   then replace(f.metric_name, 'punct_', '')
        else f.metric_name
    end as series_label,

    -- measures (non-additive: never SUM)
    f.value,
    f.zscore

from fact f
inner join {{ ref('dim_work') }}   w  on w.work_key   = f.work_key
inner join {{ ref('dim_author') }} a  on a.author_key = f.author_key
inner join {{ ref('dim_metric') }} dm on dm.metric_key = f.metric_key
