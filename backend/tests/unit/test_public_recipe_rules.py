"""The anonymous visitor of the public pages as a case of `Viewer` and
`can_view_recipe`, the mention rewrite of the public presenter, and the
in-process rate limiter, without a database."""

from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_rules import can_delete_recipe
from src.cookbook.domain.services.recipe_rules import can_edit_recipe
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility as V
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.adapters.outbound.external.request_rate_limiter import InMemoryRequestRateLimiter
from src.platform.domain.value_objects.permission import Permission

NOW = datetime(2026, 11, 22, tzinfo=UTC)


def _recipe(visibility: V, *, status: RecipeStatus = RecipeStatus.PUBLISHED) -> Recipe:
    return Recipe(
        id=1,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        status=status,
        visibility=visibility,
        shared_user_ids=[0],
        shared_group_ids=[0],
        co_editor_ids=[0],
    )


@pytest.mark.parametrize("visibility", [V.PRIVATE, V.HOUSEHOLD, V.SHARED, V.INSTANCE])
def test_the_visitor_never_reads_a_recipe_below_public(visibility: V) -> None:
    visitor = Viewer.visitor(public_allowed=True)
    assert not can_view_recipe(visitor, _recipe(visibility))


def test_the_visitor_reads_published_public_recipes_only_while_allowed() -> None:
    assert can_view_recipe(Viewer.visitor(public_allowed=True), _recipe(V.PUBLIC))
    assert not can_view_recipe(Viewer.visitor(public_allowed=False), _recipe(V.PUBLIC))
    draft = _recipe(V.PUBLIC, status=RecipeStatus.DRAFT)
    assert not can_view_recipe(Viewer.visitor(public_allowed=True), draft)


def test_the_visitor_holds_no_identity_and_no_permission() -> None:
    visitor = Viewer.visitor(public_allowed=True)
    assert visitor.anonymous
    assert visitor.id == 0
    assert not visitor.user.is_active
    assert not any(visitor.user.has_permission(p) for p in Permission.ALL)
    # Not even an ownerless recipe or one that names id 0 somewhere opens to it.
    ownerless = _recipe(V.HOUSEHOLD)
    ownerless.owner_id = None
    assert not can_view_recipe(visitor, ownerless)
    public = _recipe(V.PUBLIC)
    assert not can_edit_recipe(visitor, public)
    assert not can_delete_recipe(visitor, public)


async def test_the_rate_limiter_counts_per_key_within_the_window() -> None:
    limiter = InMemoryRequestRateLimiter()
    assert [await limiter.hit("a", limit=2, window_seconds=60) for _ in range(2)] == [0, 0]
    assert await limiter.hit("a", limit=2, window_seconds=60) >= 1
    assert await limiter.hit("b", limit=2, window_seconds=60) == 0
    assert await limiter.hit("c", limit=1, window_seconds=0) == 0
    assert await limiter.hit("c", limit=1, window_seconds=0) == 0
