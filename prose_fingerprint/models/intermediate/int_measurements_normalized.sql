-- int_measurements_normalized
-- Adds a per-metric z-score to every measurement so metrics living on wildly
-- different scales (sentence length ~7-31, adjective density ~0.05-0.10,
-- Yule's K ~78-216) become directly comparable. This standardized form is what
-- lets a work's metrics line up into a single "fingerprint".
--
-- Grain: one row per work x measured series (63 child names, including the
-- multivalue children funcword_* / punct_* / senttype_*). 51 works x 63 = 3,213.
--
-- Two joins of note:
--   1. BRIDGE: the multivalue children do NOT match dim_metric (which holds only
--      the 15 concept rows). We derive each child's parent CONCEPT name by prefix
--      so it can pick up the concept's surrogate key + metadata. The 11
--      single-value metrics already equal their own concept name.
--   2. Z-SCORE PARTITION: the window partitions by the CHILD metric_name, so each
--      series (e.g. funcword_the across 51 works) gets its own mean/spread. We do
--      NOT partition by the concept key -- pooling all funcword_* together would
--      mix unrelated distributions and produce a meaningless average.

with measurements as (

    select
        work_id,
        metric_name,
        value
    from {{ ref('stg_measurements') }}

),

-- Map each measured (child) name onto its metric CONCEPT name.
bridged as (

    select
        work_id,
        metric_name,
        value,
        case
            when metric_name like 'funcword_%' then 'function_word_frequency'
            when metric_name like 'punct_%'    then 'punctuation_frequency'
            when metric_name like 'senttype_%' then 'sentence_type_mix'
            else metric_name  -- the 11 single-value metrics name themselves
        end as concept_name
    from measurements

),

-- Attach the concept's stable surrogate key from the dimension. LEFT join on
-- purpose: if a child prefix is ever left unmapped, its row survives with a
-- NULL metric_key and the not_null test in _intermediate.yml fails by name
-- (fail loud) -- rather than an inner join silently dropping the row. Today all
-- 63 prefixes map, so no NULLs are produced; the test is a tripwire for future
-- metrics added to the extractor.
joined as (

    select
        bridged.work_id,
        bridged.metric_name,
        dim_metric.metric_key,
        bridged.value
    from bridged
    left join {{ ref('dim_metric') }} as dim_metric
        on bridged.concept_name = dim_metric.metric_name

)

select
    work_id,
    metric_key,
    metric_name,
    value,
    {{ zscore('value', 'metric_name') }} as zscore
from joined
