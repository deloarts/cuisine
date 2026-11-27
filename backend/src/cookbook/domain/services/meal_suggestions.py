"""
Meal plan suggestions: which recipes are worth planning in a week, scored
from the cooking history of the plan's scope and re-ranked for variety.

The score is a sum of named signals, each between zero and its weight, so a
suggestion can always say which signal carried it. How often the scope cooked
a recipe counts on a log scale, so a single staple does not crowd out the
rest. A recipe becomes "due again" once the time since it was last cooked
outgrows its own usual interval. Favourites, recipes in season in the week's
month, recipes cooked around these dates in earlier years and, when a meal
is asked for, recipes whose meal tags fit it rise; a recipe cooked in the
last few days, one tagged only as a component (a sauce, a side, a drink) and
one that conflicts with the viewer's own food restrictions sink. Without
much history the remaining signals (favourites, the season, new recipes)
carry the list, and ties go to the newest recipe.

The re-ranking is maximal marginal relevance: the list is filled one recipe
at a time, each time with the candidate whose score minus its similarity to
the recipes already chosen is highest, so the top does not consist of five
variations of one dish. Similarity is a Jaccard index over tags and
ingredients, each weighted by how rare it is among the candidates, so salt
and onions make nothing similar.

Everything here is deterministic: the same history and cookbook give the
same list.
"""

import math
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import timedelta

from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import SuggestionReason

# ── Weights ──────────────────────────────────────────────────────────
# Every boost lies between zero and its weight. The weights are chosen so
# that the history signals lead (they are the household's own taste), the
# personal signals follow, and newness only decides among recipes nothing
# else speaks for.

# How often the scope cooked the recipe, on a log scale that reaches the
# full weight at AFFINITY_SATURATION times: the twentieth time adds far less
# than the second.
WEIGHT_OFTEN_COOKED = 1.0
AFFINITY_SATURATION = 20
# Grows from nothing once the recipe's usual interval has passed since it
# was last cooked, to the full weight at twice that interval. Slightly below
# affinity so a forgotten one-off does not outrank a regular that is due.
WEIGHT_DUE_AGAIN = 0.8
# The usual interval of a recipe cooked once is unknown; a month stands in.
# No interval counts as shorter than a week, since nobody plans the same
# dish twice a week on purpose.
SINGLE_COOK_INTERVAL_DAYS = 30
MIN_INTERVAL_DAYS = 7
# The viewer's own favourite: a deliberate choice, worth most of a signal.
WEIGHT_FAVOURITE = 0.6
# Cooked within ANNIVERSARY_WINDOW_DAYS of the week's dates in one of the
# last ANNIVERSARY_YEARS years; full weight from two such times on. As
# strong as a favourite, because seasonal habits (asparagus in May, goose in
# November) are what a household tends to forget to plan.
WEIGHT_THIS_TIME_LAST_YEAR = 0.6
ANNIVERSARY_YEARS = 5
ANNIVERSARY_WINDOW_DAYS = 7
ANNIVERSARY_FULL_COUNT = 2
# Every seasonal ingredient is in season in the week's month. Lighter than
# the history signals, since many recipes use no seasonal ingredient at all.
WEIGHT_IN_SEASON = 0.4
# The recipe's meal tags fit the asked meal; a mismatch (a dessert for
# dinner) sinks it by as much.
WEIGHT_FITS_SLOT = 0.5
SLOT_MISMATCH_PENALTY = 0.5
# Never cooked by the scope and published lately: fades to nothing over
# NEW_RECIPE_DAYS. The weakest boost, so it decides the cold start and the
# ties, not the list of a household with a history.
WEIGHT_NEW_RECIPE = 0.3
NEW_RECIPE_DAYS = 60

# Cooked in the last RECENT_DAYS days: larger than every boost together, so
# such a recipe only fills a list that would otherwise stay short.
RECENT_DAYS = 3
RECENT_PENALTY = 5.0
# Tagged only as a component of a meal, such as a sauce or a side dish.
COMPONENT_PENALTY = 1.0
# Conflicts with one of the viewer's own food restrictions.
WARNING_PENALTY = 1.0

# How much similarity to an already chosen recipe costs in the re-ranking:
# a near duplicate loses about one strong signal.
DIVERSITY_WEIGHT = 0.8
# The re-ranking looks at this many times the wanted number of the best
# scored candidates, which keeps it fast and the list relevant.
RERANK_POOL_FACTOR = 4

# A recipe cooked at least this often is "often cooked"; below that the
# label says it was cooked before.
OFTEN_COOKED_MIN = 3

# The seeded meal tags, by seed key, and the meals they fit. Tags people
# made themselves have no seed key and do not count.
MEAL_TAG_SLOTS: Mapping[str, frozenset[MealSlot]] = {
    "breakfast": frozenset({MealSlot.BREAKFAST}),
    "lunch": frozenset({MealSlot.LUNCH}),
    "dinner": frozenset({MealSlot.DINNER}),
    "snack": frozenset({MealSlot.SNACK}),
    "main_course": frozenset({MealSlot.LUNCH, MealSlot.DINNER}),
    "soup": frozenset({MealSlot.LUNCH, MealSlot.DINNER}),
    "salad": frozenset({MealSlot.LUNCH, MealSlot.DINNER}),
    "starter": frozenset({MealSlot.LUNCH, MealSlot.DINNER}),
    "dessert": frozenset({MealSlot.SNACK}),
    "baking": frozenset({MealSlot.BREAKFAST, MealSlot.SNACK}),
    "bread": frozenset({MealSlot.BREAKFAST, MealSlot.SNACK}),
    "spread": frozenset({MealSlot.BREAKFAST, MealSlot.SNACK}),
}
COMPONENT_TAGS = frozenset({"side_dish", "sauce_dip", "preserves", "drink"})

_WEIGHTS: Mapping[SuggestionReason, float] = {
    SuggestionReason.OFTEN_COOKED: WEIGHT_OFTEN_COOKED,
    SuggestionReason.NOT_COOKED_LATELY: WEIGHT_DUE_AGAIN,
    SuggestionReason.FAVOURITE: WEIGHT_FAVOURITE,
    SuggestionReason.COOKED_THIS_TIME_LAST_YEAR: WEIGHT_THIS_TIME_LAST_YEAR,
    SuggestionReason.IN_SEASON: WEIGHT_IN_SEASON,
    SuggestionReason.FITS_SLOT: WEIGHT_FITS_SLOT,
    SuggestionReason.NEW_RECIPE: WEIGHT_NEW_RECIPE,
}

# When two signals are equally strong, the more telling label wins.
_REASON_ORDER = (
    SuggestionReason.COOKED_THIS_TIME_LAST_YEAR,
    SuggestionReason.NOT_COOKED_LATELY,
    SuggestionReason.OFTEN_COOKED,
    SuggestionReason.FAVOURITE,
    SuggestionReason.IN_SEASON,
    SuggestionReason.FITS_SLOT,
    SuggestionReason.NEW_RECIPE,
)


@dataclass(frozen=True)
class CookHistory:
    """What the plan's scope cooked of one recipe."""

    times_cooked: int = 0
    first_cooked: date | None = None
    last_cooked: date | None = None
    # How often it was cooked near the planned week's dates in earlier years.
    around_this_time: int = 0


@dataclass(frozen=True)
class SuggestionCandidate:
    recipe_id: int
    # The day it was published (or created), for the newness boost and ties.
    published_on: date
    history: CookHistory = field(default_factory=CookHistory)
    is_favourite: bool = False
    in_season: bool = False
    has_warning: bool = False
    # The seed keys of its meal tags.
    meal_tag_keys: frozenset[str] = frozenset()
    # Tags and ingredients, as opaque keys, for the similarity.
    features: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Suggestion:
    recipe_id: int
    score: float
    reason: SuggestionReason


def anniversary_windows(date_from: date, date_to: date) -> list[tuple[date, date]]:
    """The planned range in each of the last ANNIVERSARY_YEARS years,
    widened by ANNIVERSARY_WINDOW_DAYS on both sides."""
    pad = timedelta(days=ANNIVERSARY_WINDOW_DAYS)
    return [
        (_years_back(date_from, years) - pad, _years_back(date_to, years) + pad)
        for years in range(1, ANNIVERSARY_YEARS + 1)
    ]


def _years_back(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February
        return day.replace(year=day.year - years, day=28)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def signals(
    candidate: SuggestionCandidate, *, today: date, slot: MealSlot | None = None
) -> tuple[dict[SuggestionReason, float], float]:
    """The boosts of a candidate by reason, and the sum of its penalties
    (zero or negative)."""
    history = candidate.history
    boosts: dict[SuggestionReason, float] = {}
    penalty = 0.0
    if history.times_cooked and history.last_cooked is not None:
        times = history.times_cooked
        boosts[SuggestionReason.OFTEN_COOKED] = WEIGHT_OFTEN_COOKED * _clamp(
            math.log1p(times) / math.log1p(AFFINITY_SATURATION)
        )
        since = max(0, (today - history.last_cooked).days)
        interval: float = SINGLE_COOK_INTERVAL_DAYS
        if times >= 2 and history.first_cooked is not None:
            interval = (history.last_cooked - history.first_cooked).days / (times - 1)
        interval = max(interval, MIN_INTERVAL_DAYS)
        boosts[SuggestionReason.NOT_COOKED_LATELY] = WEIGHT_DUE_AGAIN * _clamp(since / interval - 1)
        if since < RECENT_DAYS:
            penalty -= RECENT_PENALTY
    else:
        age = max(0, (today - candidate.published_on).days)
        boosts[SuggestionReason.NEW_RECIPE] = WEIGHT_NEW_RECIPE * _clamp(1 - age / NEW_RECIPE_DAYS)
    if history.around_this_time:
        boosts[SuggestionReason.COOKED_THIS_TIME_LAST_YEAR] = WEIGHT_THIS_TIME_LAST_YEAR * _clamp(
            history.around_this_time / ANNIVERSARY_FULL_COUNT
        )
    if candidate.is_favourite:
        boosts[SuggestionReason.FAVOURITE] = WEIGHT_FAVOURITE
    if candidate.in_season:
        boosts[SuggestionReason.IN_SEASON] = WEIGHT_IN_SEASON
    fitting = [MEAL_TAG_SLOTS[k] for k in candidate.meal_tag_keys if k in MEAL_TAG_SLOTS]
    if slot is not None and fitting:
        if any(slot in slots for slots in fitting):
            boosts[SuggestionReason.FITS_SLOT] = WEIGHT_FITS_SLOT
        else:
            penalty -= SLOT_MISMATCH_PENALTY
    if not fitting and candidate.meal_tag_keys & COMPONENT_TAGS:
        penalty -= COMPONENT_PENALTY
    if candidate.has_warning:
        penalty -= WARNING_PENALTY
    return boosts, penalty


def reason_of(boosts: Mapping[SuggestionReason, float], history: CookHistory) -> SuggestionReason:
    """The label of the strongest boost, measured against its own weight so
    a full "due again" beats a nearly full "often cooked". "Often cooked"
    needs OFTEN_COOKED_MIN times; without any boost the label says whether
    the scope cooked the recipe before."""
    shown = {
        reason: value / _WEIGHTS[reason]
        for reason, value in boosts.items()
        if value > 0
        and (
            reason is not SuggestionReason.OFTEN_COOKED or history.times_cooked >= OFTEN_COOKED_MIN
        )
    }
    if shown:
        return max(_REASON_ORDER, key=lambda r: (shown.get(r, 0.0), -_REASON_ORDER.index(r)))
    return (
        SuggestionReason.COOKED_BEFORE if history.times_cooked else SuggestionReason.NOT_COOKED_YET
    )


def score(
    candidate: SuggestionCandidate, *, today: date, slot: MealSlot | None = None
) -> Suggestion:
    boosts, penalty = signals(candidate, today=today, slot=slot)
    return Suggestion(
        recipe_id=candidate.recipe_id,
        score=sum(boosts.values()) + penalty,
        reason=reason_of(boosts, candidate.history),
    )


def feature_weights(candidates: Iterable[SuggestionCandidate]) -> dict[str, float]:
    """How rare each tag or ingredient is among the candidates: the inverse
    document frequency, smoothed so a key every candidate has weighs close
    to nothing but never less than zero."""
    pool = list(candidates)
    counts: dict[str, int] = {}
    for candidate in pool:
        for key in candidate.features:
            counts[key] = counts.get(key, 0) + 1
    total = len(pool)
    return {key: math.log((total + 1) / (count + 1)) for key, count in counts.items()}


def similarity(a: frozenset[str], b: frozenset[str], weights: Mapping[str, float]) -> float:
    """The weighted Jaccard index of two feature sets, from 0 to 1."""
    union = sum(weights.get(k, 0.0) for k in a | b)
    if union <= 0:
        return 0.0
    return sum(weights.get(k, 0.0) for k in a & b) / union


def rank(
    candidates: Iterable[SuggestionCandidate],
    *,
    today: date,
    limit: int,
    slot: MealSlot | None = None,
    excluded: Iterable[int] = (),
) -> list[Suggestion]:
    """The best `limit` candidates, varied, best first. Recipes in
    `excluded` (those already planned in the week) never appear."""
    skip = set(excluded)
    pool = [c for c in candidates if c.recipe_id not in skip]
    if limit <= 0 or not pool:
        return []
    weights = feature_weights(pool)
    scored = sorted(
        ((score(c, today=today, slot=slot), c) for c in pool),
        # Ties go to the newest: the later day, then the later id.
        key=lambda pair: (-pair[0].score, -pair[1].published_on.toordinal(), -pair[1].recipe_id),
    )
    remaining = scored[: max(limit * RERANK_POOL_FACTOR, limit)]
    chosen: list[tuple[Suggestion, SuggestionCandidate]] = []
    while remaining and len(chosen) < limit:
        best_index = 0
        best_value = -math.inf
        for index, (suggestion, candidate) in enumerate(remaining):
            closest = max(
                (similarity(candidate.features, c.features, weights) for _, c in chosen),
                default=0.0,
            )
            value = suggestion.score - DIVERSITY_WEIGHT * closest
            # Strictly greater keeps the earlier (better scored, newer) one on a tie.
            if value > best_value:
                best_index, best_value = index, value
        chosen.append(remaining.pop(best_index))
    return [suggestion for suggestion, _ in chosen]
