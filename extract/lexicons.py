"""Tunable reference tables the stylometric metrics read.

Which function words to track, what counts as archaic, which punctuation marks to rate.
"""

from __future__ import annotations


# Metric 5 - function words tracked individually. Their rates are a fingerprint:
# authors reach for them unconsciously.
FUNCTION_WORDS: tuple[str, ...] = (
    "the", "of", "and", "a", "an", "to", "in", "that", "it", "is",
    "was", "for", "with", "as", "on", "at", "by", "be", "this", "had",
    "not", "but", "from", "or", "which", "they", "you", "his", "her", "their",
    "would", "there", "been", "when", "so", "if", "no", "all", "we", "he",
)

# Metric 3 - archaic / elevated diction (hand-picked, not exhaustive).
ARCHAIC_WORDS: frozenset[str] = frozenset({
    "thou", "thee", "thy", "thine", "ye", "thyself",
    "hath", "doth", "hast", "dost", "wast", "wert", "shalt", "wilt",
    "ere", "oft", "whilst", "amongst", "betwixt", "amidst", "unto", "upon",
    "hither", "thither", "whither", "hence", "thence", "whence", "yonder",
    "nigh", "naught", "aught", "wrought", "clad", "smote", "slew", "bade",
    "mayhap", "perchance", "verily", "forsooth", "anon", "wherefore",
    "methinks", "prithee", "lo", "behold", "nay", "yea", "spake", "wroth",
})

# Metric 10 - punctuation marks rated individually (count per word). Maps a
# metric subkey -> the token strings counting as that mark; dash and ellipsis
# fold their variants into one rate each. Keyed punct_<name>.
PUNCTUATION_MARKS: dict[str, frozenset[str]] = {
    "comma": frozenset({","}),
    "semicolon": frozenset({";"}),
    "colon": frozenset({":"}),
    "period": frozenset({"."}),
    "question": frozenset({"?"}),
    "exclamation": frozenset({"!"}),
    "dash": frozenset({"—", "–", "--"}),
    "ellipsis": frozenset({"…", "..."}),
    "parenthesis": frozenset({"(", ")"}),
}

# Metric 11 - contraction clitics. spaCy splits "don't" -> ["do", "n't"], so a
# contraction surfaces as one of these. "'s" is handled separately in code.
CONTRACTION_CLITICS: frozenset[str] = frozenset({
    "n't", "'re", "'ve", "'ll", "'m", "'d",
})

# Metric 12 - double-quote characters bounding dialogue. Smart quotes are
# directional; the straight quote is ambiguous, so the code toggles on it.
OPEN_QUOTES: frozenset[str] = frozenset({"“"})
CLOSE_QUOTES: frozenset[str] = frozenset({"”"})
STRAIGHT_QUOTES: frozenset[str] = frozenset({'"'})
