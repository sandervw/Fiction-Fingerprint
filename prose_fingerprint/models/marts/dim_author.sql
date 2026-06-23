-- One row per author, derived from the work-grain seed (Option A: dedup in dbt,
-- not by hand-shaping the CSV). GROUP BY every attribute so any author whose works
-- DISAGREE on tradition/era would split into duplicate author_keys; a uniqueness
-- test on author_key catches that loudly rather than silently picking a winner.
select
    {{ dbt_utils.generate_surrogate_key(['author']) }} as author_key,
    author as name,
    tradition,
    era,
    is_self
from {{ ref('seed_authors') }}
group by author, tradition, era, is_self
