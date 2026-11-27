"""The meal plan's suggestion score and its variety re-ranking."""

from datetime import date
from datetime import timedelta

from src.cookbook.domain.services.meal_suggestions import RECENT_DAYS
from src.cookbook.domain.services.meal_suggestions import WEIGHT_FAVOURITE
from src.cookbook.domain.services.meal_suggestions import CookHistory
from src.cookbook.domain.services.meal_suggestions import SuggestionCandidate
from src.cookbook.domain.services.meal_suggestions import anniversary_windows
from src.cookbook.domain.services.meal_suggestions import feature_weights
from src.cookbook.domain.services.meal_suggestions import rank
from src.cookbook.domain.services.meal_suggestions import score
from src.cookbook.domain.services.meal_suggestions import signals
from src.cookbook.domain.services.meal_suggestions import similarity
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import SuggestionReason

TODAY = date(2026, 11, 25)
OLD = date(2024, 1, 1)


def _candidate(recipe_id: int, **extra: object) -> SuggestionCandidate:
    values: dict[str, object] = {"published_on": OLD, **extra}
    return SuggestionCandidate(recipe_id=recipe_id, **values)  # type: ignore[arg-type]


def _cooked(times: int, every_days: int, last_days_ago: int, around: int = 0) -> CookHistory:
    last = TODAY - timedelta(days=last_days_ago)
    return CookHistory(
        times_cooked=times,
        first_cooked=last - timedelta(days=every_days * (times - 1)),
        last_cooked=last,
        around_this_time=around,
    )


def test_affinity_is_log_scaled() -> None:
    def affinity(times: int) -> float:
        boosts, _ = signals(_candidate(1, history=_cooked(times, 30, 30)), today=TODAY)
        return boosts[SuggestionReason.OFTEN_COOKED]

    assert affinity(1) < affinity(2) < affinity(10) < affinity(20) == affinity(200)
    # The step from one to two is worth more than the one from ten to twenty.
    assert affinity(2) - affinity(1) > (affinity(20) - affinity(10)) / 2


def test_due_again_grows_with_the_recipes_own_interval() -> None:
    def due(every_days: int, last_days_ago: int) -> float:
        boosts, _ = signals(
            _candidate(1, history=_cooked(5, every_days, last_days_ago)), today=TODAY
        )
        return boosts[SuggestionReason.NOT_COOKED_LATELY]

    # A weekly dish not cooked for a week is not due yet, after two it is.
    assert due(7, 7) == 0
    assert due(7, 14) > 0
    assert due(7, 10) < due(7, 14)
    # Three weeks are long for a weekly dish but short for a monthly one.
    assert due(7, 21) > due(30, 21) == 0


def test_recently_cooked_sinks_below_everything_uncooked() -> None:
    recent = _candidate(
        1,
        history=_cooked(20, 7, RECENT_DAYS - 1, around=3),
        is_favourite=True,
        in_season=True,
        meal_tag_keys=frozenset({"dinner"}),
    )
    plain = _candidate(2)
    assert score(recent, today=TODAY, slot=MealSlot.DINNER).score < score(plain, today=TODAY).score
    later = _candidate(1, history=_cooked(20, 7, RECENT_DAYS))
    assert score(later, today=TODAY).score > 0


def test_favourite_season_and_last_year_add_up() -> None:
    plain = score(_candidate(1), today=TODAY).score
    favourite = score(_candidate(1, is_favourite=True), today=TODAY)
    assert favourite.score == plain + WEIGHT_FAVOURITE
    assert favourite.reason is SuggestionReason.FAVOURITE
    seasonal = score(_candidate(1, in_season=True), today=TODAY)
    assert seasonal.reason is SuggestionReason.IN_SEASON and seasonal.score > plain
    anniversary = score(_candidate(1, history=_cooked(1, 1, 365, around=2)), today=TODAY)
    assert anniversary.reason is SuggestionReason.COOKED_THIS_TIME_LAST_YEAR


def test_slot_fit_from_meal_tags() -> None:
    breakfast = _candidate(1, meal_tag_keys=frozenset({"breakfast"}))
    main = _candidate(2, meal_tag_keys=frozenset({"main_course"}))
    untagged = _candidate(3)
    assert (
        score(breakfast, today=TODAY, slot=MealSlot.BREAKFAST).reason is SuggestionReason.FITS_SLOT
    )
    assert (
        score(main, today=TODAY, slot=MealSlot.BREAKFAST).score
        < score(untagged, today=TODAY, slot=MealSlot.BREAKFAST).score
        < score(breakfast, today=TODAY, slot=MealSlot.BREAKFAST).score
    )
    # Without a slot the meal tags change nothing.
    assert score(main, today=TODAY).score == score(untagged, today=TODAY).score


def test_components_and_own_warnings_sink() -> None:
    plain = score(_candidate(1), today=TODAY).score
    assert score(_candidate(1, meal_tag_keys=frozenset({"sauce_dip"})), today=TODAY).score < plain
    # A side that is also tagged as a meal is a meal.
    assert (
        score(_candidate(1, meal_tag_keys=frozenset({"side_dish", "salad"})), today=TODAY).score
        == plain
    )
    assert score(_candidate(1, has_warning=True), today=TODAY).score < plain


def test_reason_labels() -> None:
    once = score(_candidate(1, history=_cooked(1, 1, 10)), today=TODAY)
    # Cooked once: not "often", and not due yet within a month.
    assert once.reason is SuggestionReason.COOKED_BEFORE
    often = score(_candidate(1, history=_cooked(12, 14, 14)), today=TODAY)
    assert often.reason is SuggestionReason.OFTEN_COOKED
    overdue = score(_candidate(1, history=_cooked(12, 7, 60)), today=TODAY)
    assert overdue.reason is SuggestionReason.NOT_COOKED_LATELY
    new = score(_candidate(1, published_on=TODAY - timedelta(days=3)), today=TODAY)
    assert new.reason is SuggestionReason.NEW_RECIPE
    assert score(_candidate(1), today=TODAY).reason is SuggestionReason.NOT_COOKED_YET


def test_cold_start_falls_back_to_favourites_season_and_newest() -> None:
    candidates = [
        _candidate(1),
        _candidate(2, published_on=TODAY - timedelta(days=40)),
        _candidate(3, published_on=TODAY - timedelta(days=2)),
        _candidate(4, in_season=True),
        _candidate(5, is_favourite=True),
    ]
    assert [s.recipe_id for s in rank(candidates, today=TODAY, limit=5)] == [5, 4, 3, 2, 1]


def test_ties_go_to_the_newest_and_are_deterministic() -> None:
    candidates = [_candidate(i, published_on=OLD + timedelta(days=i)) for i in range(1, 6)]
    first = rank(candidates, today=TODAY, limit=3)
    assert [s.recipe_id for s in first] == [5, 4, 3]
    assert rank(list(reversed(candidates)), today=TODAY, limit=3) == first


def test_planned_recipes_are_left_out() -> None:
    candidates = [_candidate(1, is_favourite=True), _candidate(2)]
    assert [s.recipe_id for s in rank(candidates, today=TODAY, limit=5, excluded=[1])] == [2]
    assert rank(candidates, today=TODAY, limit=0) == []


def test_rare_features_weigh_more() -> None:
    candidates = [
        _candidate(1, features=frozenset({"ingredient:salt", "ingredient:goose"})),
        _candidate(2, features=frozenset({"ingredient:salt", "ingredient:duck"})),
        _candidate(3, features=frozenset({"ingredient:salt"})),
    ]
    weights = feature_weights(candidates)
    assert weights["ingredient:goose"] > weights["ingredient:salt"] >= 0
    # Sharing only salt makes two recipes barely similar.
    assert similarity(candidates[0].features, candidates[1].features, weights) < 0.2
    assert similarity(candidates[0].features, candidates[0].features, weights) == 1
    assert similarity(frozenset(), frozenset(), weights) == 0


def test_variety_re_ranking_spreads_similar_recipes() -> None:
    pasta = frozenset({"tag:italian", "ingredient:pasta", "ingredient:tomato"})
    # Three pasta dishes score highest, a curry and a soup a little lower.
    candidates = [
        _candidate(1, is_favourite=True, in_season=True, features=pasta),
        _candidate(2, is_favourite=True, in_season=True, features=pasta),
        _candidate(3, is_favourite=True, in_season=True, features=pasta),
        _candidate(4, is_favourite=True, features=frozenset({"tag:indian", "ingredient:lentils"})),
        _candidate(5, is_favourite=True, features=frozenset({"tag:soup", "ingredient:pumpkin"})),
    ]
    top = [s.recipe_id for s in rank(candidates, today=TODAY, limit=3)]
    # Equal scores go to the later id, so the newest pasta leads.
    assert top[0] == 3
    assert set(top[1:]) == {4, 5}
    # The similar ones still come, after the varied ones.
    assert [s.recipe_id for s in rank(candidates, today=TODAY, limit=5)][3:] == [2, 1]


def test_anniversary_windows_cover_earlier_years() -> None:
    windows = anniversary_windows(date(2028, 2, 28), date(2028, 3, 5))
    assert len(windows) == 5
    assert windows[0] == (date(2027, 2, 21), date(2027, 3, 12))
    # 29 February falls back to the 28th in a common year.
    assert anniversary_windows(date(2028, 2, 29), date(2028, 2, 29))[0][0] == date(2027, 2, 21)
