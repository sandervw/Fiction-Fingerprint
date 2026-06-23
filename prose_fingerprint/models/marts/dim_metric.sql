-- One row per metric concept (15). Pass-through of seed_metrics + a surrogate key
-- so facts join on a stable hash, not a free-text metric_name.
select
    {{ dbt_utils.generate_surrogate_key(['metric_name']) }} as metric_key,
    metric_name,
    display_name,
    category,
    unit,
    higher_means,
    description,
    formula,
    is_multivalue
from {{ ref('seed_metrics') }}
