"""The shopping list mode rules and the range check of their settings."""

from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta

import pytest

from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.services.shopping_modes import bought_cutoff
from src.cookbook.domain.services.shopping_modes import deletes_on
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.exceptions import InvalidSettingsError
from src.platform.domain.services.settings_rules import validate_shopping

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def _list(
    *,
    mode: ShoppingListMode = ShoppingListMode.NORMAL,
    keep: bool = False,
    household_id: int | None = None,
) -> ShoppingList:
    return ShoppingList(
        owner_id=1,
        name="Markt",
        created=NOW,
        changed=NOW,
        last_activity_at=NOW,
        mode=mode,
        keep=keep,
        household_id=household_id,
    )


def test_deletes_on_only_for_unkept_normal_lists_outside_a_household() -> None:
    assert deletes_on(_list(), 30) == date(2026, 12, 22)
    assert deletes_on(_list(), 0) is None
    assert deletes_on(_list(keep=True), 30) is None
    assert deletes_on(_list(mode=ShoppingListMode.CONTINUOUS), 30) is None
    assert deletes_on(_list(household_id=7), 30) is None


def test_the_bought_cutoff_is_the_window_before_now() -> None:
    assert bought_cutoff(NOW, 12) == NOW - timedelta(hours=12)


@pytest.mark.parametrize(("hours", "days"), [(0, 30), (721, 30), (12, -1), (12, 3651)])
def test_shopping_settings_out_of_range(hours: int, days: int) -> None:
    with pytest.raises(InvalidSettingsError):
        validate_shopping(ShoppingSettings(bought_window_hours=hours, idle_list_days=days))


def test_shopping_settings_defaults_are_valid() -> None:
    validate_shopping(ShoppingSettings())
    validate_shopping(ShoppingSettings(bought_window_hours=720, idle_list_days=0))
