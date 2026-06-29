"""Prose-fingerprint extractor - the "EL" of the pipeline.

Per work: read the manifest, clean markdown, parse with spaCy (chunked for long
novels), and land results in DuckDB's `raw` schema. Row shapes and table writers
live in loaders.py, per-work metrics in stylometrics.py, vocab in vocab.py; this
module orchestrates them. Labels live in the manifest as dbt seeds.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import spacy
from spacy.language import Language
from spacy.tokens import Doc

from cleaning import clean_markdown
from loaders import (
    MeasurementRow,
    VocabRow,
    WorkRow,
    land_measurements,
    land_vocab,
    land_works,
)
from stylometrics import (
    adjective_density,
    adverb_density,
    archaic_word_rate,
    contraction_rate,
    dialogue_narration_ratio,
    function_word_frequency,
    honore_r,
    mean_parse_tree_depth,
    mean_sentence_length,
    mean_word_length,
    punctuation_frequency,
    sentence_length_stdev,
    sentence_type_mix,
    yules_k,
)
from vocab import vocab_terms


# Chunk size for parsing long works, kept under spaCy's 1M-char limit.
MAX_CHUNK_CHARS = 100_000

# Per-work metrics; each takes the work Doc and returns {metric_name: value}.
# Append new metrics here as they land.
METRIC_FUNCTIONS = (
    mean_word_length,          # 1
    yules_k,                   # 2
    archaic_word_rate,         # 3
    honore_r,                  # 4
    function_word_frequency,   # 5  (multi-value)
    mean_sentence_length,      # 6
    sentence_length_stdev,     # 7
    mean_parse_tree_depth,     # 8
    sentence_type_mix,         # 9  (multi-value)
    punctuation_frequency,     # 10 (multi-value)
    contraction_rate,          # 11
    dialogue_narration_ratio,  # 12
    adjective_density,         # 13
    adverb_density,            # 14
)


# --- Manifest data shape --------------------------------------------------


@dataclass(frozen=True)
class Work:
    """The bits of a manifest row the extractor needs."""

    work_id: str
    rel_path: str  # relative to repo root


# --- Filesystem helpers ---------------------------------------------------


def find_repo_root() -> Path:
    """Repo root is one level up from this file."""
    return Path(__file__).resolve().parent.parent


def load_work_text(source: Path) -> str:
    """Return the full raw text of a work."""
    with source.open(encoding="utf-8") as handle:
        return handle.read()


# --- Parsing (clean -> chunk -> parse -> reassemble) ----------------------


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks below max_chars, breaking only on blank lines.

    Paragraph boundaries keep sentences whole, so per-chunk parses reassemble
    faithfully via Doc.from_docs.
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
        size += len(paragraph) + 2  # +2 for the "\n\n" rejoin
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def build_work_doc(nlp: Language, clean_text: str) -> Doc:
    """Parse a (possibly long) work into one Doc without hitting spaCy's
    memory wall: chunk, parse as a stream, then stitch back together."""
    chunks = chunk_text(clean_text, MAX_CHUNK_CHARS)
    docs = list(nlp.pipe(chunks, batch_size=8))
    return Doc.from_docs(docs)


# --- Manifest + measurement ----------------------------------------------


def read_manifest(manifest_path: Path) -> list[Work]:
    """Parse the manifest CSV into Work records."""
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [Work(work_id=row["work_id"], rel_path=row["path"]) for row in reader]


def measure_metrics(work_id: str, doc: Doc) -> list[MeasurementRow]:
    """Run every metric over one work's Doc, flattening each {name: value}
    dict into one MeasurementRow per (work_id, metric, value)."""
    rows: list[MeasurementRow] = []
    for metric_fn in METRIC_FUNCTIONS:
        for metric_name, value in metric_fn(doc).items():
            rows.append(MeasurementRow(work_id, metric_name, float(value)))
    return rows


def collect_vocab(work_id: str, doc: Doc) -> list[VocabRow]:
    """Turn one work's content-lemma counts into raw_vocab rows, one per
    distinct term. dbt later pools these up to the author for metric 15."""
    return [VocabRow(work_id, term, count) for term, count in vocab_terms(doc).items()]


def measure_work(
    nlp: Language, work: Work, repo_root: Path
) -> tuple[WorkRow, list[MeasurementRow], list[VocabRow]]:
    """Read, clean, and parse one work into its work row, measurements, and
    vocab. Parsed once into one Doc that everything downstream reads off."""
    source = repo_root / work.rel_path
    clean = clean_markdown(load_work_text(source))
    doc = build_work_doc(nlp, clean)
    word_count = sum(1 for token in doc if token.is_alpha)
    work_row = WorkRow(work_id=work.work_id, word_count=word_count)
    return (
        work_row,
        measure_metrics(work.work_id, doc),
        collect_vocab(work.work_id, doc),
    )


# --- Orchestration --------------------------------------------------------


def main() -> None:
    repo_root = find_repo_root()
    # The manifest IS the dbt seed, so extractor and dbt can never drift.
    manifest_path = repo_root / "prose_fingerprint" / "seeds" / "seed_authors.csv"
    db_path = repo_root / "prose_fingerprint" / "warehouse.duckdb"

    # Disable NER: no metric uses named entities, and skipping it speeds parsing.
    nlp = spacy.load("en_core_web_sm", disable=["ner"])
    works = read_manifest(manifest_path)

    # One parse per work yields its work row, measurement rows, and vocab rows.
    work_rows: list[WorkRow] = []
    measurement_rows: list[MeasurementRow] = []
    vocab_rows: list[VocabRow] = []
    for work in works:
        work_row, metric_rows, term_rows = measure_work(nlp, work, repo_root)
        work_rows.append(work_row)
        measurement_rows.extend(metric_rows)
        vocab_rows.extend(term_rows)

    # One batch timestamp shared by all three tables. Stored as naive UTC
    # wall-clock, since DuckDB shifts a tz-aware datetime to local time.
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)

    with duckdb.connect(str(db_path)) as con:
        land_works(con, work_rows, loaded_at)
        land_measurements(con, measurement_rows, loaded_at)
        land_vocab(con, vocab_rows, loaded_at)

    total_words = sum(row.word_count for row in work_rows)
    print(
        f"Landed {len(work_rows)} works ({total_words:,} words); "
        f"{len(measurement_rows):,} rows into raw.raw_measurements "
        f"({len(METRIC_FUNCTIONS)} metrics); "
        f"{len(vocab_rows):,} rows into raw.raw_vocab."
    )


if __name__ == "__main__":
    main()
