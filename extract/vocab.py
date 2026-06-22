"""Vocabulary extraction for the prose-fingerprint Jaccard overlap (metric 15).

Unlike the per-work *measurements* in stylometrics.py, this emits a per-work
*vocabulary*: the distinct content-word lemmas in a work, each with its count.
It is only the Python half of metric 15 - the Jaccard overlap itself is
computed dbt-side (int_vocab_jaccard.sql) as a portable set-join, not here.
Each term lands as one tidy raw.raw_vocab row (work_id, term, term_count); dbt
pools a work's rows up to its author and overlaps every author against you.
spaCy surfaces: docs/reference/spacy.md.
"""

from __future__ import annotations

from collections import Counter

from spacy.tokens import Doc


# Open-class ("content") POS tags: words that carry meaning, as opposed to
# function words (determiners, prepositions, pronouns, auxiliaries). PROPN is
# deliberately excluded - character/place names are trivially author-unique
# ("Gormenghast" is only ever Peake) and would swamp the shared-diction signal.
# Logic, not a tunable list, so it lives here (cf. SUBORDINATE_DEPS).
CONTENT_POS: frozenset[str] = frozenset({"NOUN", "VERB", "ADJ", "ADV"})


def vocab_terms(doc: Doc) -> Counter[str]:
    """Metric 15 (Python half): a work's content-word lemmas with their counts.

    A token qualifies when it is a word (is_alpha), is not a stopword (is_stop
    drops the everyone-shares-them function words), and is an open-class content
    word (CONTENT_POS). Lemmatised and lowercased, so "Journeys"/"journeyed"
    fold to one "journey". Returns a Counter (term -> per-work frequency): its
    keys are the distinct vocabulary the Jaccard overlap uses, the counts are
    there for future frequency work (TF-IDF, weighted overlap).
    """
    return Counter(
        token.lemma_.lower()
        for token in doc
        if token.is_alpha and not token.is_stop and token.pos_ in CONTENT_POS
    )
