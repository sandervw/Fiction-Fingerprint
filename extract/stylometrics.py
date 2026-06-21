"""Stylometric measurement functions for the prose-fingerprint extractor.

Contract: each per-work metric takes a parsed spaCy Doc and returns a
{metric_name: value} dict. Returning a dict (not a bare float) lets one
metric emit several values - e.g. the sentence-type mix returns three. The
extractor flattens these into tidy raw.raw_measurements rows
(work_id, metric, value), so a metric that yields N values becomes N rows.

These are PLACEHOLDERS: the signatures + docstrings are the contract; each
body lands one metric at a time in a later increment. The note after each
name points at the spaCy surface it will read (see docs/reference/spacy.md).
"""

from __future__ import annotations

from spacy.tokens import Doc


# --- Lexical --------------------------------------------------------------


def mean_word_length(doc: Doc) -> dict[str, float]:
    """Metric 1: mean characters per alphabetic token. (token.is_alpha, len)"""
    raise NotImplementedError("mean_word_length")


def yules_k(doc: Doc) -> dict[str, float]:
    """Metric 2: vocabulary richness, stable across text length. (token counts)"""
    raise NotImplementedError("yules_k")


def archaic_word_rate(doc: Doc) -> dict[str, float]:
    """Metric 3: share of tokens in an archaic/rare wordlist. (token.lower_)"""
    raise NotImplementedError("archaic_word_rate")


def honore_r(doc: Doc) -> dict[str, float]:
    """Metric 4: richness from hapax proportion. (token counts, hapaxes)"""
    raise NotImplementedError("honore_r")


def function_word_frequency(doc: Doc) -> dict[str, float]:
    """Metric 5: per-word rates of function words (the, of, and...). (token.lower_)

    Multi-value: one entry per tracked function word.
    """
    raise NotImplementedError("function_word_frequency")


# --- Syntactic ------------------------------------------------------------


def mean_sentence_length(doc: Doc) -> dict[str, float]:
    """Metric 6: mean words per sentence. (doc.sents, token.is_alpha)"""
    raise NotImplementedError("mean_sentence_length")


def sentence_length_stdev(doc: Doc) -> dict[str, float]:
    """Metric 7: stdev of sentence length (rhythm burstiness). (doc.sents)"""
    raise NotImplementedError("sentence_length_stdev")


def mean_parse_tree_depth(doc: Doc) -> dict[str, float]:
    """Metric 8: mean dependency-tree depth. (token.head walk to ROOT)"""
    raise NotImplementedError("mean_parse_tree_depth")


def sentence_type_mix(doc: Doc) -> dict[str, float]:
    """Metric 9: share of simple/compound/complex sentences. (dep_ labels)

    Multi-value: returns three entries (simple, compound, complex).
    """
    raise NotImplementedError("sentence_type_mix")


# --- Mechanical -----------------------------------------------------------


def punctuation_frequency(doc: Doc) -> dict[str, float]:
    """Metric 10: per-mark punctuation rates (; : , -- ...). (token.is_punct)

    Multi-value: one entry per punctuation mark.
    """
    raise NotImplementedError("punctuation_frequency")


def contraction_rate(doc: Doc) -> dict[str, float]:
    """Metric 11: frequency of contractions (don't, isn't). (token.text)"""
    raise NotImplementedError("contraction_rate")


# --- Structural -----------------------------------------------------------


def dialogue_narration_ratio(doc: Doc) -> dict[str, float]:
    """Metric 12: share of quoted speech vs narration. (quote spans)"""
    raise NotImplementedError("dialogue_narration_ratio")


def adjective_density(doc: Doc) -> dict[str, float]:
    """Metric 13: adjectives as a fraction of all words. (token.pos_ == ADJ)"""
    raise NotImplementedError("adjective_density")


def adverb_density(doc: Doc) -> dict[str, float]:
    """Metric 14: adverbs as a fraction of all words. (token.pos_ == ADV)"""
    raise NotImplementedError("adverb_density")


# --- Distinctive (cross-work - different grain) ---------------------------


def jaccard_vocab_overlap(tokens_a: set[str], tokens_b: set[str]) -> dict[str, float]:
    """Metric 15: shared-vocabulary fraction between two authors.

    NOT per-work: takes two vocab sets (an author vs you), so it lands in a
    separate raw_vocab table, not raw_measurements. Signature differs on
    purpose. Placeholder.
    """
    raise NotImplementedError("jaccard_vocab_overlap")
