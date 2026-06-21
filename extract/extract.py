"""Prose-fingerprint extractor - the "EL" of the pipeline.

Per work: read the manifest, clean markdown to plain prose, parse it with
spaCy (chunked so long novels don't blow past spaCy's memory limit), and land
results in DuckDB's `raw` schema:
  - raw.raw_works         one row per work: (work_id, word_count)
  - raw.raw_measurements  tidy (work_id, metric, value) - created here,
                          filled once the stylometrics functions land.

All labels (title, author, tradition...) live in corpus_manifest.csv and
become dbt seeds, so raw_works only carries what needs the text: word_count.

Run from anywhere:  python extract/extract.py
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb
import spacy
from duckdb import DuckDBPyConnection
from spacy.language import Language
from spacy.tokens import Doc

from cleaning import clean_markdown


# Parse long works in chunks below this many characters. Each chunk stays well
# under spaCy's 1M-char limit, so peak parser memory stays modest (~1GB/100k).
MAX_CHUNK_CHARS = 100_000


# --- Data shapes ----------------------------------------------------------
# Plain data containers use dataclasses (no behaviour, just typed fields).


@dataclass(frozen=True)
class Work:
    """The bits of a corpus_manifest.csv row the extractor needs."""

    work_id: str
    rel_path: str  # a .md file OR a folder of chapters, relative to repo root


@dataclass(frozen=True)
class WorkRow:
    """One measured work, ready to land in raw.raw_works."""

    work_id: str
    word_count: int


# --- Filesystem helpers ---------------------------------------------------


def find_repo_root() -> Path:
    """Repo root is one level up from this file (extract/extract.py)."""
    return Path(__file__).resolve().parent.parent


def chapter_sort_key(path: Path) -> tuple[int, str]:
    """Sort chapter files by their number, so Chapter-2 precedes Chapter-10.

    Plain alphabetical sorting would put "Chapter-10" before "Chapter-2"
    (because '1' < '2' as text). We pull the integer out and sort on that.
    """
    match = re.search(r"Chapter-(\d+)", path.name)
    number = int(match.group(1)) if match else 0
    return (number, path.name)


def load_work_text(source: Path) -> str:
    """Return the full raw text of a work.

    A work is either a single .md file or a folder of chapter .md files.
    For a folder we read every chapter in numeric order and join them into
    one string, so the whole work is measured as a single unit.
    """
    if source.is_dir():
        chapters = sorted(source.glob("*.md"), key=chapter_sort_key)
        parts: list[str] = []
        for chapter in chapters:
            with chapter.open(encoding="utf-8") as handle:
                parts.append(handle.read())
        return "\n\n".join(parts)

    with source.open(encoding="utf-8") as handle:
        return handle.read()


# --- Parsing (clean -> chunk -> parse -> reassemble) ----------------------


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks below max_chars, breaking only on blank lines.

    Breaking on paragraph boundaries means a sentence is never cut in half, so
    the per-chunk parses reassemble (via Doc.from_docs) into a faithful whole.
    """
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        # Start a new chunk once the running one would exceed the limit.
        if current and size + len(paragraph) > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            size = 0
        current.append(paragraph)
        size += len(paragraph) + 2  # +2 accounts for the "\n\n" rejoin
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def build_work_doc(nlp: Language, clean_text: str) -> Doc:
    """Parse a (possibly long) work without hitting spaCy's memory wall.

    Chunk the text under spaCy's limit, parse the chunks as a stream, then
    stitch them back into one Doc. Every metric later reads off this one Doc.
    """
    chunks = chunk_text(clean_text, MAX_CHUNK_CHARS)
    docs = list(nlp.pipe(chunks, batch_size=8))
    return Doc.from_docs(docs)


# --- Manifest + measurement ----------------------------------------------


def read_manifest(manifest_path: Path) -> list[Work]:
    """Parse corpus_manifest.csv into Work records (ignores unused columns)."""
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [Work(work_id=row["work_id"], rel_path=row["path"]) for row in reader]


def measure_work(nlp: Language, work: Work, repo_root: Path) -> WorkRow:
    """Read, clean, and parse one work, then derive its raw.raw_works row."""
    source = repo_root / work.rel_path
    clean = clean_markdown(load_work_text(source))
    doc = build_work_doc(nlp, clean)
    word_count = sum(1 for token in doc if token.is_alpha)
    return WorkRow(work_id=work.work_id, word_count=word_count)


# --- Load into DuckDB -----------------------------------------------------


def land_works(con: DuckDBPyConnection, rows: Sequence[WorkRow]) -> None:
    """Create (or replace) raw.raw_works and insert the measured rows.

    raw_works carries only what needs the text (word_count). Titles, authors
    and other labels stay in the manifest and arrive on the dbt side as seeds.
    CREATE OR REPLACE keeps re-runs idempotent; ? params keep inserts safe.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.raw_works (work_id VARCHAR, word_count BIGINT)"
    )
    con.executemany(
        "INSERT INTO raw.raw_works VALUES (?, ?)",
        [(row.work_id, row.word_count) for row in rows],
    )


def create_measurements_table(con: DuckDBPyConnection) -> None:
    """Create the empty tidy table the metrics increment will populate.

    Long/tidy shape - one row per (work, metric, value) - so adding a 16th
    metric never changes the schema and it pivots cleanly for BI. Left empty
    for now; filled once extract/stylometrics.py is implemented and wired in.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.raw_measurements ("
        " work_id VARCHAR, metric VARCHAR, value DOUBLE)"
    )


# --- Orchestration --------------------------------------------------------


def main() -> None:
    repo_root = find_repo_root()
    manifest_path = repo_root / "corpus_manifest.csv"
    db_path = repo_root / "prose_fingerprint" / "warehouse.duckdb"

    # Disable NER: none of the 15 metrics use named entities, and skipping it
    # speeds up the full parse. Chunking keeps each parse under the size limit.
    nlp = spacy.load("en_core_web_sm", disable=["ner"])
    works = read_manifest(manifest_path)
    rows = [measure_work(nlp, work, repo_root) for work in works]

    # duckdb connections are context managers, so the file is closed cleanly.
    with duckdb.connect(str(db_path)) as con:
        land_works(con, rows)
        create_measurements_table(con)

    total_words = sum(row.word_count for row in rows)
    print(
        f"Landed {len(rows)} works into raw.raw_works ({total_words:,} words); "
        "raw.raw_measurements created empty (awaiting metric implementations)."
    )


if __name__ == "__main__":
    main()
