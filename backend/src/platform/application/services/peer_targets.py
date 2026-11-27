"""
Checks a peer's base URL before anything is stored or sent: the https rule
and the webhook target guard, with the private network switch of the
notification settings, which applies to peers too.
"""

from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.services.peering_rules import normalised_base_url
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard


async def private_targets_allowed(settings_repo: ISettingsRepository) -> bool:
    return (await settings_repo.get_notifications()).allow_private_webhook_targets


async def checked_base_url(
    url: str,
    *,
    guard: IWebhookTargetGuard,
    settings_repo: ISettingsRepository,
    require_https: bool,
) -> str:
    """The normalised base URL, once the https rule and the target guard
    accept it."""
    base = normalised_base_url(url, require_https=require_https)
    try:
        await guard.check(
            base, allow_private=await private_targets_allowed(settings_repo), subject="peer"
        )
    except InvalidWebhookConfigurationError as exc:
        raise InvalidPeerConfigurationError(str(exc)) from exc
    return base
