-- One row per author, deduped from the work-grain seed via GROUP BY on every
-- attribute, so conflicting author rows split into duplicate keys and trip the test.
select
    {{ dbt_utils.generate_surrogate_key(['author']) }} as author_key,
    author as name,
    tradition,
    era,
    is_self
from {{ ref('seed_authors') }}
group by author, tradition, era, is_self
