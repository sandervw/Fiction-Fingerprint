-- int_measurements_normalized
-- Adds a per-metric z-score to every measurement so metrics on different scales
-- become comparable (the standardized "fingerprint" form).
-- Grain: one row per work x measured series (51 works x 63 = 3,213).
-- The z-score window partitions by the CHILD metric_name, so each series gets its
-- own mean/spread.

with measurements as (

    select
        work_id,
        metric_name,
        value
    from {{ ref('stg_measurements') }}

),

-- Map each measured (child) name onto its metric concept name by prefix.
bridged as (

    select
        work_id,
        metric_name,
        value,
        case
            when metric_name like 'funcword_%' then 'function_word_frequency'
            when metric_name like 'punct_%'    then 'punctuation_frequency'
            when metric_name like 'senttype_%' then 'sentence_type_mix'
            else metric_name
        end as concept_name
    from measurements

),

-- Attach the concept's surrogate key. LEFT join so an unmapped child survives with
-- a NULL metric_key and trips the not_null test instead of being dropped.
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
