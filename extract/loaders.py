"""DuckDB landing layer for the prose-fingerprint extractor.

The persistence half of the EL: the typed row shapes for each `raw` table and
the functions that (re)create those tables and insert the rows. Kept separate
from extract.py so orchestration/parsing stays free of I/O concerns (and each
module stays within the project's 300-line limit).

Tables, all in the `raw` schema:
  - raw_works         one row per work: (work_id, word_count)
  - raw_measurements  tidy (work_id, metric, value): the 14 per-work metrics
  - raw_vocab         tidy (work_id, term, term_count): each work's content-word
                      lemmas + per-work frequency, feeding metric 15 (Jaccard,
                      computed dbt-side)

Every table also carries a `loaded_at` batch timestamp (UTC, passed in by the
caller so all three share the exact same value). Because the extractor does a
full CREATE OR REPLACE each run, this is a load/batch stamp - "when this
snapshot landed" - not a preserved per-row first-insert date.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from duckdb import DuckDBPyConnection


# --- Row shapes -----------------------------------------------------------
# Plain data containers (no behaviour, just typed fields) mirroring each table.


@dataclass(frozen=True)
class WorkRow:
    """One measured work, ready to land in raw.raw_works."""

    work_id: str
    word_count: int


@dataclass(frozen=True)
class MeasurementRow:
    """One tidy measurement, ready to land in raw.raw_measurements."""

    work_id: str
    metric: str
    value: float


@dataclass(frozen=True)
class VocabRow:
    """One content lemma of a work + its per-work count, for raw.raw_vocab."""

    work_id: str
    term: str
    term_count: int


# --- Landing functions ----------------------------------------------------


def land_works(
    con: DuckDBPyConnection, rows: Sequence[WorkRow], loaded_at: datetime
) -> None:
    """Create (or replace) raw.raw_works and insert the measured rows.

    raw_works carries only what needs the text (word_count). Titles, authors
    and other labels stay in the manifest and arrive on the dbt side as seeds.
    CREATE OR REPLACE keeps re-runs idempotent; ? params keep inserts safe.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.raw_works ("
        " work_id VARCHAR, word_count BIGINT, loaded_at TIMESTAMP)"
    )
    con.executemany(
        "INSERT INTO raw.raw_works VALUES (?, ?, ?)",
        [(row.work_id, row.word_count, loaded_at) for row in rows],
    )


def land_measurements(
    con: DuckDBPyConnection, rows: Sequence[MeasurementRow], loaded_at: datetime
) -> None:
    """Create (or replace) raw.raw_measurements and insert the tidy rows.

    Long/tidy shape - one row per (work, metric, value) - so adding a 16th
    metric never changes the schema and it pivots cleanly for BI.
    CREATE OR REPLACE keeps re-runs idempotent; ? params keep inserts safe.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.raw_measurements ("
        " work_id VARCHAR, metric VARCHAR, value DOUBLE, loaded_at TIMESTAMP)"
    )
    if rows:
        con.executemany(
            "INSERT INTO raw.raw_measurements VALUES (?, ?, ?, ?)",
            [(row.work_id, row.metric, row.value, loaded_at) for row in rows],
        )


def land_vocab(
    con: DuckDBPyConnection, rows: Sequence[VocabRow], loaded_at: datetime
) -> None:
    """Create (or replace) raw.raw_vocab and insert the tidy term rows.

    Long/tidy shape - one row per (work, term) - holding each work's distinct
    content-word lemmas and how often each occurs. dbt pools these up to the
    author and computes metric 15's Jaccard overlap vs you as a portable
    set-join (presence only; term_count is there for future frequency work).
    CREATE OR REPLACE keeps re-runs idempotent; ? params keep inserts safe.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.raw_vocab ("
        " work_id VARCHAR, term VARCHAR, term_count BIGINT, loaded_at TIMESTAMP)"
    )
    if rows:
        con.executemany(
            "INSERT INTO raw.raw_vocab VALUES (?, ?, ?, ?)",
            [(row.work_id, row.term, row.term_count, loaded_at) for row in rows],
        )
