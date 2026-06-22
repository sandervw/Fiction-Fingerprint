# LEarning Notes

*Claude, never touch this file unless I say to.*

## Setup

run `uv init --python 3.12 --no-workspace 2>&1`
- uv init = build new python proj w. Rust and python 3.12, in standalone workspace
- pyproject.toml is the package.json equivalent

run `uv add dbt-core dbt-duckdb 2>&1`
- records/installs the dependencies of dbt-core/duckdb in a virtual env and pins versions in uv.lock (like package-lock.json)

run `uv run dbt --version` (verify dbt runs in venv)

run `uv run dbt init prose_fingerprint`
- scaffolds the project (produced a standard dbt skeleton)
```
prose_fingerprint/
├── dbt_project.yml      # project config (name, paths, model defaults)
├── models/example/      # two throwaway sample models we'll delete
├── seeds/  macros/  tests/  snapshots/  analyses/   # empty dirs
└── .gitignore           # ignores target/, dbt_packages/, logs/
```

create profiles.yml in project root
- tells dbt which db to build for / target

## Viewing the data

`duckdb -ui prose_fingerprint/warehouse.duckdb`      # browser UI (object tree + grid)
`duckdb prose_fingerprint/warehouse.duckdb `         # SQL shell: .tables, SELECT ... LIMIT 10

## Design Decisions

Raw data is extracted from /corups via the /extracts python logic

Five python files:
- `cleaning.py` - "the wash/strainer station"; cleans the raw file text
- `extracts.py` - "the cook"; knows text and NLP; cleans, parses with spaCy; runs metrics, assembles types rows; the 'E' of ELT
- `lexicons.py` - "the reference charts"; a list of spice rack spices; holds data, not logic
- `loaders.py` - "the waiter"; knows the database; holds table shapes and create/insert; the 'L' of ELT
- `stylometrics.py` - "the measuring gear"; scales, calipers; reads numbers off the dish
- `vocab.py` - "the specific sampler/bagging appliance"; does one specific job for one metric

The cleansing/quality part of transformation lives in the python extract (cleaning.py)
- strips out markdown (keeps source files intact while cleaning up text for downstream)
- Flattens multi-value stylometric measures into single work-metric-value rows

Keep reference tables for list-based metrics (archaic words, function words, punctuation) in lexicons.py

Python creates a few 'raw' schema tables in duckdb
- raw_measurements (one row per work_id, metric, and value)
- raw_works (one row per work_id and wordcount)
- raw_vocab (one row per work per word)
  - USed to claculate vocab overlap between me and others authors (Jaccard)