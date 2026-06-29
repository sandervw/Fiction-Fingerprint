"""Vocabulary extraction for the prose-fingerprint Jaccard overlap (metric 15).

Emits a per-work vocabulary: the distinct content-word lemmas in a work, each
with its count. Only the Python half - the Jaccard overlap itself is computed
dbt-side. Each term lands as one raw.raw_vocab row.
"""

from __future__ import annotations

from collections import Counter

from spacy.tokens import Doc


# Open-class ("content") POS tags. PROPN is excluded: character/place names are
# trivially author-unique and would swamp the shared-diction signal.
CONTENT_POS: frozenset[str] = frozenset({"NOUN", "VERB", "ADJ", "ADV"})


def vocab_terms(doc: Doc) -> Counter[str]:
    """Metric 15 (Python half): a work's content-word lemmas with their counts.

    Keeps is_alpha, non-stopword, CONTENT_POS tokens, lemmatised and lowercased
    so "Journeys"/"journeyed" fold to one. Returns a {term: frequency} Counter.
    """
    return Counter(
        token.lemma_.lower()
        for token in doc
        if token.is_alpha and not token.is_stop and token.pos_ in CONTENT_POS
    )
