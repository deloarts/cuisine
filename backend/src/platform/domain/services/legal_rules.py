"""The privacy mode in plain words, the checks for legal texts and whether
a user still has to acknowledge the privacy statement."""

from src.platform.domain.entities.legal import LegalVersion
from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.legal import PrivacyModeSnapshot
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.services.settings_rules import CONTENT_LOCALES

LEGAL_TEXT_MAX = 50_000
FALLBACK_LOCALE = "en-GB"


def privacy_mode_of(settings: PrivacySettings, *, peering: bool = False) -> PrivacyModeSnapshot:
    """The lock mode the privacy settings amount to, with `peering` the state
    of the peering feature. The default is read through the public and
    peering switches, so a stored "public" default while public recipes are
    not allowed, or a stored "peers" default while peering is off, counts as
    instance mode."""
    default = settings.effective_visibility(settings.default_recipe_visibility, peering=peering)
    if settings.users_may_change_visibility:
        mode = PrivacyMode.USER_CHOICE
    elif default == "public":
        mode = PrivacyMode.PUBLIC
    elif default == "peers":
        mode = PrivacyMode.PEERS
    elif default == "instance":
        mode = PrivacyMode.INSTANCE
    else:
        mode = PrivacyMode.PRIVATE
    return PrivacyModeSnapshot(
        mode=mode,
        default_visibility=default,
        allow_public_recipes=settings.allow_public_recipes,
        peering_enabled=peering,
    )


def validate_legal_texts(texts: dict[str, str]) -> dict[str, str]:
    unknown = set(texts) - CONTENT_LOCALES
    if unknown:
        raise InvalidInputError(f"Unknown languages: {', '.join(sorted(unknown))}.")
    kept = {k: v.strip() for k, v in texts.items() if v.strip()}
    if not kept:
        raise InvalidInputError("The page needs a text in at least one language.")
    if any(len(v) > LEGAL_TEXT_MAX for v in kept.values()):
        raise InvalidInputError(f"A legal text holds at most {LEGAL_TEXT_MAX} characters.")
    return kept


def legal_text(version: LegalVersion, locale: str) -> tuple[str, str]:
    for candidate in (locale, FALLBACK_LOCALE):
        if candidate in version.texts:
            return candidate, version.texts[candidate]
    first = sorted(version.texts)[0]
    return first, version.texts[first]


def acknowledgement_pending(user: User, current: LegalVersion | None) -> bool:
    """Service accounts never read a statement; everyone else must have
    acknowledged the current version, once there is one."""
    if current is None or user.is_service_account:
        return False
    acknowledged = user.privacy_acknowledged_version
    return acknowledged is None or acknowledged < current.version
