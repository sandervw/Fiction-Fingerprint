-- Flags any work not carrying all 14 per-work metric concepts (Jaccard, the
-- 15th, is cross-author and lives elsewhere). Zero rows returned = pass.

select
    work_key,
    count(distinct metric_key) as concept_count
from {{ ref('fact_style_measurement') }}
group by work_key
having count(distinct metric_key) <> 14
