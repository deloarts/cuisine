"""
Mentions in step text: `@[Name](ingredient:<public id>)`,
`@[Name](recipe:<public id>)` and `@[Name](equipment:<public id>)`, written by
the editor's @ suggestions. Every mention must point at a line or an
equipment item of its own step; plain-text outputs reduce a mention to its
name. Agents may also write a mention by name (`NAMED_MENTION`), which
`resolve_named_mentions` turns into one by id before the step is saved.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

MENTION = re.compile(r"@\[([^\]\n]+)\]\((ingredient|recipe|equipment):([0-9A-Fa-f-]{36})\)")


@dataclass(frozen=True)
class Mention:
    name: str
    kind: Literal["ingredient", "recipe", "equipment"]
    public_id: str


def mentions(text: str) -> list[Mention]:
    return [
        Mention(m.group(1), m.group(2), m.group(3).lower())  # type: ignore[arg-type]
        for m in MENTION.finditer(text)
    ]


def strip_mentions(text: str) -> str:
    """The text with every mention reduced to its name."""
    return MENTION.sub(lambda m: m.group(1), text)


# A mention an agent writes without an id, `@[Zwiebeln](ingredient)` or
# `@[Topf](equipment)`, which names one of its step's own lines or items
# instead. A sub-recipe is always mentioned by its id.
NAMED_MENTION = re.compile(r"@\[([^\]\n]+)\]\((ingredient|equipment)\)")


@dataclass(frozen=True)
class MentionTarget:
    """A line or item of one step a named mention may point at: its kind,
    public id and every name it goes by (name, plural, aliases, the name the
    caller gave)."""

    kind: Literal["ingredient", "equipment"]
    public_id: str
    names: tuple[str, ...]


class UnresolvedMentionError(ValueError):
    """A named mention matches none, or more than one, of its step's lines."""

    def __init__(self, message: str, *, name: str, kind: str) -> None:
        super().__init__(message)
        self.name = name
        self.kind = kind


def resolve_named_mentions(
    text: str, targets: list[MentionTarget], key: Callable[[str], str]
) -> str:
    """The text with every named mention turned into a mention by id. A name
    matches a target of the same kind when one of its names has the same
    `key` (case, diacritics and spacing aside). Failing that, a name that
    ends one of a target's names or is a whole word of it counts ("flour"
    for "plain flour", "Zucker" for "Kristallzucker"), since a step's text
    names its ingredients the short way. Either way exactly one target of
    the step must match."""

    def ends_or_word(name: str, wanted: str) -> bool:
        candidate = key(name)
        return candidate.endswith(wanted) or wanted in candidate.split(" ")

    def replace(match: re.Match[str]) -> str:
        name, kind = match.group(1), match.group(2)
        wanted = key(name)
        same_kind = [t for t in targets if t.kind == kind]
        found = {t.public_id for t in same_kind if any(key(n) == wanted for n in t.names if n)}
        if not found and wanted:
            found = {
                t.public_id for t in same_kind if any(ends_or_word(n, wanted) for n in t.names if n)
            }
        if len(found) != 1:
            problem = "matches none" if not found else "matches more than one"
            raise UnresolvedMentionError(
                f"The mention @[{name}]({kind}) {problem} of the {kind} lines of its step.",
                name=name,
                kind=kind,
            )
        return f"@[{name}]({kind}:{found.pop()})"

    return NAMED_MENTION.sub(replace, text)
