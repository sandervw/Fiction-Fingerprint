"""Stylometric measurement functions for the prose-fingerprint extractor.

Contract: each per-work metric takes a parsed spaCy Doc and returns a
{metric_name: value} dict. A dict (not a bare float) lets one metric emit
several values - the extractor flattens these into tidy raw.raw_measurements
rows (work_id, metric, value), so N values become N rows. Editable word/
punctuation tables live in lexicons.py; #15 (jaccard) is a cross-work
placeholder. spaCy surfaces: docs/reference/spacy.md.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter

from spacy.tokens import Doc, Span, Token

from lexicons import (
    ARCHAIC_WORDS,
    CLOSE_QUOTES,
    CONTRACTION_CLITICS,
    FUNCTION_WORDS,
    OPEN_QUOTES,
    PUNCTUATION_MARKS,
    STRAIGHT_QUOTES,
)


# Dependency labels marking a subordinate clause -> the sentence is "complex".
# Logic, not a tunable list, so it lives here. See docs/reference/spacy.md.
SUBORDINATE_DEPS: frozenset[str] = frozenset(
    {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj"}
)


# --- Shared helpers -------------------------------------------------------


def _alpha_word_count(doc: Doc) -> int:
    """Count word tokens (is_alpha) - the project-wide "word", as in word_count.

    The shared denominator for every density/rate below; punctuation, numbers,
    and symbols are not words.
    """
    return sum(1 for token in doc if token.is_alpha)


def _word_frequencies(doc: Doc) -> Counter[str]:
    """Frequency of each case-folded word type (is_alpha tokens, via lower_).

    "The" and "the" fold to one type. The distribution both richness metrics
    (Yule's K, Honoré's R) and the word-list metrics read.
    """
    return Counter(token.lower_ for token in doc if token.is_alpha)


# --- Lexical --------------------------------------------------------------


def mean_word_length(doc: Doc) -> dict[str, float]:
    """Metric 1: mean characters per word (is_alpha tokens; len = letters)."""
    lengths = [len(token.text) for token in doc if token.is_alpha]
    if not lengths:
        return {"mean_word_length": 0.0}
    return {"mean_word_length": sum(lengths) / len(lengths)}


def yules_k(doc: Doc) -> dict[str, float]:
    """Metric 2: Yule's K = 10^4 * (S2 - N) / N^2, length-stable richness.

    N = total words, S2 = sum of each type's squared frequency. Repetition
    raises K; varied vocabulary lowers it. Returns 0.0 for an empty doc.
    """
    counts = _word_frequencies(doc)
    total = sum(counts.values())  # N
    if total == 0:
        return {"yules_k": 0.0}
    sum_squares = sum(count * count for count in counts.values())  # S2
    k = 10_000 * (sum_squares - total) / (total * total)
    return {"yules_k": k}


def archaic_word_rate(doc: Doc) -> dict[str, float]:
    """Metric 3: share of words found in ARCHAIC_WORDS (curated, not exhaustive).

    Blunt, but separates "thee/thou/hath" authors from modern prose. 0.0 if none.
    """
    words = _alpha_word_count(doc)
    if words == 0:
        return {"archaic_word_rate": 0.0}
    counts = _word_frequencies(doc)
    archaic = sum(count for word, count in counts.items() if word in ARCHAIC_WORDS)
    return {"archaic_word_rate": archaic / words}


def honore_r(doc: Doc) -> dict[str, float]:
    """Metric 4: Honoré's R = 100 * ln(N) / (1 - V1/V), hapax-based richness.

    N = words, V = distinct words, V1 = hapaxes (used once); more once-only
    words -> larger R. 0.0 for no words or the all-hapax (zero-division) case.
    """
    counts = _word_frequencies(doc)
    total = sum(counts.values())  # N
    vocab_size = len(counts)  # V
    if total == 0 or vocab_size == 0:
        return {"honore_r": 0.0}
    hapaxes = sum(1 for count in counts.values() if count == 1)  # V1
    denominator = 1 - (hapaxes / vocab_size)
    if denominator == 0:
        return {"honore_r": 0.0}
    return {"honore_r": 100 * math.log(total) / denominator}


def function_word_frequency(doc: Doc) -> dict[str, float]:
    """Metric 5 (multi-value): per-word rate of each FUNCTION_WORDS entry.

    Keyed funcword_<word>; absent words still emit a 0.0 row so every work
    reports the same keys. All-zero for a doc with no words.
    """
    words = _alpha_word_count(doc)
    counts = _word_frequencies(doc)
    if words == 0:
        return {f"funcword_{word}": 0.0 for word in FUNCTION_WORDS}
    return {f"funcword_{word}": counts.get(word, 0) / words for word in FUNCTION_WORDS}


# --- Syntactic ------------------------------------------------------------


def mean_sentence_length(doc: Doc) -> dict[str, float]:
    """Metric 6: words (is_alpha) per sentence (doc.sents). 0.0 if no sentences."""
    sentence_count = sum(1 for _ in doc.sents)
    if sentence_count == 0:
        return {"mean_sentence_length": 0.0}
    return {"mean_sentence_length": _alpha_word_count(doc) / sentence_count}


def sentence_length_stdev(doc: Doc) -> dict[str, float]:
    """Metric 7: population stdev of sentence length in words - rhythm burstiness.

    Low = metronome; high = bursty (Peake). 0.0 with fewer than 2 sentences.
    """
    lengths = [sum(1 for token in sent if token.is_alpha) for sent in doc.sents]
    if len(lengths) < 2:
        return {"sentence_length_stdev": 0.0}
    return {"sentence_length_stdev": statistics.pstdev(lengths)}


def _token_depth(token: Token) -> int:
    """Hops from a token up to its sentence ROOT (ROOT = depth 0).

    Follow each token's head until a token is its own head (the ROOT marker).
    """
    depth = 0
    while token.head != token:
        token = token.head
        depth += 1
    return depth


def mean_parse_tree_depth(doc: Doc) -> dict[str, float]:
    """Metric 8: mean over sentences of the deepest token's distance to ROOT.

    Deeper = more clause-within-clause (hypotactic) prose. 0.0 if no sentences.
    """
    depths = [
        max((_token_depth(token) for token in sent), default=0)
        for sent in doc.sents
    ]
    if not depths:
        return {"mean_parse_tree_depth": 0.0}
    return {"mean_parse_tree_depth": sum(depths) / len(depths)}


def _classify_sentence(sent: Span) -> str:
    """Label a sentence simple/compound/complex from its dependencies.

    Priority: complex (SUBORDINATE_DEPS) > compound (VERB/AUX "conj" off ROOT) >
    simple; complex wins ties.
    """
    if any(token.dep_ in SUBORDINATE_DEPS for token in sent):
        return "complex"
    coordinated = any(
        token.dep_ == "conj"
        and token.head.dep_ == "ROOT"
        and token.pos_ in {"VERB", "AUX"}
        for token in sent
    )
    return "compound" if coordinated else "simple"


def sentence_type_mix(doc: Doc) -> dict[str, float]:
    """Metric 9 (multi-value): simple/compound/complex shares, keyed senttype_<kind>."""
    counts = {"simple": 0, "compound": 0, "complex": 0}
    for sent in doc.sents:
        counts[_classify_sentence(sent)] += 1
    total = sum(counts.values())
    if total == 0:
        return {f"senttype_{kind}": 0.0 for kind in counts}
    return {f"senttype_{kind}": count / total for kind, count in counts.items()}


# --- Mechanical -----------------------------------------------------------


def punctuation_frequency(doc: Doc) -> dict[str, float]:
    """Metric 10 (multi-value): per-word rate of each PUNCTUATION_MARKS group.

    Keyed punct_<name>, each group's occurrences over total words. Per word so
    it scales to "marks per 1000 words". All-zero for a doc with no words.
    """
    words = _alpha_word_count(doc)
    mark_counts = Counter(token.text for token in doc if token.is_punct)
    result: dict[str, float] = {}
    for name, marks in PUNCTUATION_MARKS.items():
        occurrences = sum(mark_counts.get(mark, 0) for mark in marks)
        result[f"punct_{name}"] = occurrences / words if words else 0.0
    return result


def contraction_rate(doc: Doc) -> dict[str, float]:
    """Metric 11: contractions per word.

    spaCy splits a contraction into a clitic ("n't", "'ve", ...); count those
    after normalising the smart apostrophe. "'s" counts only when not possessive
    (tag POS). 0.0 for a doc with no words.
    """
    words = _alpha_word_count(doc)
    if words == 0:
        return {"contraction_rate": 0.0}
    contractions = 0
    for token in doc:
        clitic = token.text.replace("’", "'").lower()
        if clitic in CONTRACTION_CLITICS:
            contractions += 1
        elif clitic == "'s" and token.tag_ != "POS":
            contractions += 1
    return {"contraction_rate": contractions / words}


# --- Structural -----------------------------------------------------------


def dialogue_narration_ratio(doc: Doc) -> dict[str, float]:
    """Metric 12: fraction of words inside double quotes.

    Sweep tokens flipping an "inside quote" switch (left smart-quote opens,
    right closes, straight quote toggles); words while on are dialogue. Value is
    dialogue / all words. Single quotes (apostrophes) ignored. 0.0 if no words.
    """
    total = 0
    dialogue = 0
    inside_quote = False
    for token in doc:
        text = token.text
        if text in OPEN_QUOTES:
            inside_quote = True
        elif text in CLOSE_QUOTES:
            inside_quote = False
        elif text in STRAIGHT_QUOTES:
            inside_quote = not inside_quote
        elif token.is_alpha:
            total += 1
            if inside_quote:
                dialogue += 1
    if total == 0:
        return {"dialogue_narration_ratio": 0.0}
    return {"dialogue_narration_ratio": dialogue / total}


def adjective_density(doc: Doc) -> dict[str, float]:
    """Metric 13: ADJ-tagged tokens as a fraction of all words. 0.0 if no words."""
    word_count = _alpha_word_count(doc)
    if word_count == 0:
        return {"adjective_density": 0.0}
    adjectives = sum(1 for token in doc if token.pos_ == "ADJ")
    return {"adjective_density": adjectives / word_count}


def adverb_density(doc: Doc) -> dict[str, float]:
    """Metric 14: ADV-tagged tokens as a fraction of all words. 0.0 if no words."""
    word_count = _alpha_word_count(doc)
    if word_count == 0:
        return {"adverb_density": 0.0}
    adverbs = sum(1 for token in doc if token.pos_ == "ADV")
    return {"adverb_density": adverbs / word_count}


# --- Distinctive (cross-work - different grain) ---------------------------


def jaccard_vocab_overlap(tokens_a: set[str], tokens_b: set[str]) -> dict[str, float]:
    """Metric 15: shared-vocabulary fraction between two authors.

    NOT per-work: takes two vocab sets (an author vs you), so it lands in a
    separate raw_vocab table, not raw_measurements. Placeholder.
    """
    raise NotImplementedError("jaccard_vocab_overlap")
