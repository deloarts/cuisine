"""
Comparing catalogue names. Ingredient and family main names and aliases form
one namespace per locale, compared without case, diacritics or extra spaces
(`name_key`). Near duplicates go further: simple plural endings fall away and
short names may differ by one letter, so "Erdäpfel" or "Erdapfl" find
"Erdapfel".
"""

import re
import unicodedata
from collections.abc import Iterable

_SPACE = re.compile(r"\s+")
# Longest first, so "-en" wins over "-n".
_GERMAN_ENDINGS = ("en", "n", "e", "s")
_ENGLISH_ENDINGS = ("es", "s")
_UMLAUTS = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})


def name_key(name: str) -> str:
    """Case-, diacritic- and whitespace-insensitive form of a name."""
    text = unicodedata.normalize("NFKD", name.strip().casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _SPACE.sub(" ", text)


def stems(name: str, locale: str) -> set[str]:
    """The name's key and its forms without one plural ending."""
    key = name_key(name.translate(_UMLAUTS) if locale.startswith("de") else name)
    forms = {key}
    endings = _GERMAN_ENDINGS if locale.startswith("de") else _ENGLISH_ENDINGS
    for ending in endings:
        if key.endswith(ending) and len(key) - len(ending) >= 3:
            forms.add(key[: -len(ending)])
    return forms


def _distance(a: str, b: str, limit: int) -> int:
    """Levenshtein distance, giving up above `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def is_near(a: str, b: str, locale: str) -> bool:
    """Whether two names probably mean the same food."""
    left, right = stems(a, locale), stems(b, locale)
    if left & right:
        return True
    shortest = min(len(name_key(a)), len(name_key(b)))
    if shortest < 4:
        return False
    limit = 1 if shortest <= 8 else 2
    return any(_distance(x, y, limit) <= limit for x in left for y in right)


_WORD = re.compile(r"[^\w]+")


def search_rank(names: Iterable[str], search: str) -> int:
    """How well an entry whose names (every name, plural and alias in every
    language) contain `search` matches it, lower first: 0 for a name equal
    to it, 1 for a name with it as a whole word ("schwarzer Pfeffer" for
    "Pfeffer"), 2 for a name starting with it ("Pfefferoni"), 3 for a word
    starting with it, 4 for any other match ("Kräutersalz" for "Salz")."""
    key = name_key(search)
    best = 4
    for name in names:
        candidate = name_key(name)
        if not candidate:
            continue
        if candidate == key:
            return 0
        words = [w for w in _WORD.split(candidate) if w]
        if key in words:
            best = min(best, 1)
        elif candidate.startswith(key):
            best = min(best, 2)
        elif any(w.startswith(key) for w in words):
            best = min(best, 3)
    return best
