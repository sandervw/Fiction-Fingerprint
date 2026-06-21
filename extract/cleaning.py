"""Markdown -> plain prose cleanup for the prose-fingerprint extractor.

A separate quality step: strip markdown SYNTAX (frontmatter, headings, scene
breaks, emphasis, links) while leaving the author's PROSE and its punctuation
(em-dashes, smart quotes, apostrophes, interrupted-dialogue hyphens) untouched,
because that punctuation is itself measured downstream. One pure function, no
I/O. Rules are applied in order; order matters (whole-line drops before inline
emphasis), so each step is a separate, named regex.
"""

from __future__ import annotations

import re


# Leading YAML frontmatter block: ---\n ... \n---\n at the very start of file.
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# Whole lines to delete entirely (heading / scene-break / horizontal rule).
_HEADING_LINE = re.compile(r"(?m)^[ \t]*#{1,6}[ \t].*$")
_RULE_LINE = re.compile(
    r"(?m)^[ \t]*(?:\*[ \t]*){3,}$"  # * * *  or  ***
    r"|^[ \t]*-{3,}[ \t]*$"          # ---
    r"|^[ \t]*_{3,}[ \t]*$"          # ___
)

# Inline markers: strip the syntax, keep the words inside.
_BLOCKQUOTE = re.compile(r"(?m)^[ \t]*>[ \t]?")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BOLD_STAR = re.compile(r"\*\*([^*]+)\*\*")
_BOLD_US = re.compile(r"__([^_]+)__")
_ITALIC_STAR = re.compile(r"\*([^*\n]+)\*")
_ITALIC_US = re.compile(r"_([^_\n]+)_")
_INLINE_CODE = re.compile(r"`([^`]+)`")

# Collapse the blank-line gaps that deletions leave behind.
_EXTRA_BLANKS = re.compile(r"\n{3,}")


def clean_markdown(raw: str) -> str:
    """Reduce raw markdown to plain prose, leaving prose punctuation intact."""
    # Normalise line endings first so every line-anchored rule below is reliable.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    text = _FRONTMATTER.sub("", text)
    text = _HEADING_LINE.sub("", text)
    text = _RULE_LINE.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _IMAGE.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _BOLD_STAR.sub(r"\1", text)
    text = _BOLD_US.sub(r"\1", text)
    text = _ITALIC_STAR.sub(r"\1", text)
    text = _ITALIC_US.sub(r"\1", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _EXTRA_BLANKS.sub("\n\n", text)

    return text.strip()
