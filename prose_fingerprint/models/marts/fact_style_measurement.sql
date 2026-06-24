-- fact_style_measurement
-- The central fact: one measured number per work per metric series, carrying the
-- raw value and its per-series z-score. Swaps work_id for the conformed work_key and
-- carries author_key direct off dim_work, so the fact attaches straight to dim_work,
-- dim_author, and dim_metric (a star) and slices by author without hopping dim_work.
-- Grain: one row per work x measured series (3,213 = 51 x 63), keyed (work_id,
-- metric_name) since multivalue concepts share one metric_key across many series.

with measurements as (

    select
        work_id,
        metric_key,
        metric_name,
        value,
        zscore
    from {{ ref('int_measurements_normalized') }}

),

works as (  -- conformed work + author keys

    select
        work_id,
        work_key,
        author_key
    from {{ ref('dim_work') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['measurements.work_id', 'measurements.metric_name']) }} as measurement_key,
    works.work_key,            -- FK -> dim_work
    works.author_key,          -- FK -> dim_author (carried direct for slicing)
    measurements.metric_key,   -- FK -> dim_metric (concept grain)
    measurements.metric_name,  -- child series name (metric_key is concept-grain)
    measurements.value,
    measurements.zscore
from measurements
inner join works using (work_id)
