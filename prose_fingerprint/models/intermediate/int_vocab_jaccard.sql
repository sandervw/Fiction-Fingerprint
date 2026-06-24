-- int_vocab_jaccard
-- Metric 15: vocabulary overlap between YOU and every other author, as a
-- Jaccard index = |shared terms| / |combined unique terms|. 0 = no shared
-- vocabulary, 1 = identical vocabularies. A "distinctive" metric: how close
-- another author's word palette sits to your own.
--
-- Grain: one row per OTHER author (the 9 non-self authors). "You" (is_self) is
-- the single fixed comparison target, so each row's author_key is the OTHER
-- author being measured against you.
--
-- term_count is deliberately IGNORED: Jaccard is presence/absence (set overlap),
-- not frequency-weighted. Each author's works are pooled into ONE distinct-term set.
--
-- Two deviations from the §3.1 draft, both deliberate:
--   * pool via the conformed dims (dim_work -> dim_author) for author_key + is_self;
--     the draft joined stg_works/seed_authors, which don't carry author_key.
--   * LEFT join `shared` so an author with zero overlap still emits a jaccard=0
--     row instead of vanishing (inner join would silently drop it).

with author_vocab as (

    -- Each author's pooled vocabulary: distinct content-word terms across all
    -- their works. DISTINCT collapses repeats within and across an author's works.
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

me as (  -- |A|: your vocabulary (the single is_self author)
    select term from author_vocab where is_self
),

them as (  -- every other author's vocabulary
    select author_key, term from author_vocab where not is_self
),

my_size as (  -- size of your vocabulary (one row, cross-joined in below)
    select count(*) as my_size from me
),

their_size as (  -- |B|: size of each other author's vocabulary
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
    -- |A∩B| / |A∪B|, where |A∪B| = |A| + |B| - |A∩B|. Denominator is always
    -- >= my_vocab_size > 0 (shared <= their_size), so no divide-by-zero guard needed.
    coalesce(shared.shared_terms, 0) * 1.0
        / (my_size.my_size + their_size.their_size - coalesce(shared.shared_terms, 0))
        as jaccard
from their_size
left join shared
    on their_size.author_key = shared.author_key
cross join my_size
