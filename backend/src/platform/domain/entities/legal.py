"""
A published version of a legal page: the imprint or the privacy statement,
with its text per content locale. Versions are never edited; publishing
creates the next one. A new privacy statement version asks every user to
acknowledge it again before they can go on using the app.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class LegalKind(StrValueEnum):
    IMPRINT = "imprint"
    PRIVACY = "privacy"


class PrivacyMode(StrValueEnum):
    # Every new recipe is visible to every signed-in user, and nobody can
    # change that.
    INSTANCE = "instance"
    # Every new recipe is public, readable without signing in, and nobody
    # can change that. Needs public recipes to be allowed.
    PUBLIC = "public"
    # Every new recipe goes to every signed-in user and every paired
    # instance, and nobody can change that. Needs peering to be on.
    PEERS = "peers"
    # New recipes start at a narrower default, and nobody can change it.
    PRIVATE = "private"
    # Every user picks each recipe's visibility, starting from the default.
    USER_CHOICE = "user_choice"


@dataclass(frozen=True)
class PrivacyModeSnapshot:
    """The privacy settings a statement version was published under, so the
    statement always names the mode it was acknowledged for."""

    mode: PrivacyMode
    default_visibility: str
    # Whether public recipes were allowed. Versions published before the
    # setting existed read as False, which is what those instances did.
    allow_public_recipes: bool = False
    # Whether peering was on. Versions published before it was recorded
    # read as False.
    peering_enabled: bool = False


@dataclass(kw_only=True)
class LegalVersion(Entity):
    kind: LegalKind
    version: int
    # Markdown per content locale.
    texts: dict[str, str] = field(default_factory=dict)
    published_at: datetime
    published_by_id: int | None = None
    # Set on privacy statement versions.
    privacy_mode: PrivacyModeSnapshot | None = None
