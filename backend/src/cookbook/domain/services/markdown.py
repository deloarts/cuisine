"""The plain text of the Markdown subset recipe text is written in (bold,
italic, bullet and numbered lists, hard line breaks), for places that show
or index text without formatting, such as list snippets."""

import re

from src.cookbook.domain.services.mentions import strip_mentions

_BOLD = re.compile(r"(\*\*|__)(.+?)\1", re.DOTALL)
_ITALIC = re.compile(r"(?<![\w*])([*_])(?!\s)(.+?)(?<!\s)\1(?![\w*])", re.DOTALL)
_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_BREAK = re.compile(r"(?:\\|  +)\n")
_SPACE = re.compile(r"\s+")


def plain_text(markdown: str) -> str:
    """The text without marks, on one line with single spaces."""
    text = _BREAK.sub("\n", strip_mentions(markdown))
    text = _LIST.sub("", text)
    text = _BOLD.sub(r"\2", text)
    text = _ITALIC.sub(r"\2", text)
    return _SPACE.sub(" ", text).strip()
