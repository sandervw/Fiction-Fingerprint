# Fiction-Fingerprint

Every writer has a fingerprint: habits of sentence length, punctuation, and word
choice they reach for without thinking. This project measures mine against ten
fantasy and weird-fiction authors I admire, and asks how close my prose actually
sits to theirs.

It is a **dbt Core + DuckDB** analytics project. The literary question is the
vehicle; the point is a clean, tested, dimensional warehouse served as a dashboard.

## What it does

1. A **Python + spaCy extractor** reads 137 works (mine plus ten studied authors,
   ~4.01M words) and emits 15 style metrics per work as tidy rows.
2. **dbt** shapes those rows into a star schema, normalizes every metric to a
   z-score (how many standard deviations a work sits from the corpus average), and
   computes vocabulary overlap between me and each author.
3. **Evidence.dev** serves it as a dashboard: pick an author, see where my prose
   runs heavier or lighter across each metric.

Think of the z-score as a tuning meter. Zero is the corpus average; positive means
I do more of something than the typical work, negative means less.

## The metrics

Fifteen stylometric measures across four families:

- **Lexical:** word length, Yule's K and Honoré's R (vocabulary richness), archaic
  diction, function-word rates.
- **Syntactic:** sentence length and its variation, parse-tree depth, sentence-type mix.
- **Mechanical:** punctuation rates, contractions.
- **Structural:** dialogue share, adjective and adverb density, vocabulary overlap.

## Stack

| Layer     | Tool                             |
| --------- | -------------------------------- |
| Extract   | Python, spaCy (`en_core_web_sm`) |
| Warehouse | DuckDB (single file)             |
| Transform | dbt Core + `dbt_utils`           |
| BI        | Evidence.dev                     |

The dbt models avoid engine-specific SQL, so the warehouse is designed to port to
Microsoft Fabric with only a `profiles.yml` change.

## Layout

```
corpus/             the source texts, by author
extract/            Python + spaCy extractor
prose_fingerprint/  the dbt project (models, seeds, macros, tests)
reports/            the Evidence.dev dashboard
docs/               design notes (see docs/dbt-Project.md)
```

## Running it

Python is managed with `uv`; dbt runs against the bundled DuckDB file.

```bash
uv run python extract/extract.py     # parse corpus, land raw tables
cd prose_fingerprint
dbt build                            # seeds, models, and tests
dbt docs generate && dbt docs serve  # the DAG
cd ../reports && npm run dev         # the dashboard
```

`docs/dbt-Project.md` has the full design: dimensional model, the z-score macro,
the metric definitions, and the portability rules.
