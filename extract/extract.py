"""Prose-fingerprint extractor - the "EL" of the pipeline.

Per work: read the manifest, clean markdown to plain prose, parse it with
spaCy (chunked so long novels don't blow past spaCy's memory limit), and land
the results in DuckDB's `raw` schema. The row shapes and table-writing
functions live in loaders.py, the per-work metrics in stylometrics.py, and the
vocabulary emitter in vocab.py; this module is the orchestration tying them
together.

All labels (title, author, tradition...) live in corpus_manifest.csv and
become dbt seeds, so the raw tables carry only what needs the text.

Run from anywhere:  python extract/extract.py
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
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


# Parse long works in chunks below this many characters. Each chunk stays well
# under spaCy's 1M-char limit, so peak parser memory stays modest (~1GB/100k).
MAX_CHUNK_CHARS = 100_000

# Per-work metric functions currently implemented. Each takes the work Doc and
# returns {metric_name: value}; the driver below flattens those into tidy
# (work_id, metric, value) rows. Append new metrics here as they land.
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
    """The bits of a corpus_manifest.csv row the extractor needs."""

    work_id: str
    rel_path: str  # a .md file OR a folder of chapters, relative to repo root


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


def measure_metrics(work_id: str, doc: Doc) -> list[MeasurementRow]:
    """Run every implemented metric over one work's Doc into tidy rows.

    Each metric returns a {name: value} dict (one entry, or several for the
    multi-value metrics). We flatten those into one MeasurementRow per
    (work_id, metric, value).
    """
    rows: list[MeasurementRow] = []
    for metric_fn in METRIC_FUNCTIONS:
        for metric_name, value in metric_fn(doc).items():
            rows.append(MeasurementRow(work_id, metric_name, float(value)))
    return rows


def collect_vocab(work_id: str, doc: Doc) -> list[VocabRow]:
    """Turn one work's content-lemma counts into tidy raw_vocab rows.

    vocab_terms returns a {term: count} Counter; we emit one VocabRow per
    distinct term. dbt later pools these up to the author for metric 15.
    """
    return [VocabRow(work_id, term, count) for term, count in vocab_terms(doc).items()]


def measure_work(
    nlp: Language, work: Work, repo_root: Path
) -> tuple[WorkRow, list[MeasurementRow], list[VocabRow]]:
    """Read, clean, and parse one work into its work row, measurements, and vocab.

    The text is parsed once into a single work-level Doc; the word count, every
    metric, and the vocabulary all read off that same Doc, so the heavy parse
    happens once.
    """
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
    manifest_path = repo_root / "corpus_manifest.csv"
    db_path = repo_root / "prose_fingerprint" / "warehouse.duckdb"

    # Disable NER: none of the 15 metrics use named entities, and skipping it
    # speeds up the full parse. Chunking keeps each parse under the size limit.
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

    # duckdb connections are context managers, so the file is closed cleanly.
    with duckdb.connect(str(db_path)) as con:
        land_works(con, work_rows)
        land_measurements(con, measurement_rows)
        land_vocab(con, vocab_rows)

    total_words = sum(row.word_count for row in work_rows)
    print(
        f"Landed {len(work_rows)} works ({total_words:,} words); "
        f"{len(measurement_rows):,} rows into raw.raw_measurements "
        f"({len(METRIC_FUNCTIONS)} metrics); "
        f"{len(vocab_rows):,} rows into raw.raw_vocab."
    )


if __name__ == "__main__":
    main()
