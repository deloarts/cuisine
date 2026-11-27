"""
Registers what the cookbook brings to peering in Platform's catalogue, so
Platform never names a cookbook concept: the exchange formats with the
versions a peer may receive (the current one and the one before it), the
capabilities this release can show on a mirror, the `recipe` content kind
of the peer channel (what this instance sends and how it takes in what a
peer sends), and what follows a pairing, a revoke, a change of a peer's
switches or capabilities, and a change of the public recipes or the peering
switch.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import receive_peer_recipes
from src.cookbook.application.services.formats.specs import CATALOGUE
from src.cookbook.application.services.formats.specs import RECIPES
from src.cookbook.application.services.peer_sharing import RECIPE_KIND
from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.use_cases.mirrors.receive_recipes import ReceivePeerRecipes
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.application.use_cases.admin.settings import FeaturesSavedHook
from src.platform.application.use_cases.admin.settings import PrivacySavedHook
from src.platform.application.use_cases.peering.pairing import PeerPairedHook
from src.platform.application.use_cases.peering.peers import PeerChangedHook
from src.platform.application.use_cases.peering.peers import PeerRevokedHook
from src.platform.domain.value_objects.peering import PeeringFormat
from src.platform.domain.value_objects.peering import register_peering_capability
from src.platform.domain.value_objects.peering import register_peering_format

# What a mirror on this instance can show of a peer's recipes.
COOKBOOK_CAPABILITIES = ("equipment", "extended_nutrients", "seasons", "variations")


def _window(current: int, released: list[int]) -> tuple[int, ...]:
    return tuple(v for v in sorted(released) if v >= current - 1)


def register_cookbook_peering() -> None:
    """Idempotent, since tests build the app more than once."""
    register_peering_format(
        PeeringFormat(
            name=RECIPES.name,
            versions=_window(RECIPES.current, list(RECIPES.versions)),
            required=True,
        )
    )
    register_peering_format(
        PeeringFormat(
            name=CATALOGUE.name, versions=_window(CATALOGUE.current, list(CATALOGUE.versions))
        )
    )
    for capability in COOKBOOK_CAPABILITIES:
        register_peering_capability(capability)


def _sharing(db: AsyncSession) -> PeerRecipeSharing:
    return Cookbook(Platform(db)).sharing()


def _receiver(db: AsyncSession) -> ReceivePeerRecipes:
    return receive_peer_recipes(Cookbook(Platform(db)))


def _revoked(db: AsyncSession) -> PeerRevokedHook:
    return _receiver(db).peer_revoked


def _changed(db: AsyncSession) -> PeerChangedHook:
    return _receiver(db).peer_changed


def _privacy_saved(db: AsyncSession) -> PrivacySavedHook:
    return _receiver(db).privacy_saved


def _features_saved(db: AsyncSession) -> FeaturesSavedHook:
    return _receiver(db).features_saved


def _paired(db: AsyncSession) -> PeerPairedHook:
    return _receiver(db).peer_paired


_mirrors_registered = False


def register_cookbook_mirrors() -> None:
    """Idempotent, since tests build the app more than once."""
    global _mirrors_registered
    if _mirrors_registered:
        return
    deps.register_peer_content(RECIPE_KIND, provider=_sharing, consumer=_receiver)
    deps.register_peer_revoked_hook(_revoked)
    deps.register_peer_changed_hook(_changed)
    deps.register_privacy_saved_hook(_privacy_saved)
    deps.register_features_saved_hook(_features_saved)
    deps.register_peer_paired_hook(_paired)
    _mirrors_registered = True
