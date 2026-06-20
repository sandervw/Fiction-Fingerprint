# DuckDB reference

Local cheat-sheet. Source: duckdb.org docs (via Context7), fetched 2026-06-20. DuckDB = in-process analytical SQL DB ("SQLite for analytics"). One file, no server. Two roles here: (1) Python API for the extractor to land rows, (2) SQL engine dbt compiles against.

---

## Python API (the extractor lands data here)

```python
import duckdb

# persistent file (created if missing); omit arg for in-memory
con = duckdb.connect("warehouse.duckdb")

con.sql("CREATE SCHEMA IF NOT EXISTS raw")
con.sql("CREATE TABLE raw.integers (i INTEGER)")
con.sql("INSERT INTO raw.integers VALUES (42)")
con.sql("SELECT * FROM raw.integers").show()
con.close()
```

`.sql()` returns a lazy relation (chainable, `.show()`/`.df()`/`.fetchall()` to materialize). `.execute()` runs a statement, supports parameters: `con.execute("... WHERE id = ?", [id])`.

### From pandas (main landing path)

DuckDB sees pandas DataFrames in local scope by name. No manual loading needed:

```python
import duckdb, pandas as pd

df = pd.DataFrame({'work_id': [1], 'metric': ['ttr'], 'value': [0.42]})

con = duckdb.connect("warehouse.duckdb")
# create a persistent table from the DataFrame
con.execute("CREATE TABLE raw.measurements AS SELECT * FROM df")
# or append to an existing table
con.execute("INSERT INTO raw.measurements SELECT * FROM df")
```

`con.register('name', df)` explicitly registers a DataFrame as a virtual table (useful when the variable isn't in scope or to control the name). Registered views are virtual; `CREATE TABLE AS` persists a copy.

---

## SQL essentials

DuckDB's dialect is Postgres-like with extras. Reminder: extras (list/regex/struct) are great but do NOT port to Fabric, so keep them in the extractor, not in dbt models.

### Read files directly

```sql
-- query files with no load step; schema auto-inferred
SELECT * FROM 'data/file.csv';
SELECT * FROM 'data/file.parquet';
SELECT * FROM read_csv('flights.csv', types={'FlightDate': 'DATE'});

CREATE TABLE ontime AS SELECT * FROM read_csv('flights.csv');   -- load into table
CREATE VIEW v AS SELECT * FROM 'orders.parquet';                -- view over file
```

### Tables, types, schemas

```sql
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE works (work_id INTEGER, title VARCHAR, year INTEGER, words BIGINT);
```

Portable types to prefer (exist in Fabric too): `INTEGER`, `BIGINT`, `DOUBLE`, `DECIMAL(p,s)`, `VARCHAR`, `BOOLEAN`, `DATE`. Avoid DuckDB-only types (`LIST`/`STRUCT`/`MAP`) in anything dbt models.

### Window + aggregate functions (portable, use freely in dbt)

```sql
avg(value)    over (partition by metric_key)
stddev(value) over (partition by metric_key)
row_number()  over (partition by author_key order by value desc)
```

Aggregates: `count`, `sum`, `avg`, `min`, `max`, `stddev`, plus `string_agg(x, ',')` and `list(x)` (last two are DuckDB-flavored).

### DuckDB-only niceties (extractor only, never in portable dbt models)

- `LIST` columns: `CREATE TABLE t (tags VARCHAR[])`
- String/regex: `regexp_matches`, `regexp_extract`, `string_split`, `len`, `lower`
- `FROM`-first syntax: `FROM tbl SELECT col` (DuckDB lets you omit leading SELECT)

---

## CLI (optional, for poking at the file)

```bash
duckdb warehouse.duckdb          # open a SQL shell against the file
```

Then `.tables`, `.schema`, `SELECT ...`, `.quit`.
