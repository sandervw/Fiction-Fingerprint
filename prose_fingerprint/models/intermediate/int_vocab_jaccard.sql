-- int_vocab_jaccard
-- Metric 15: vocabulary overlap between YOU and every other author, as a Jaccard
-- index = |shared| / |combined unique terms| (0 = none, 1 = identical).
-- Grain: one row per OTHER author (9 non-self). term_count ignored; Jaccard is
-- presence/absence, with each author's works pooled into one distinct-term set.

with author_vocab as (

    -- Each author's pooled vocabulary: distinct content-word terms across their works.
    select distinct
        dim_work.author_key,
        dim_author.is_self,
        stg_vocab.term
    from {{ ref('stg_vocab') }} as stg_vocab
    inner join {{ ref('dim_work') }} as dim_work
        on stg_vocab.work_id = dim_work.work_id
    inner join {{ ref('dim_author') }} as dim_author
        on dim_work.author_key = dim_author.author_key

),

me as (  -- |A|: your vocabulary
    select term from author_vocab where is_self
),

them as (  -- |B|: each other author's vocabulary
    select author_key, term from author_vocab where not is_self
),

my_size as (
    select count(*) as my_size from me
),

their_size as (
    select author_key, count(*) as their_size
    from them
    group by author_key
),

shared as (  -- |A ∩ B|: terms each other author shares with you
    select them.author_key, count(*) as shared_terms
    from them
    inner join me on them.term = me.term
    group by them.author_key
)

select
    their_size.author_key,
    my_size.my_size                                       as my_vocab_size,
    their_size.their_size                                 as their_vocab_size,
    coalesce(shared.shared_terms, 0)                      as shared_terms,
    -- |A∩B| / |A∪B|, where |A∪B| = |A| + |B| - |A∩B|.
    coalesce(shared.shared_terms, 0) * 1.0
        / (my_size.my_size + their_size.their_size - coalesce(shared.shared_terms, 0))
        as jaccard
from their_size
left join shared
    on their_size.author_key = shared.author_key
cross join my_size
