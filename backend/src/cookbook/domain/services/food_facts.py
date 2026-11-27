"""
Which food fact a day shows. The facts are numbered in a fixed order and day
`d` (its ordinal) shows fact `d * stride mod n`. A stride that shares no
factor with `n` walks through every fact once before any repeats, and a
stride near `n / 1.618` puts the facts of consecutive days far apart in the
order, so neighbouring facts about the same ingredient do not follow each
other. Everyone on the instance sees the same fact on the same day.
"""

from collections.abc import Iterator
from datetime import date
from math import gcd

GOLDEN = 0.6180339887


def stride(count: int) -> int:
    """The step through `count` facts: the first number from `count / 1.618`
    on that shares no factor with `count`."""
    step = max(1, round(count * GOLDEN))
    while gcd(step, count) != 1:
        step += 1
    return step


def daily_candidates(day: date, count: int) -> Iterator[int]:
    """The fact indexes to try on `day`, best first: the day's own fact,
    then the facts after it in the fixed order, for when the day's
    ingredient has left the catalogue. Yields nothing when there are no
    facts."""
    if count <= 0:
        return
    start = day.toordinal() * stride(count) % count
    for offset in range(count):
        yield (start + offset) % count
