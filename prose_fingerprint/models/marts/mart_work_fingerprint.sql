-- mart_work_fingerprint
-- Wide pivot of fact_style_measurement: one row per work, a z-score column per
-- series (63). author_key carries through for rolling up to author downstream.

{% set series = dbt_utils.get_column_values(
    table=ref('fact_style_measurement'),
    column='metric_name',
    order_by='metric_name'
) %}

with measured as (

    select
        f.work_key,
        w.work_id,
        w.title,
        f.author_key,
        a.name as author,
        f.metric_name,
        f.zscore
    from {{ ref('fact_style_measurement') }} f
    inner join {{ ref('dim_work') }}   w using (work_key)
    inner join {{ ref('dim_author') }} a on a.author_key = f.author_key

)

select
    work_key,
    work_id,
    title,
    author_key,
    author,
    {{ dbt_utils.pivot(
        column='metric_name',
        values=series,
        agg='max',
        then_value='zscore',
        else_value='null',
        quote_identifiers=true
    ) }}
from measured
group by 1, 2, 3, 4, 5
