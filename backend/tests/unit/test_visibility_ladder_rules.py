"""The visibility ladder: the public switch, the read-as-instance rule and the
lock modes, without a database."""

from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_handover import Readers
from src.cookbook.domain.services.recipe_handover import handed_over_visibility
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.recipe_rules import effective_visibility
from src.cookbook.domain.services.recipe_rules import narrower
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility as V
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PublicRecipesNotAllowedError
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.services.privacy_draft import privacy_mode_text
from src.platform.domain.services.settings_rules import validate_privacy

NOW = datetime(2026, 11, 22, tzinfo=UTC)


def _recipe(visibility: V, owner: int = 1, recipe_id: int = 1) -> Recipe:
    return Recipe(
        id=recipe_id,
        owner_id=owner,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        status=RecipeStatus.PUBLISHED,
        visibility=visibility,
    )


def test_the_ladder_runs_from_private_to_public() -> None:
    assert [v.value for v in V] == [
        "private",
        "household",
        "shared",
        "instance",
        "peers",
        "public",
    ]


def test_public_reads_as_instance_while_not_allowed() -> None:
    assert effective_visibility(V.PUBLIC, public_allowed=False) is V.INSTANCE
    assert effective_visibility(V.PUBLIC, public_allowed=True) is V.PUBLIC
    assert effective_visibility(V.SHARED, public_allowed=False) is V.SHARED
    settings = PrivacySettings()
    assert settings.effective_visibility("public") == "instance"
    settings.allow_public_recipes = True
    assert settings.effective_visibility("public") == "public"


def test_every_signed_in_viewer_reads_instance_and_public_recipes() -> None:
    reader = User(id=7, full_name="R", email="r@example.com", created=NOW, hashed_password="")
    viewer = Viewer(user=reader)
    assert can_view_recipe(viewer, _recipe(V.INSTANCE))
    assert can_view_recipe(viewer, _recipe(V.PUBLIC))


def test_an_instance_sub_recipe_of_a_public_one_is_narrower_only_while_allowed() -> None:
    parent, sub = _recipe(V.PUBLIC), _recipe(V.INSTANCE, recipe_id=2)
    assert narrower(sub, parent, public_allowed=True)
    assert not narrower(sub, parent, public_allowed=False)
    assert not narrower(parent, sub, public_allowed=True)
    assert not narrower(_recipe(V.PUBLIC, recipe_id=3), parent, public_allowed=True)


def test_handing_over_never_makes_a_recipe_public() -> None:
    def readers(visibility: V) -> Readers:
        return Readers(
            owner_id=2,
            visibility=visibility,
            user_ids=frozenset(),
            group_ids=frozenset(),
            household_ids=frozenset(),
        )

    private = Readers(1, V.PRIVATE, frozenset(), frozenset(), frozenset())
    widened = handed_over_visibility(
        private, [readers(V.PUBLIC)], new_owner_id=2, new_owner_household=set(), leaving_id=1
    )
    assert widened.visibility is V.INSTANCE
    public = Readers(1, V.PUBLIC, frozenset(), frozenset(), frozenset())
    kept = handed_over_visibility(
        public, [], new_owner_id=2, new_owner_household=set(), leaving_id=1
    )
    assert kept.visibility is V.PUBLIC


def test_lock_modes_follow_the_default_and_the_switch() -> None:
    assert privacy_mode_of(PrivacySettings()).mode is PrivacyMode.INSTANCE
    assert privacy_mode_of(PrivacySettings("instance", False)).mode is PrivacyMode.INSTANCE
    assert privacy_mode_of(PrivacySettings("private", False)).mode is PrivacyMode.PRIVATE
    assert privacy_mode_of(PrivacySettings("household", True)).mode is PrivacyMode.USER_CHOICE
    public = privacy_mode_of(PrivacySettings("public", False, allow_public_recipes=True))
    assert (public.mode, public.default_visibility, public.allow_public_recipes) == (
        PrivacyMode.PUBLIC,
        "public",
        True,
    )
    # A stored public default without the switch counts as instance mode.
    stale = privacy_mode_of(PrivacySettings("public", False, allow_public_recipes=False))
    assert (stale.mode, stale.default_visibility) == (PrivacyMode.INSTANCE, "instance")


def test_a_public_default_needs_the_switch() -> None:
    with pytest.raises(PublicRecipesNotAllowedError):
        validate_privacy(PrivacySettings("public", False))
    validate_privacy(PrivacySettings("public", False, allow_public_recipes=True))
    validate_privacy(PrivacySettings("instance", True))


def test_the_statement_section_says_whether_recipes_can_be_public() -> None:
    allowed = privacy_mode_of(PrivacySettings("instance", True, allow_public_recipes=True))
    closed = privacy_mode_of(PrivacySettings("instance", True))
    english = privacy_mode_text(allowed, "en-GB")
    assert "Anyone on the internet can read a public recipe without signing in" in english
    assert "Your name is not shown on it unless you switch that on" in english
    assert "Public recipes are not allowed on this instance" in privacy_mode_text(closed, "en-GB")
    german = privacy_mode_text(allowed, "de-AT")
    assert "ohne Anmeldung lesen" in german and "außer du schaltest das" in german
    public_mode = privacy_mode_of(PrivacySettings("public", False, allow_public_recipes=True))
    assert "**public**" in privacy_mode_text(public_mode, "en-GB")
