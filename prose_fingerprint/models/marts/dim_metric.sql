-- One row per metric concept. Pass-through of seed_metrics + a surrogate key.
select
    {{ dbt_utils.generate_surrogate_key(['metric_name']) }} as metric_key,
    metric_name,
    display_name,
    category,
    unit,
    higher_means,
    description,
    formula,
    is_multivalue,
    additivity        -- Kimball additivity class; all non-additive, never SUM value or zscore
from {{ ref('seed_metrics') }}
