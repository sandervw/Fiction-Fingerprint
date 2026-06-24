# dbt Core reference

Local cheat-sheet so I don't re-fetch. Source: docs.getdbt.com (via Context7), fetched 2026-06-20. dbt is the "T" in ELT: it runs `select` statements as managed, tested, documented models. Verify version-specific syntax against live docs if something looks off.

---

## Project anatomy

```
project/
├── dbt_project.yml      # project config; names the profile to use
├── packages.yml         # external packages (e.g. dbt_utils); installed by `dbt deps`
├── profiles.yml         # connection/credentials; lives in ~/.dbt/ OR project root
├── seeds/               # CSVs loaded as tables by `dbt seed`
├── models/              # .sql (and .py) models + .yml property files
├── macros/              # reusable Jinja/SQL
├── tests/               # singular (custom) tests
└── snapshots/           # SCD type-2 (not used here)
```

`dbt_project.yml` links to a profile by name:

```yaml
name: 'prose_fingerprint'
profile: 'prose_fingerprint'   # must match a key in profiles.yml

models:
  prose_fingerprint:           # matches `name` above
    staging:
      +materialized: view
    marts:
      +materialized: table
```

`profiles.yml` holds the connection. Supports multiple named `outputs` (targets) under one profile; `target:` picks the default. This is the dual-target (duckdb now / fabric later) hook.

```yaml
prose_fingerprint:
  target: dev
  outputs:
    dev:
      type: postgres        # adapter-specific; see dbt-duckdb.md for duckdb
      schema: dbt_dev
      threads: 4
```

---

## Models

A model = one `.sql` file = one `select`. The filename is the relation name. Build with `dbt run`.

- **`ref('other_model')`** — reference another model. Builds the DAG and ensures correct build order. Always use instead of hardcoding table names.
- **`source('source_name', 'table_name')`** — reference raw tables declared in a `_sources.yml`. This is how Python-landed raw tables enter the DAG.

```sql
-- models/staging/stg_measurements.sql
select
    work_id,
    metric_name,
    cast(value as double) as value
from {{ source('raw', 'measurements') }}
```

Per-model config block (overrides project defaults):

```sql
{{ config(materialized='table', tags=['marts']) }}
select ...
```

### Materializations

| Type | What it builds | Use when |
|------|----------------|----------|
| `view` | a DB view, recomputed on read | staging / light transforms (default for our `staging/`) |
| `table` | a physical table, rebuilt each run | marts, anything queried often (our `marts/`) |
| `incremental` | table built once, then only new rows appended | append-only event data. **Not needed here** (static corpus); know it exists for the tradeoff |
| `ephemeral` | inlined as a CTE, no DB object | small reused logic you don't want materialized |

Incremental skeleton (reference only):

```sql
{{ config(materialized='incremental', unique_key='id') }}
select * from {{ ref('upstream') }}
{% if is_incremental() %}
  where loaded_at > (select max(loaded_at) from {{ this }})
{% endif %}
```

---

## Sources, seeds, properties (YAML)

One `version: 2` schema file describes sources, seeds, and model columns/tests/docs. Put near the models it covers.

```yaml
version: 2

sources:
  - name: raw                       # logical group; referenced as source('raw', ...)
    schema: raw                     # actual schema in the warehouse
    tables:
      - name: measurements
      - name: works

seeds:
  - name: seed_authors
    config:
      column_types:
        is_self: boolean

models:
  - name: stg_measurements
    description: "Cleaned tidy measurement rows."
    columns:
      - name: work_id
        data_tests:
          - not_null
```

**Seeds** = version-controlled CSVs in `seeds/`, loaded by `dbt seed`. Textbook use: small static reference data (our `dim_metric` definitions, author metadata). Not for large data.

---

## Tests

Two kinds. Recent dbt uses the key `data_tests:` (older `tests:` still works).

**Generic** (reusable, declared in YAML on a column):

```yaml
columns:
  - name: order_id
    data_tests:
      - unique
      - not_null
  - name: status
    data_tests:
      - accepted_values:
          arguments:            # `arguments:` wrapper is v1.10.5+; older = top-level
            values: ['placed', 'shipped', 'completed']
  - name: customer_id
    data_tests:
      - relationships:          # foreign-key check
          arguments:
            to: ref('customers')
            field: id
```

Four built-ins: `unique`, `not_null`, `accepted_values`, `relationships`. Add config like `severity: warn` or a `where:` filter under a `config:` block.

**Singular** (custom) — a `.sql` file in `tests/` that returns rows; any returned row = failure. This is how we'll assert "every work has exactly 15 metrics" and "values in range":

```sql
-- tests/assert_15_metrics_per_work.sql
select work_id, count(*) as n
from {{ ref('fact_style_measurement') }}
group by 1
having count(*) <> 15
```

---

## Macros + Jinja

Macros = reusable SQL templated with Jinja, in `macros/`. The z-score macro from the plan:

```sql
-- macros/zscore.sql
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif(stddev_pop({{ value_col }}) over (partition by {{ partition_col }}), 0)
{% endmacro %}
```

`stddev_pop` (divide by N), not `stddev`/`stddev_samp` (divide by N-1): our 51 works ARE the whole corpus, not a sample of a larger population, so the population stddev is the honest spread. Call inside a model: `{{ zscore('value', 'metric_name') }}` (partition by the measured child series). Window functions exist in both DuckDB and Fabric, so this stays portable.

---

## Packages

Declare in `packages.yml`, install with `dbt deps`:

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.0.0", "<2.0.0"]
```

`dbt_utils` gives cross-db macros that compile per-adapter (the portability win): `dbt_utils.pivot` (wide mart), `dbt_utils.generate_surrogate_key` (stable keys), `dbt_utils.star`, etc.

---

## Exposures

Declare downstream consumers (the BI dashboard) so they appear in lineage:

```yaml
exposures:
  - name: author_fingerprint_dashboard
    type: dashboard
    maturity: high
    url: http://localhost:3000
    depends_on:
      - ref('mart_author_fingerprint')
    owner:
      name: Sander
```

---

## CLI commands

| Command | Does |
|---------|------|
| `dbt debug` | check config + warehouse connection |
| `dbt deps` | install packages from packages.yml |
| `dbt seed` | load CSVs from seeds/ |
| `dbt run` | build models |
| `dbt test` | run tests |
| `dbt build` | seed + run + test + snapshot, in DAG order (preferred all-in-one) |
| `dbt docs generate` then `dbt docs serve` | build + view lineage graph |

Useful flags: `--select <model>` (run one model or a path/tag), `--select <model>+` (model + downstream), `--exclude`, `--full-refresh`, `--target <name>` (pick output, e.g. fabric).

Single model: `dbt run --select stg_measurements`. Single test: `dbt test --select stg_measurements`.
