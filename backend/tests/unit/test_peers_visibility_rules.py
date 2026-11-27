"""The peers visibility without a database: read as instance while peering is
off, the audience of a recipe among several paired instances, the sub-recipe
rule, handovers, the lock mode and the settings checks."""

import uuid
from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.services.peer_sharing import _Context
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_handover import Readers
from src.cookbook.domain.services.recipe_handover import handed_over_visibility
from src.cookbook.domain.services.recipe_rules import VisibilitySwitches
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.recipe_rules import effective_visibility
from src.cookbook.domain.services.recipe_rules import narrower
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility as V
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PeerRecipesNotAllowedError
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.services.privacy_draft import privacy_mode_text
from src.platform.domain.services.settings_rules import validate_privacy

NOW = datetime(2026, 11, 27, tzinfo=UTC)


def _recipe(visibility: V, *, recipe_id: int = 1, **extra: object) -> Recipe:
    values: dict[str, object] = {"status": RecipeStatus.PUBLISHED, **extra}
    return Recipe(
        id=recipe_id,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        visibility=visibility,
        **values,  # type: ignore[arg-type]
    )


def _peer(peer_id: int, *, users_may_share: bool = True) -> Peer:
    return Peer(
        id=peer_id,
        instance_id=uuid.uuid4(),
        name=f"Peer {peer_id}",
        base_url=f"https://peer{peer_id}.example.com",
        protocol_version=1,
        users_may_share=users_may_share,
        created=NOW,
        paired_at=NOW,
        changed=NOW,
    )


def _context(*, peering: bool = True, public_allowed: bool = True) -> _Context:
    peers = [_peer(1), _peer(2), _peer(3, users_may_share=False)]
    return _Context(
        peers={p.id: p for p in peers},
        public_allowed=public_allowed,
        peering=peering,
        instance_id=str(uuid.uuid4()),
    )


def test_peers_reads_as_instance_while_peering_is_off() -> None:
    assert effective_visibility(V.PEERS, public_allowed=True) is V.INSTANCE
    assert effective_visibility(V.PEERS, public_allowed=False, peering=True) is V.PEERS
    assert VisibilitySwitches(peering=True).effective(V.PEERS) is V.PEERS
    assert VisibilitySwitches(public_allowed=True).effective(V.PUBLIC) is V.PUBLIC
    settings = PrivacySettings()
    assert settings.effective_visibility("peers") == "instance"
    assert settings.effective_visibility("peers", peering=True) == "peers"


def test_signed_in_viewers_read_peers_recipes_and_visitors_never() -> None:
    reader = User(id=7, full_name="R", email="r@example.com", created=NOW, hashed_password="")
    assert can_view_recipe(Viewer(user=reader), _recipe(V.PEERS))
    assert not can_view_recipe(Viewer.visitor(public_allowed=True), _recipe(V.PEERS))


def test_peers_and_public_recipes_go_to_every_peer_that_may_receive() -> None:
    audience = PeerRecipeSharing._audience
    assert audience(_recipe(V.PEERS), _context()) == {1, 2}
    assert audience(_recipe(V.PUBLIC), _context()) == {1, 2}
    assert audience(_recipe(V.INSTANCE), _context()) == set()
    # Peering off: peers reads as instance; public recipes not allowed:
    # public reads as instance.
    assert audience(_recipe(V.PEERS), _context(peering=False)) == set()
    assert audience(_recipe(V.PUBLIC), _context(public_allowed=False)) == set()
    # Explicit shares count only for peers that may receive.
    assert audience(_recipe(V.SHARED, shared_peer_ids=[2, 3]), _context()) == {2}
    # Drafts and capped recipes never leave.
    assert audience(_recipe(V.PEERS, status=RecipeStatus.DRAFT), _context()) == set()
    assert audience(_recipe(V.PEERS, peer_capped=True), _context()) == set()


def test_an_instance_sub_recipe_of_a_peers_one_is_narrower_only_while_peering_is_on() -> None:
    parent, sub = _recipe(V.PEERS), _recipe(V.INSTANCE, recipe_id=2)
    assert narrower(sub, parent, public_allowed=False, peering=True)
    assert not narrower(sub, parent, public_allowed=False, peering=False)
    public = _recipe(V.PUBLIC, recipe_id=3)
    assert narrower(parent, public, public_allowed=True, peering=True)
    assert not narrower(_recipe(V.PEERS, recipe_id=4), parent, public_allowed=False, peering=True)


def test_handing_over_never_makes_a_recipe_go_to_peers() -> None:
    using = Readers(
        owner_id=2,
        visibility=V.PEERS,
        user_ids=frozenset(),
        group_ids=frozenset(),
        household_ids=frozenset(),
    )
    private = Readers(
        owner_id=1,
        visibility=V.PRIVATE,
        user_ids=frozenset(),
        group_ids=frozenset(),
        household_ids=frozenset(),
    )
    handed = handed_over_visibility(
        private, [using], new_owner_id=2, new_owner_household=frozenset(), leaving_id=1
    )
    assert handed.visibility is V.INSTANCE
    kept = handed_over_visibility(
        using, [], new_owner_id=3, new_owner_household=frozenset(), leaving_id=2
    )
    assert kept.visibility is V.PEERS


def test_the_peers_lock_mode_needs_peering() -> None:
    settings = PrivacySettings("peers", False)
    on = privacy_mode_of(settings, peering=True)
    assert (on.mode, on.default_visibility, on.peering_enabled) == (
        PrivacyMode.PEERS,
        "peers",
        True,
    )
    off = privacy_mode_of(settings)
    assert (off.mode, off.default_visibility, off.peering_enabled) == (
        PrivacyMode.INSTANCE,
        "instance",
        False,
    )
    assert "paired instance" in privacy_mode_text(on, "en-GB")
    assert "verbundenen Instanzen" in privacy_mode_text(on, "de-AT")
    with pytest.raises(PeerRecipesNotAllowedError):
        validate_privacy(settings)
    validate_privacy(settings, peering=True)
