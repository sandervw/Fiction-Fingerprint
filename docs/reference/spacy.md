# spaCy reference

Local cheat-sheet. Source: spacy.io (via Context7), fetched 2026-06-21. spaCy is the **Python extractor's** tool only; it never touches the dbt/Fabric side (see dbt-Project.md §7).

Installed: `spacy` 3.8.x + model `en_core_web_sm` 3.8.0. The small model ships a tagger, dependency parser, sentence segmenter, and NER. No word vectors (none of our 15 metrics need them).

---

## Install (uv)

```bash
uv add spacy
# pin the model as a tracked dependency so `uv sync` restores it on a clone:
uv add "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
```

The pin writes a `[tool.uv.sources]` entry in `pyproject.toml`. Plain `python -m spacy download en_core_web_sm` also works but is NOT tracked (lands only in `.venv`).

---

## Load and process

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("Autonomous cars shift liability toward manufacturers. They drive themselves.")
```

A `doc` is an iterable of `Token` objects, also sliceable into spans. Run the text through `nlp` once; every metric below reads off the same `doc`.

---

## What each metric reads

| Metric(s)                                  | spaCy surface                                  |
| ------------------------------------------ | ---------------------------------------------- |
| Mean / stdev sentence length, sentence-type| `doc.sents` (sentence iterator)                |
| Adjective density, adverb density          | `token.pos_` == `"ADJ"` / `"ADV"`              |
| Parse-tree depth                           | `token.head`, `token.children`, `token.dep_`   |
| Sentence-type mix                          | dependency labels (subordination/coordination) |
| Word counts, punctuation frequency         | `token.is_alpha`, `token.is_punct`             |

Yule's K, Honoré's R, function-word frequency, contraction rate, and Jaccard overlap are plain counting over tokens; no parser features required.

---

## Key Token attributes

| Attribute            | Meaning                                                        |
| -------------------- | ------------------------------------------------------------- |
| `token.text`         | the raw token string                                          |
| `token.pos_`         | coarse Universal POS tag (`ADJ`, `ADV`, `NOUN`, `VERB`, ...)  |
| `token.tag_`         | fine-grained POS tag                                          |
| `token.dep_`         | dependency relation label (string)                            |
| `token.head`         | syntactic parent token (ROOT's head is itself)               |
| `token.children`     | direct syntactic children                                     |
| `token.lefts` / `rights` | children before / after the token                        |
| `token.n_lefts` / `n_rights` | counts of those children                             |
| `token.subtree`      | the token plus all syntactic descendants                      |
| `token.is_alpha`     | True if all-alphabetic (use to count "words")                 |
| `token.is_punct`     | True if punctuation                                           |
| `token.is_sent_start`| True if the token begins a sentence                           |

---

## Sentence iteration

```python
for sent in doc.sents:
    n_words = sum(1 for t in sent if t.is_alpha)
```

Sentence boundaries come from the parser (`Token.is_sent_start`, surfaced as `Doc.sents`).

---

## Parse-tree depth

Walk each token up to ROOT, counting hops; the sentence's depth is the deepest token.

```python
def token_depth(token):
    depth = 0
    while token.head != token:      # ROOT is its own head
        token = token.head
        depth += 1
    return depth

sent_depth = max(token_depth(t) for t in sent)
```

---

## Sentence-type signals (heuristic)

No built-in "simple/compound/complex" label; derive it from dependency labels within a sentence:

- **Subordinate clause (complex):** a child with `dep_` in `{advcl, ccomp, xcomp, acl, relcl, csubj}`.
- **Coordinated clause (compound):** a `conj` linking two clause heads, usually with a `cc` (and/but/or).
- **Simple:** one clause, neither of the above.

Treat this as a best-effort classifier; document the rule in the extractor.
