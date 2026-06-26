# Evidence.dev reference

Local cheat-sheet. Source: evidence-dev/evidence (via Context7), fetched 2026-06-26. Evidence is "BI as code": reports are Markdown files with SQL inside, built into a static website. It's the dashboard layer that sits on top of our dbt marts.

---

## Mental model (coming from PowerBI / SQL Server)

| PowerBI | Evidence |
|---|---|
| `.pbix` canvas, drag visuals | `.md` files you type |
| DAX measures + data model | plain SQL queries |
| model relationships (`dim_id → fact_id`), auto cross-filter | **no relationships** — joins/filters written by hand in SQL |
| publish to Service | `npm run build` → static site |

There is **no semantic model**. Do the modeling upstream in dbt; Evidence just queries it.

---

## Project shape

```
sources/                 # one folder per data source
  warehouse/
    connection.yaml       # non-secret config (type, db file)
    connection.options.yaml  # secrets (gitignored) — not needed for local DuckDB
    some_query.sql        # optional source query
src/pages/               # the reports; folder structure = site URLs
  index.md
  authors/[author].md     # bracket = templated/dynamic page
```

Pages reference source data as `source_name.query_name` (or query a table directly).

---

## Scaffold + run

```bash
npx degit evidence-dev/template my-project   # download starter template
cd my-project
npm install
npm run sources    # build/cache data from sources
npm run dev        # dev server on localhost:3000
```

`npm run build` produces the static site. `npm run sources -- --changed` rebuilds only changed sources.

---

## Connecting to our DuckDB

DuckDB connection lives in `sources/<name>/connection.yaml`, `type: duckdb`, pointing at the warehouse file:

```yaml
name: warehouse
type: duckdb
# DuckDB file path option key — confirm exact name at install (filename/path)
```

> Evidence caches source results to parquet and runs page queries through its own embedded DuckDB. Confirm the exact filename key + whether to point at our existing `prose_fingerprint/warehouse.duckdb` when we wire it up.

---

## Pages = Markdown + components

A page is prose + fenced SQL blocks + component tags, all in one `.md`. Components are **Svelte** (same idea as MDX = Markdown + React); `<BarChart/>` is a component, not HTML.

````markdown
```sql author_lengths
select author, mean_word_length from mart_work_fingerprint
```

<BarChart data={author_lengths} x=author y=mean_word_length />
````

Named SQL block (`author_lengths`) → its result is the `data={...}` for any component below it.

---

## Filtering (the PowerBI cross-filter replacement)

No auto-propagation. Three mechanisms:

**1. Pre-joined marts.** Query a wide flat table (e.g. `mart_work_fingerprint`); joins already done in dbt.

**2. Inputs → WHERE clause.** An input captures a selection into `${inputs.<name>.value}`, interpolated into SQL:

````markdown
```sql authors
select distinct author from mart_work_fingerprint
```

<Dropdown data={authors} name=picked value=author />

```sql filtered
select * from mart_work_fingerprint
where author = '${inputs.picked.value}'
```
````

Multi-value: `where author in ${inputs.picked.value}` (no quotes).

**3. Query chaining.** Reference one query inside another with `${query_name}` to build reusable base queries, then filter downstream:

```sql
select * from ${author_lengths} where mean_word_length > 4
```

---

## Exposures (dbt link)

Once a dashboard exists, declare it as a dbt `exposure` so lineage knows the marts feed it. That's the planned Week-3 follow-up after the dashboard is up.

> Portability note: Evidence reads straight from the DuckDB file and is independent of the dbt engine — swapping dbt to Fabric later doesn't touch the Evidence layer, only the `connection.yaml`.
