"""
The two shopping list modes. A continuous list keeps what was bought under
"Recently bought" for a window of hours and then forgets it; a normal list
keeps every item but deletes itself once nobody has used it for the idle
days. A household's default list and a list a member chose to keep never
delete themselves, and 0 idle days turns self-deletion off.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta

from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.value_objects.enums import ShoppingListMode


def bought_cutoff(now: datetime, window_hours: int) -> datetime:
    """Items ticked before this moment have left "Recently bought"; a ticked
    item without a tick time counts as older."""
    return now - timedelta(hours=window_hours)


def self_deletes(shopping_list: ShoppingList, idle_days: int) -> bool:
    return (
        idle_days > 0
        and shopping_list.mode is ShoppingListMode.NORMAL
        and not shopping_list.keep
        and shopping_list.household_id is None
    )


def deletion_due_at(shopping_list: ShoppingList, idle_days: int) -> datetime | None:
    """When the list deletes itself if nobody uses it, or None if it never does."""
    if not self_deletes(shopping_list, idle_days):
        return None
    return shopping_list.last_activity_at + timedelta(days=idle_days)


def deletes_on(shopping_list: ShoppingList, idle_days: int) -> date | None:
    """The UTC day the list deletes itself on if nobody uses it until then."""
    due = deletion_due_at(shopping_list, idle_days)
    return due.date() if due is not None else None


def idle_cutoff(now: datetime, idle_days: int) -> datetime:
    """Normal lists last used before this moment are due for deletion."""
    return now - timedelta(days=idle_days)
