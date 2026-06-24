-- fact_vocab_overlap
-- Metric 15 promoted to author-PAIR grain: stamps your author_key as the fixed left
-- side so each row reads as an edge, author_key_a (you) <-> author_key_b (other).
-- Grain: one row per OTHER author (9).

with overlap as (

    select
        author_key as author_key_b,
        my_vocab_size,
        their_vocab_size,
        shared_terms,
        jaccard
    from {{ ref('int_vocab_jaccard') }}

),

me as (  -- the self author; supplies author_key_a for every pair

    select author_key as author_key_a
    from {{ ref('dim_author') }}
    where is_self

)

select
    {{ dbt_utils.generate_surrogate_key(['me.author_key_a', 'overlap.author_key_b']) }} as overlap_key,
    me.author_key_a,            -- FK -> dim_author (you)
    overlap.author_key_b,       -- FK -> dim_author (other)
    overlap.my_vocab_size,
    overlap.their_vocab_size,
    overlap.shared_terms,
    overlap.jaccard
from overlap
cross join me
