# Project: prose-fingerprint

A 3-week dbt Core project that models stylometric measurements of studied authors (Wagner, Peake, Eddison, Vance, Clark Ashton Smith) against your own prose, served as a 15-metric comparison dashboard.

**Design constraint:** built locally, _portable to Fabric_, not _built in Fabric_. The swap to the `dbt-fabric` Warehouse adapter later should be a `profiles.yml`.

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

- **Extractor (Python):** library and metric TBD. Emits **tidy rows**, never wide tables — one row per `(work, metric, value)`. Lands them in DuckDB.
- **DuckDB:** zero-infra local warehouse — a single file, no server to run. Gentlest warehouse to start on (it's basically "SQLite for analytics"), and the `dbt-duckdb` adapter is first-rate.
- **dbt Core:** the part you're here to learn. Everything below.
- **BI:** see §6.

> **Keep all messy text/regex/list work in Python.** This is both good architecture _and_ the #1 portability rule — Fabric's T-SQL warehouse surface won't have DuckDB's string/list/regex niceties. dbt SQL stays joins, aggregations, and window functions that exist in both engines.

---

## 2. Dimensional Model (Fact Constellation)

Three fact tables sharing the same dimensions is a **fact constellation** (a.k.a. galaxy schema): multiple facts at different grains joined to **conformed dimensions** (`dim_author`, `dim_work`, `dim_metric`). `fact_style_measurement` is the **primary** fact; the other two exist only because they live at grains the primary fact can't hold (a pairwise comparison and a histogram).

The primary fact is deliberately **tall and narrow** — one row per work per metric — so adding a 16th metric needs no schema change, and it pivots cleanly for BI.

| Table                                     | Grain              | Key columns                                                     |
| ----------------------------------------- | ------------------ | --------------------------------------------------------------- |
| `dim_author`                              | one row per author | `author_key`, `name`, `tradition`, `era`, `is_self`             |
| `dim_work`                                | one row per work   | `work_key`, `author_key`, `title`, `year`, `word_count`, `type` |
| `dim_metric`                              | one row per metric | `metric_key`, `metric_name`, `category`, `unit`, `higher_is`    |
| `fact_style_measurement` _(primary)_      | work × metric      | `work_key`, `author_key`, `metric_key`, `value`, `z_score`      |
| `fact_vocab_overlap` _(secondary)_        | author pair        | `author_key_a`, `author_key_b`, `jaccard`, `shared_terms`       |
| `fact_sentence_length_bins` _(secondary)_ | work × bin         | `work_key`, `length_bin`, `sentence_count`                      |

`is_self = true` on your author row makes "you vs everyone" just a filter, not special-casing.

---

## 3. The 15 Metrics (so you're not guessing)

| #   | Metric                       | Category    | Notes                                   |
| --- | ---------------------------- | ----------- | --------------------------------------- |
| 1   | Type-token ratio             | lexical     | vocabulary richness                     |
| 2   | Hapax legomena rate          | lexical     | one-off words / total                   |
| 3   | Mean word length             | lexical     |                                         |
| 4   | % archaic/rare words         | lexical     | dictionary list; CAS & Eddison spike    |
| 5   | Latinate : Germanic ratio    | lexical     | CAS's "jeweled" register lives here     |
| 6   | Mean sentence length         | syntactic   |                                         |
| 7   | Sentence-length stdev        | syntactic   | burstiness — Peake runs long & variable |
| 8   | Commas per sentence          | syntactic   | subordination proxy                     |
| 9   | Mean parse-tree depth        | syntactic   | spaCy dependency depth                  |
| 10  | Flesch-Kincaid grade         | readability |                                         |
| 11  | Dialogue : narration ratio   | structural  | Vance high; Eddison low                 |
| 12  | Mean paragraph length        | structural  |                                         |
| 13  | Adjective density            | structural  |                                         |
| 14  | Adverb density               | structural  |                                         |
| 15  | Jaccard vocab overlap vs you | distinctive | drives `fact_vocab_overlap`             |

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
│       └── _marts.yml           # tests + exposure
└── macros/
    └── zscore.sql               # normalize a metric across the corpus
```

**Materializations:** `staging` → views; `marts` → tables. Skip `incremental` — your corpus is static; note _why_ you'd use it (append-only event data) so you understand the tradeoff.

---

## 5. dbt Concepts This Hits (your learning checklist)

- [ ] `sources` + `staging` convention (raw → `stg_`)
- [ ] `ref` / `source` DAG and `dbt docs generate` → **lineage graph** (you like these)
- [ ] **Seeds** — `dim_metric` and author metadata as version-controlled CSVs (textbook use case)
- [ ] **Generic tests** — `not_null`, `unique`, `accepted_values`, `relationships` (author↔work FK)
- [ ] **Singular/custom test** — assert every work has exactly 15 metrics; assert values in range
- [ ] **Macros + Jinja** — the `zscore` macro applied across metrics; a pivot for the wide mart
- [ ] **Packages** — `dbt_utils` for `pivot` and `generate_surrogate_key` (also the portability win, §7)
- [ ] **Exposures** — declare the dashboard so it shows in lineage
- [ ] **Materializations** — view vs table, and reasoning about incremental

**Example: the z-score macro** (the "aha" moment for Jinja + cross-db SQL)

```sql
-- macros/zscore.sql
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif(stddev({{ value_col }}) over (partition by {{ partition_col }}), 0)
{% endmacro %}
```

Used in `int_measurements_normalized.sql` to make 15 metrics on wildly different scales comparable on one radar chart. Window functions exist in both DuckDB and Fabric → portable.

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

### Week 1 — Environment + Extract/Load

- Install `dbt-core` + `dbt-duckdb`; `dbt init prose_fingerprint`; `dbt debug` green.
- Write the Python extractor: sentence seg, tokenization, dialogue detection, the 15 metric calcs.
- Land tidy `(work, metric, value)` rows + work metadata into DuckDB `raw` schema.
- Seeds in; `stg_*` views compile; first `dbt run`.
- **Done when:** raw data lands and staging models build clean.

### Week 2 — Model + Test

- Build `dim_*` and `fact_*` (star schema); `int_measurements_normalized` (z-scores via macro); `int_vocab_jaccard`.
- Add tests: FK `relationships`, `not_null`, the custom "15 metrics per work" + range tests.
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