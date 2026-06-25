# Project: prose-fingerprint

A 3-week dbt Core project that models stylometric measurements of studied authors (Wagner, Peake, Eddison, Vance, Clark Ashton Smith) against your own prose, served as a 15-metric comparison dashboard.

**Design constraint:** built locally, _portable to Fabric_. The swap to the `dbt-fabric` Warehouse adapter later should be a `profiles.yml`.

---

## 1. Architecture (EL → T → BI)

```
┌─────────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ Python extractor│ → │ DuckDB (raw) │ → │ dbt (models)│ → │ BI dashboard │
│ (reads texts,   │   │ landing zone │   │ THE PROJECT │   │ you vs Wagner│
│  emits metrics) │   │              │   │             │   │  × 15 metrics│
└─────────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
   NOT dbt's job        the "L"           the "T" — focus     the "exposure"
```

- **Extractor (Python):** lives at repo-root `extract/`, outside the dbt project (portability). Uses **spaCy** (`en_core_web_sm`, NER off). Emits **tidy rows**, never wide tables. Lands three `raw` tables in DuckDB (see §1.1).
- **DuckDB:** zero-infra local warehouse — a single file, no server to run. Gentlest warehouse to start on (it's basically "SQLite for analytics"), and the `dbt-duckdb` adapter is first-rate.
- **dbt Core:** the part you're here to learn. Everything below.
- **BI:** see §6.

> **Keep all messy text/regex/list work in Python.** This is both good architecture _and_ the #1 portability rule — Fabric's T-SQL warehouse surface won't have DuckDB's string/list/regex niceties.

### 1.1 Extractor, as built

Modules under `extract/` (each ≤300 lines, full type hints):

| Module            | Job                                                          |
| ----------------- | ------------------------------------------------------------ |
| `extract.py`      | orchestration: manifest → clean → parse → land               |
| `cleaning.py`     | markdown → plain prose (regex only; keeps prose punctuation) |
| `stylometrics.py` | the 14 per-work metric functions                             |
| `lexicons.py`     | tunable tables (function words, archaic list, punctuation)   |
| `vocab.py`        | metric 15's vocabulary emitter (content-word lemmas)         |
| `loaders.py`      | DuckDB landing: row shapes + writing the three `raw` tables  |

**Metric contract:** each per-work metric is `(doc: Doc) -> dict[str, float]`. The driver flattens that dict to tidy rows, so a multi-value metric (function words, punctuation, sentence type) becomes N rows; its keys use `prefix_subkey` (`funcword_the`, `punct_semicolon`, `senttype_complex`). A "word" is a spaCy `is_alpha` token, the shared denominator throughout.

**Raw landing tables** (one parse per work feeds all three):

| Table                  | Grain         | Columns                         |
| ---------------------- | ------------- | ------------------------------- |
| `raw.raw_works`        | work          | `work_id`, `word_count`         |
| `raw.raw_measurements` | work × metric | `work_id`, `metric`, `value`    |
| `raw.raw_vocab`        | work × term   | `work_id`, `term`, `term_count` |

Labels (title, author, tradition, era, is_self) stay in `seed_authors.csv` and arrive on the dbt side as seeds; `prose_type` is derived in `dim_work` from `word_count`. Corpus: 51 works (24 self + 27 others), ~1.97M words.

---

## 2. Dimensional Model (Fact Constellation)

Three fact tables sharing the same dimensions is a **fact constellation** (a.k.a. galaxy schema): multiple facts at different grains joined to **conformed dimensions** (`dim_author`, `dim_work`, `dim_metric`). `fact_style_measurement` is the **primary** fact; the other two exist only because they live at grains the primary fact can't hold (a pairwise comparison and a histogram).

The primary fact is deliberately **tall and narrow** — one row per work per metric — so adding a 16th metric needs no schema change, and it pivots cleanly for BI.

| Table                                     | Grain              | Key columns                                                     |
| ----------------------------------------- | ------------------ | --------------------------------------------------------------- |
| `dim_author`                              | one row per author | `author_key`, `name`, `tradition`, `era`, `is_self`             |
| `dim_work`                                | one row per work   | `work_key`, `author_key`, `title`, `year`, `word_count`, `type` |
| `dim_metric`                              | one row per metric | `metric_key`, `metric_name`, `display_name`, etc                |
| `fact_style_measurement` _(primary)_      | work × metric      | `work_key`, `author_key`, `metric_key`, `value`, `zscore`       |
| `fact_vocab_overlap` _(secondary)_        | author pair        | `author_key_a`, `author_key_b`, `jaccard`, `shared_terms`       |
| `fact_sentence_length_bins` _(secondary)_ | work × bin         | `work_key`, `length_bin`, `sentence_count`                      |

`is_self = true` on your author row makes "you vs everyone" just a filter, not special-casing.

---

## 3. The 15 Metrics (final set)

| #   | Metric                       | Category    | Summary                                                                    |
| --- | ---------------------------- | ----------- | -------------------------------------------------------------------------- |
| 1   | Mean word length             | lexical     | Average characters per word; denser diction runs longer.                   |
| 2   | Yule's K                     | lexical     | Vocabulary richness; higher = more repetition (poorer); length-stable.     |
| 3   | % archaic/rare words         | lexical     | Proportion matching an archaic/rare-word list (CAS, Eddison).              |
| 4   | Honoré's R                   | lexical     | Richness from hapax proportion; higher = richer vocabulary; length-robust. |
| 5   | Function-word frequency      | lexical     | Rates of "the, of, and"; classic hard-to-fake fingerprint.                 |
| 6   | Mean sentence length         | syntactic   | Average words per sentence; pacing proxy.                                  |
| 7   | Sentence-length stdev        | syntactic   | Variation in sentence length; rhythm "burstiness" (Peake).                 |
| 8   | Mean parse-tree depth        | syntactic   | Average grammatical nesting depth from dependency parse.                   |
| 9   | Sentence-type mix            | syntactic   | Proportion of simple, compound, and complex sentences.                     |
| 10  | Punctuation frequency        | mechanical  | Rates of all marks (semicolons, dashes, colons, commas).                   |
| 11  | Contraction rate             | mechanical  | Frequency of contractions ("don't"); deeply ingrained habit.               |
| 12  | Dialogue : narration ratio   | structural  | Share of quoted speech versus narration (Vance high, Eddison low).         |
| 13  | Adjective density            | structural  | Adjectives as a fraction of all words; descriptive heaviness.              |
| 14  | Adverb density               | structural  | Adverbs as a fraction of all words; a "weak prose" tell.                   |
| 15  | Jaccard vocab overlap vs you | distinctive | Shared-vocabulary fraction between an author and you.                      |

### 3.1 Metric 15 in detail: Jaccard vocabulary overlap

Metric 15 is the odd one out: it compares two authors, so its grain and implementation both differ from the other 14.

**Python emits a vocabulary, not a value.** `vocab.py`'s `vocab_terms(doc)` returns a work's **content-word lemmas** with their per-work counts (open-class POS, stopwords dropped, lemmatised and lowercased; proper nouns excluded so character names don't drown the signal). These land as tidy `raw.raw_vocab` rows, tens of thousands of them, one per `(work_id, term, term_count)`. The count is unused by Jaccard (which is presence-based) but is there for later frequency work like TF-IDF or weighted overlap:

| work_id            | term     | term_count |
| ------------------ | -------- | ---------- |
| rhialto-marvellous | sorcerer | 14         |
| rhialto-marvellous | journey  | 5          |
| the-glass-sky      | sorcerer | 9          |
| the-glass-sky      | glass    | 22         |

**dbt computes the overlap** in `int_vocab_jaccard.sql`. It pools each author's works into one distinct-term vocabulary (`stg_vocab → dim_work → dim_author`, then `distinct term`), then measures every other author against you. Intersection is a join on `term`; union is `|A| + |B| - |A∩B|`. Pure joins and counts, so it ports to Fabric. As built: 10 authors (1 self + 9 others) → 9 output rows, and a LEFT join keeps a zero-overlap author at jaccard=0 rather than dropping it.

```sql
with author_vocab as (
    select distinct dw.author_key, da.is_self, v.term
    from {{ ref('stg_vocab') }}   v
    join {{ ref('dim_work') }}    dw on v.work_id = dw.work_id
    join {{ ref('dim_author') }}  da on dw.author_key = da.author_key
),
me   as (select term from author_vocab where is_self),
them as (select author_key, term from author_vocab where not is_self),
my_size    as (select count(*) as my_size from me),
their_size as (select author_key, count(*) as their_size from them group by author_key),
shared as (
    select t.author_key, count(*) as shared_terms   -- |A ∩ B|: terms that survive the join
    from them t join me on t.term = me.term
    group by t.author_key
)
select
    ts.author_key,
    coalesce(sh.shared_terms, 0) as shared_terms,
    coalesce(sh.shared_terms, 0) * 1.0
        / (m.my_size + ts.their_size - coalesce(sh.shared_terms, 0)) as jaccard   -- |A∩B| / |A∪B|
from their_size ts
left join shared sh on ts.author_key = sh.author_key   -- LEFT: a zero-overlap author still emits jaccard=0
cross join my_size m
```

**Worked example.** You = {sorcerer, journey, glass, horizon}; Vance = {sorcerer, magic, journey, tower}. Shared = {sorcerer, journey} = 2; union = 4 + 4 - 2 = 6; jaccard = 2 / 6 = **0.33**. One row out per other author feeds `fact_vocab_overlap`.

---

## 4. dbt Project Layout

```
prose_fingerprint/
├── dbt_project.yml
├── packages.yml                # dbt_utils
├── profiles.yml                # dual target: duckdb (now) + fabric (later)
├── seeds/
│   ├── seed_authors.csv         # tradition/era/is_self metadata
│   └── seed_metrics.csv         # metric definitions → dim_metric
├── models/
│   ├── staging/
│   │   ├── _sources.yml         # raw tables loaded by Python
│   │   ├── stg_measurements.sql # rename/cast/clean (view)
│   │   ├── stg_works.sql
│   │   └── stg_vocab.sql
│   ├── intermediate/
│   │   ├── int_measurements_normalized.sql   # z-scores via macro
│   │   └── int_vocab_jaccard.sql
│   └── marts/
│       ├── dim_author.sql
│       ├── dim_work.sql
│       ├── dim_metric.sql
│       ├── fact_style_measurement.sql
│       ├── fact_vocab_overlap.sql
│       ├── mart_author_fingerprint.sql       # WIDE: 15 metrics pivoted, for BI
│       └── _marts.yml           # generic tests (exposure: week 3)
├── macros/
│   └── zscore.sql               # normalize a metric across the corpus
└── tests/
    └── assert_work_has_all_metric_concepts.sql   # singular: 14 concepts/work
```

**Materializations:** `staging` → views; `marts` → tables. Skip `incremental` — your corpus is static; note _why_ you'd use it (append-only event data) so you understand the tradeoff.

---

## 5. dbt Concepts This Hits (your learning checklist)

- [x] `sources` + `staging` convention (raw → `stg_`)
- [x] `ref` / `source` DAG and `dbt docs generate` → **lineage graph** (you like these)
- [x] **Seeds** — `dim_metric` and author metadata as version-controlled CSVs (textbook use case)
- [x] **Generic tests** — `not_null`, `unique`, `accepted_values`, `relationships` (author↔work FK)
- [x] **Singular/custom test** — every work carries all 14 per-work concepts; values range-tested
- [x] **Macros + Jinja** — the `zscore` macro applied across metrics (pivot for the wide mart: week 3)
- [x] **Packages** — `dbt_utils` for `pivot` and `generate_surrogate_key` (also the portability win, §7)
- [ ] **Exposures** — declare the dashboard so it shows in lineage
- [x] **Materializations** — view vs table, and reasoning about incremental

**Example: the z-score macro** (the "aha" moment for Jinja + cross-db SQL)

```sql
-- macros/zscore.sql
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif(stddev_pop({{ value_col }}) over (partition by {{ partition_col }}), 0)
{% endmacro %}
```

**As built:** uses `stddev_pop` (divide by N), not sample `stddev` (divide by N-1), because the 51 works ARE the whole corpus, not a sample of a larger population, so the population spread is the honest one. Called in `int_measurements_normalized.sql` as `{{ zscore('value', 'metric_name') }}`, partitioned by the **child** series name (the 63 measured `funcword_*` / `punct_*` / `senttype_*` / single-value names), NOT the 15 concept keys, so each series gets its own mean/spread. Children bridge to their `dim_metric` concept row by prefix via a LEFT join, so an unmapped prefix surfaces as a NULL `metric_key` that a `not_null` test catches instead of a silently dropped row. Window functions exist in both DuckDB and Fabric → portable.

---

## 6. BI Layer (pick one)

| Option           | Why                                                                    | Tradeoff                   |
| ---------------- | ---------------------------------------------------------------------- | -------------------------- |
| **Evidence.dev** | BI-as-code: SQL + markdown, git-versioned, reads DuckDB. LLM-friendly. | New tool to learn          |
| **Power BI**     | You already know it; marketable; mirrors the company stack             | DuckDB→Power BI is awkward |

Lean **Evidence.dev** — it's the analytics-engineering BI idiom and pairs natively with dbt+DuckDB.

---

## 7. Portability Rules (the "to Fabric, not in Fabric" crux)

1. **Dual target in `profiles.yml`.** Develop on `duckdb`; later add a `fabric` target. Same models.
    
    ```yaml
    prose_fingerprint:  target: duckdb  outputs:    duckdb:      type: duckdb      path: warehouse.duckdb    fabric:                       # add later — no model changes      type: fabric      driver: "ODBC Driver 18 for SQL Server"      # server / database / auth ...
    ```
    
2. **Push messy work upstream.** Regex, list ops, tokenizing → Python, never dbt SQL.
3. **Use `dbt_utils` cross-db macros** (`pivot`, `generate_surrogate_key`, `datediff`) instead of engine-specific syntax. They compile per-adapter — this _is_ the portability lesson.
4. **Standard types only** — `varchar`, `int`, `double`/`decimal`. No DuckDB-only types.
5. **No hardcoded `database.schema`** — let `profiles.yml` resolve it.
6. **Heads-up for the eventual Fabric swap:** target the **Warehouse** adapter — it's supported in dbt job in Fabric today; the Lakehouse adapter was still "coming soon" as of early 2026.

---

## 8. Three-Week Plan (evenings/weekends realistic)

### Week 1 — Environment + Extract/Load ✓ complete

- Install `dbt-core` + `dbt-duckdb` + `dbt_utils`; `dbt init prose_fingerprint`; `dbt debug` green.
- Python extractor: segmentation, tokenization, dialogue detection, 14 per-work metrics + Jaccard vocabulary.
- Land three `raw` tables: `raw_works (work_id, word_count)`, `raw_measurements (work_id, metric, value)`, `raw_vocab (work_id, term, term_count)`.
- Seeds in (`seed_authors`, `seed_metrics`); `stg_*` views compile; first `dbt run`.
- **Done when:** raw data lands and staging models build clean.

### Week 2 — Model + Test ✓ complete (2026-06-25)

- Build `dim_*` and `fact_*` (star schema); `int_measurements_normalized` (z-scores via macro); `int_vocab_jaccard`.
- Add tests: FK `relationships`, `not_null`, the singular completeness test (every work carries all 14 per-work concepts) + range tests.
- `dbt docs generate` → study the lineage graph.
- **Done when:** marts are trustworthy and every test passes.

### Week 3 — Serve + Portability + Polish

- Build `mart_author_fingerprint` (wide pivot); stand up the BI dashboard (you vs Wagner × 15).
- Declare the `exposure`. Run the **portability audit**: dry-run a second target, lint marts for any engine-specific SQL that slipped in.
- README + push to GitHub (portfolio piece, alongside `LeavesApp`).
- **Done when:** shippable artifact + a clean repo a hiring manager can read.

---

## 9. Why This Serves All Three Goals

- **Marketability:** a public, well-tested dbt repo with a real dimensional model (conformed dimensions, multiple fact grains), custom tests, macros, packages, and an exposure — the exact shape interviewers probe for.
- **LLM-readiness:** git-versioned SQL + YAML is maximally legible to Claude; the semantic/wide mart is a clean surface to point an agent at later.
- **Fabric path:** the dual-target design means "deploy to Fabric" later is a config add, and the whole thing becomes a ready-made company POC for dbt-in-Fabric.