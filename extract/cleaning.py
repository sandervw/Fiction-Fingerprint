"""Markdown -> plain prose cleanup for the prose-fingerprint extractor.

Strips markdown syntax (frontmatter, headings, scene breaks, emphasis, links)
while leaving prose punctuation untouched, since it is measured downstream.
Rules apply in order: whole-line drops before inline emphasis.
"""

from __future__ import annotations

import re


# Leading YAML frontmatter block.
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# Source-attribution line on the raw public-domain dumps - never prose.
_SOURCE_LINE = re.compile(r"(?m)^[ \t]*\*{1,2}\s*Source:.*$")

# Emphasised, standalone byline at the top; \A anchor avoids mid-prose emphasis.
_LEADING_BYLINE = re.compile(r"\A(?:[ \t]*#[^\n]*\n)?\s*\*{1,2}[^*\n]+\*{1,2}[ \t]*\n")

# Whole lines to delete (heading / scene-break / horizontal rule).
_HEADING_LINE = re.compile(r"(?m)^[ \t]*#{1,6}[ \t].*$")
_RULE_LINE = re.compile(
    r"(?m)^[ \t]*(?:\*[ \t]*){3,}$"
    r"|^[ \t]*-{3,}[ \t]*$"
    r"|^[ \t]*_{3,}[ \t]*$"
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
    # Normalise line endings so line-anchored rules below are reliable.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    text = _FRONTMATTER.sub("", text)
    text = _SOURCE_LINE.sub("", text)
    text = _LEADING_BYLINE.sub("", text)
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
