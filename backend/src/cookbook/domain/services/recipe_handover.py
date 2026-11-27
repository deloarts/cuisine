"""The visibility a recipe gets when a leaving user's recipe is handed over to
the owner of a recipe that uses it as a sub-recipe, or kept without an owner.

The handed-over recipe keeps every reader it still has and gains just the
readers of the recipes using it, judged by their visibility whether or not
they are published, so nobody reading a using recipe loses a sub-recipe
they could read before. The new owner reads it as its owner. Another using
recipe's owner becomes a shared user, a using recipe shared with users and
groups passes on those shares, and a household recipe passes on the members
of its owner's household. When the only readers to add are the new owner's
own household, the recipe becomes a household recipe; when a using recipe
is visible to every signed-in user (instance, peers or public), the recipe
becomes an instance recipe. It never becomes peers or public, since only an
owner decides to send a recipe to paired instances or publish it to the
internet; a peers or public recipe stays as it is. Otherwise the readers become
shares, and without any it stays private. The leaving user's own household
is gone with them, so a household visibility of the recipe itself adds
nobody.

The same rule applies to a recipe that stays without an owner because only
recipes staying online without one use it: those are visible to every
signed-in user, so it becomes an instance recipe too.
"""

from collections.abc import Iterable
from collections.abc import Set
from dataclasses import dataclass

from src.cookbook.domain.value_objects.enums import RecipeVisibility


@dataclass(frozen=True)
class Readers:
    """Who reads a recipe besides its owner, as its visibility says."""

    owner_id: int | None
    visibility: RecipeVisibility
    user_ids: frozenset[int]
    group_ids: frozenset[int]
    # The household of the owner, owner included; empty without one.
    household_ids: frozenset[int]


@dataclass(frozen=True)
class HandedOverVisibility:
    visibility: RecipeVisibility
    user_ids: frozenset[int]
    group_ids: frozenset[int]


def handed_over_visibility(
    recipe: Readers,
    using: Iterable[Readers],
    *,
    new_owner_id: int | None,
    new_owner_household: Set[int],
    leaving_id: int,
) -> HandedOverVisibility:
    """The narrowest visibility under which the new owner, everyone who
    still reads `recipe` and everyone who reads one of the `using` recipes
    can read the handed-over recipe."""
    if recipe.visibility in (
        RecipeVisibility.INSTANCE,
        RecipeVisibility.PEERS,
        RecipeVisibility.PUBLIC,
    ):
        return HandedOverVisibility(recipe.visibility, frozenset(), frozenset())
    users: set[int] = set()
    groups: set[int] = set()
    if recipe.visibility is RecipeVisibility.SHARED:
        users |= recipe.user_ids
        groups |= recipe.group_ids
    own_household = False
    for parent in using:
        if parent.owner_id is not None:
            users.add(parent.owner_id)
        match parent.visibility:
            case RecipeVisibility.INSTANCE | RecipeVisibility.PEERS | RecipeVisibility.PUBLIC:
                # Every member reads the using recipe; nobody beyond them
                # needs the handed-over one, so it never widens to peers
                # or public.
                return HandedOverVisibility(RecipeVisibility.INSTANCE, frozenset(), frozenset())
            case RecipeVisibility.SHARED:
                users |= parent.user_ids
                groups |= parent.group_ids
            case RecipeVisibility.HOUSEHOLD if parent.owner_id in new_owner_household:
                own_household = True
            case RecipeVisibility.HOUSEHOLD:
                users |= parent.household_ids
            case _:
                pass
    users.discard(leaving_id)
    household = set(new_owner_household) - {leaving_id}
    if new_owner_id is not None:
        users.discard(new_owner_id)
        household.discard(new_owner_id)
    if own_household:
        if not groups and users <= household:
            return HandedOverVisibility(RecipeVisibility.HOUSEHOLD, frozenset(), frozenset())
        users |= household
    if users or groups:
        return HandedOverVisibility(RecipeVisibility.SHARED, frozenset(users), frozenset(groups))
    return HandedOverVisibility(RecipeVisibility.PRIVATE, frozenset(), frozenset())
