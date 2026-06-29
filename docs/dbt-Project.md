# Project: prose-fingerprint

A dbt Core + DuckDB project that models stylometric "fingerprints": 15 style metrics measured across **135 works** (10 authors, ~3.66M words), normalized to z-scores, and served as an Evidence.dev dashboard comparing the author's own prose against nine studied authors (Wagner, Peake, Eddison, Vance, Clark Ashton Smith, Tolkien, Salvatore, Howard, Hodgson).

Built on DuckDB; designed to port to Microsoft Fabric with only a `profiles.yml` change.

---

## 1. Architecture (EL to T to BI)

```
┌─────────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ Python extractor│ → │ DuckDB (raw) │ → │ dbt (models)│ → │  Evidence.dev│
│ (reads texts,   │   │ landing zone │   │  the project│   │  you vs each │
│  emits metrics) │   │              │   │             │   │ author × 15  │
└─────────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
   the extract          the load            the transform        the serve
```

- **Extractor (Python, `extract/`):** reads corpus markdown, parses with spaCy (`en_core_web_sm`, NER disabled), emits **tidy rows**, lands three `raw` tables in DuckDB.
- **DuckDB:** single-file local warehouse, `prose_fingerprint/warehouse.duckdb`.
- **dbt Core:** staging to intermediate to marts. Everything below.
- **Evidence.dev:** BI-as-code, reads the same DuckDB file. See §6.

All messy text/regex/list work stays in Python, which keeps the dbt marts on standard SQL that ports cleanly to Fabric's T-SQL surface.

### 1.1 Extractor

Modules under `extract/`:

| Module            | Job                                                           |
| ----------------- | ------------------------------------------------------------- |
| `build_seed.py`   | scans `corpus/<Author>/*.md`, writes `seed_authors.csv`       |
| `extract.py`      | orchestration: manifest, clean, parse, land                   |
| `cleaning.py`     | markdown to plain prose (regex only; keeps prose punctuation) |
| `stylometrics.py` | the 14 per-work metric functions                              |
| `lexicons.py`     | tunable tables (function words, archaic list, punctuation)    |
| `vocab.py`        | metric 15's vocabulary emitter (content-word lemmas)          |
| `loaders.py`      | DuckDB landing: row shapes and the three `raw` table writers  |

**Metric contract:** each per-work metric is `(doc: Doc) -> dict[str, float]`. The driver flattens that dict to tidy rows, so a multi-value metric (function words, punctuation, sentence type) becomes N rows; its keys use `prefix_subkey` (`funcword_the`, `punct_semicolon`, `senttype_complex`). A "word" is a spaCy `is_alpha` token, the shared denominator throughout. Long novels are chunked under spaCy's 1M-char limit and stitched back with `Doc.from_docs`.

**Raw landing tables** (one parse per work feeds all three; each is `CREATE OR REPLACE` per run with a shared `loaded_at`):

| Table                  | Grain         | Columns                                      |
| ---------------------- | ------------- | -------------------------------------------- |
| `raw.raw_works`        | work          | `work_id`, `word_count`, `loaded_at`         |
| `raw.raw_measurements` | work × metric | `work_id`, `metric`, `value`, `loaded_at`    |
| `raw.raw_vocab`        | work × term   | `work_id`, `term`, `term_count`, `loaded_at` |

`seed_authors.csv` (`work_id`, `title`, `author`, `tradition`, `era`, `is_self`, `path`) doubles as both the extractor's manifest and a dbt seed, so the two halves cannot drift. `prose_type` is derived in `dim_work` from `word_count`.

**Corpus:** 135 works, 10 authors, ~3.66M words.

| Author               | Works | Tradition                         |
| -------------------- | ----- | --------------------------------- |
| Sander VanWilligen   | 26    | speculative fiction (`is_self`)   |
| Clark Ashton Smith   | 60    | weird fiction                     |
| Karl Edward Wagner   | 12    | sword & sorcery / dark fantasy    |
| Robert E. Howard     | 11    | sword & sorcery (Conan)           |
| William Hope Hodgson | 9     | weird / cosmic horror             |
| R. A. Salvatore      | 6     | heroic fantasy (Forgotten Realms) |
| J. R. R. Tolkien     | 4     | high fantasy                      |
| Jack Vance           | 4     | science fantasy (Dying Earth)     |
| Mervyn Peake         | 2     | gothic fantasy                    |
| E. R. Eddison        | 1     | heroic high fantasy               |

---

## 2. The 15 Metrics

| #   | Metric                       | Category    | Summary                                                          |
| --- | ---------------------------- | ----------- | ---------------------------------------------------------------- |
| 1   | Mean word length             | lexical     | Average characters per word; denser diction runs longer.         |
| 2   | Yule's K                     | lexical     | Vocabulary richness; higher = more repetition; length-stable.    |
| 3   | % archaic/rare words         | lexical     | Proportion matching a curated archaic/rare-word list.            |
| 4   | Honoré's R                   | lexical     | Hapax-based richness; higher = richer vocabulary; length-robust. |
| 5   | Function-word frequency      | lexical     | Per-word rate of each of 40 common function words.               |
| 6   | Mean sentence length         | syntactic   | Average words per sentence; a pacing proxy.                      |
| 7   | Sentence-length stdev        | syntactic   | Population spread of sentence length; rhythm "burstiness".       |
| 8   | Mean parse-tree depth        | syntactic   | Average grammatical nesting depth from the dependency parse.     |
| 9   | Sentence-type mix            | syntactic   | Shares of simple, compound, and complex sentences.               |
| 10  | Punctuation frequency        | mechanical  | Per-word rate of 9 punctuation groups.                           |
| 11  | Contraction rate             | mechanical  | Contractions per word; excludes the possessive `'s`.             |
| 12  | Dialogue : narration ratio   | structural  | Fraction of words inside double quotes.                          |
| 13  | Adjective density            | structural  | ADJ-tagged tokens as a fraction of all words.                    |
| 14  | Adverb density               | structural  | ADV-tagged tokens as a fraction of all words.                    |
| 15  | Jaccard vocab overlap vs you | distinctive | Shared-vocabulary fraction between an author and you.            |

The 15 concepts expand to **63 measured series**: 11 single-value metrics, plus the multi-value families (40 function words, 9 punctuation groups, 3 sentence types). Each series is normalized independently (§4).

### 2.1 Metric 15: Jaccard vocabulary overlap

Metric 15 compares two authors, so its grain and implementation differ from the other 14.

**Python emits a vocabulary, not a value.** `vocab.py` returns a work's content-word lemmas with their per-work counts (open-class POS, stopwords dropped, lemmatized and lowercased; proper nouns excluded so character names do not swamp the signal). These land as `raw.raw_vocab` rows, one per `(work_id, term, term_count)`. The count is unused by Jaccard (presence-based) but is kept for later frequency work.

**dbt computes the overlap** in `int_vocab_jaccard.sql`: pool each author's works into one distinct-term vocabulary, then measure every other author against you. Intersection is a join on `term`; union is `|A| + |B| - |A∩B|`. Pure joins and counts, so it ports to Fabric. A LEFT join keeps a zero-overlap author at `jaccard = 0` rather than dropping it. Output: 9 rows, one per other author.

---

## 3. Dimensional Model (Fact Constellation)

Three facts at different grains share **conformed dimensions** (`dim_author`, `dim_work`, `dim_metric`). `fact_style_measurement` is the primary fact; the other facts and marts sit beside it at grains it cannot hold.

The primary fact is **tall and narrow** (one row per work per metric series), so adding a metric needs no schema change, and it pivots cleanly for BI.

| Table                    | Grain          | Rows  | Key columns                                                                                 |
| ------------------------ | -------------- | ----- | ------------------------------------------------------------------------------------------- |
| `dim_author`             | author         | 10    | `author_key`, `name`, `tradition`, `era`, `is_self`                                         |
| `dim_work`               | work           | 135   | `work_key`, `author_key`, `work_id`, `title`, `word_count`, `prose_type`                    |
| `dim_metric`             | metric concept | 15    | `metric_key`, `metric_name`, `display_name`, `category`, `additivity`, ...                  |
| `fact_style_measurement` | work × series  | 8,505 | `measurement_key`, `work_key`, `author_key`, `metric_key`, `metric_name`, `value`, `zscore` |
| `fact_vocab_overlap`     | author pair    | 9     | `overlap_key`, `author_key_a` (you), `author_key_b`, `shared_terms`, `jaccard`              |
| `mart_style_long`        | work × series  | 8,505 | OBT: the fact denormalized against all dims, with `series_label`                            |
| `mart_work_fingerprint`  | work           | 135   | wide pivot: one z-score column per series (63)                                              |

- `is_self = true` on your author row makes "you vs everyone" a filter, not special-casing.
- `fact_style_measurement` carries `author_key` directly (off `dim_work`) so it slices by author without an extra hop. `metric_key` is concept-grain, so a multi-value concept's child series share one key; `metric_name` holds the child series name.
- `mart_style_long` is the flat serving layer for Evidence: pre-joined dims and a precomputed `series_label`, so the pages select and filter without re-joining the star.
- `mart_work_fingerprint` pivots z-scores wide via `dbt_utils.pivot` over the series list pulled with `get_column_values`.
- `dim_metric.additivity` records the Kimball additivity class. All 15 metrics are non-additive (ratios, averages, indices): `value` and `zscore` must never be summed across rows.

---

## 4. z-score Normalization (the macro)

Every measurement gets a z-score within its own series, so metrics on different scales become comparable (the standardized fingerprint form).

```sql
-- macros/zscore.sql
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif({{ stddev_pop_expr(value_col) }} over (partition by {{ partition_col }}), 0)
{% endmacro %}
```

- **Population stddev** (`stddev_pop`, divide by N), because the corpus is the whole population, not a sample.
- `nullif(..., 0)` guards a zero-spread series against divide-by-zero (yields NULL).
- `stddev_pop_expr` dispatches per engine via `adapter.dispatch`: `stddev_pop` on DuckDB, `stdevp` on Fabric.
- Called in `int_measurements_normalized.sql` partitioned by the **child** series name (the 63 series), so each series gets its own mean and spread. Each child bridges to its `dim_metric` concept by prefix in a LEFT join, so an unmapped prefix surfaces as a NULL `metric_key` that a `not_null` test catches instead of a silently dropped row.

---

## 5. dbt Project Layout

```
prose_fingerprint/
├── dbt_project.yml             # staging/intermediate → view, marts → table
├── packages.yml                # dbt_utils
├── profiles.yml                # duckdb target active; fabric stub commented
├── seeds/
│   ├── seed_authors.csv        # 135 works + author metadata (also the manifest)
│   └── seed_metrics.csv        # 15 metric definitions → dim_metric
├── models/
│   ├── staging/                # views
│   │   ├── _sources.yml        # the three raw tables
│   │   ├── stg_measurements.sql
│   │   ├── stg_works.sql
│   │   └── stg_vocab.sql
│   ├── intermediate/           # views
│   │   ├── _intermediate.yml
│   │   ├── int_measurements_normalized.sql   # z-scores via macro
│   │   └── int_vocab_jaccard.sql
│   └── marts/                  # tables
│       ├── dim_author.sql
│       ├── dim_work.sql
│       ├── dim_metric.sql
│       ├── fact_style_measurement.sql
│       ├── fact_vocab_overlap.sql
│       ├── mart_style_long.sql            # OBT for Evidence
│       ├── mart_work_fingerprint.sql      # wide z-score pivot
│       └── _marts.yml          # generic tests
├── macros/
│   └── zscore.sql              # per-series standardization, engine-dispatched
└── tests/
    └── assert_work_has_all_metric_concepts.sql   # singular: 14 concepts/work
```

**Materializations:** staging and intermediate are views; marts are tables. The corpus is static, so no incremental models. Seeds load with `+fast: false` (INSERT, not DuckDB's CWD-relative COPY).

---

## 6. BI Layer (Evidence.dev)

Lives in `reports/`, reads `warehouse.duckdb` directly. Pages:

| Page                  | Shows                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------- |
| `index.md`            | vocabulary overlap (Jaccard) and you-vs-chosen-author z-score comparison                |
| `authors/index.md`    | all authors: tradition, era, work count, word count                                     |
| `authors/[author].md` | author profile: signature metrics, sentence/punctuation/function-word breakdowns, works |
| `works/index.md`      | per-author box plot of book-to-book z-score spread, with the works list                 |
| `works/[work].md`     | one work: departure from its author's norm, and its z-score signature                   |

---

## 7. Portability (to Fabric, not in Fabric)

1. **Dual target in `profiles.yml`.** Develop on `duckdb`; a commented `fabric` target stub swaps in with no model changes.
2. **Messy work upstream.** Regex, list ops, tokenizing all live in Python, never in dbt SQL.
3. **`dbt_utils` cross-db macros** (`generate_surrogate_key`, `pivot`, `get_column_values`) compile per-adapter.
4. **Engine-dispatched SQL** where a function differs: the `zscore` macro picks `stddev_pop` vs `stdevp`.
5. **Standard types only** (`varchar`, `bigint`, `decimal`), no DuckDB-only types.
6. **No hardcoded `database.schema`**; `profiles.yml` resolves it. The eventual Fabric swap targets the Warehouse adapter.

---

## 8. dbt Features Exercised

- `sources` and `staging` convention (raw to `stg_`).
- `ref` / `source` DAG and `dbt docs generate` lineage.
- **Seeds:** metric definitions and author metadata as version-controlled CSVs.
- **Generic tests:** `unique`, `not_null`, `accepted_values`, `relationships` (FKs), `dbt_utils.accepted_range`, `dbt_utils.unique_combination_of_columns`.
- **Singular test:** every work carries all 14 per-work metric concepts.
- **Macros + Jinja:** the `zscore` macro with `adapter.dispatch`.
- **Packages:** `dbt_utils` for surrogate keys and pivot.
- **Materializations:** view (staging, intermediate) vs table (marts).
