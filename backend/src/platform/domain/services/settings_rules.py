"""Range checks for the admin settings, applied before a section is saved."""

import re

from src.platform.domain.entities.settings import RECIPE_VISIBILITIES
from src.platform.domain.entities.settings import AgentSettings
from src.platform.domain.entities.settings import BannerSettings
from src.platform.domain.entities.settings import GeneralSettings
from src.platform.domain.entities.settings import IntegrationSettings
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.entities.settings import MaintenanceSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.exceptions import InvalidSettingsError
from src.platform.domain.exceptions import PeerRecipesNotAllowedError
from src.platform.domain.exceptions import PublicRecipesNotAllowedError
from src.platform.domain.services.oauth_rules import normalise_hosts

MAIL_SECURITY_MODES = frozenset({"starttls", "tls", "none"})


_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
# The content locales a banner or notice may carry text in.
CONTENT_LOCALES = frozenset({"en-GB", "de-AT"})
BANNER_MAX_LENGTH = 500


def validate_general(settings: GeneralSettings) -> None:
    if not settings.instance_name.strip():
        raise InvalidSettingsError("The instance name must not be empty.")
    if settings.accent_color and not _HEX_COLOR.match(settings.accent_color):
        raise InvalidSettingsError("The accent colour must be #rrggbb or empty.")


def validate_banner(settings: BannerSettings) -> None:
    unknown = set(settings.messages) - CONTENT_LOCALES
    if unknown:
        raise InvalidSettingsError(f"Unknown banner languages: {', '.join(sorted(unknown))}.")
    if any(len(text) > BANNER_MAX_LENGTH for text in settings.messages.values()):
        raise InvalidSettingsError(
            f"A banner message holds at most {BANNER_MAX_LENGTH} characters."
        )
    if settings.enabled and not any(t.strip() for t in settings.messages.values()):
        raise InvalidSettingsError("An active banner needs a message.")
    if settings.starts_at and settings.ends_at and settings.ends_at <= settings.starts_at:
        raise InvalidSettingsError("The banner must end after it starts.")


def validate_security(settings: SecuritySettings) -> None:
    if not 8 <= settings.min_password_length <= 72:
        raise InvalidSettingsError("The minimum password length must be between 8 and 72.")
    if settings.session_timeout_minutes < 5:
        raise InvalidSettingsError("The session timeout must be at least 5 minutes.")
    if settings.session_max_lifetime_days < 1:
        raise InvalidSettingsError("The session lifetime must be at least one day.")
    # Zero would never lock, which would switch the login throttle off.
    if settings.max_login_attempts < 1:
        raise InvalidSettingsError("The login attempts before a lockout must be at least 1.")
    for name in (
        "totp_trusted_device_days",
        "lockout_duration_minutes",
        "token_max_lifetime_days",
    ):
        if getattr(settings, name) < 0:
            raise InvalidSettingsError(f"{name} must not be negative.")


def validate_mail(settings: MailSettings) -> None:
    if settings.security not in MAIL_SECURITY_MODES:
        raise InvalidSettingsError("The mail security must be starttls, tls or none.")
    if not 1 <= settings.port <= 65535:
        raise InvalidSettingsError("The mail port must be between 1 and 65535.")
    if settings.enabled and not (settings.host.strip() and settings.sender.strip()):
        raise InvalidSettingsError("Mail needs a server and a sender address.")
    if settings.send_limit_per_hour < 0:
        raise InvalidSettingsError("The hourly mail limit must not be negative.")
    for address in [settings.sender, settings.reply_to, *settings.alert_recipients]:
        if address and ("@" not in address or any(c.isspace() for c in address.strip())):
            raise InvalidSettingsError(f"{address!r} is not a mail address.")


def validate_integrations(settings: IntegrationSettings) -> None:
    if settings.usda_enabled and not settings.usda_api_key.strip():
        raise InvalidSettingsError("The USDA lookup needs an API key, or DEMO_KEY.")


def validate_agents(settings: AgentSettings) -> None:
    if not 1 <= settings.calls_per_minute <= 10_000:
        raise InvalidSettingsError("The calls per minute must be between 1 and 10000.")
    if not 0 <= settings.drafts_per_hour <= 10_000:
        raise InvalidSettingsError("The drafts per hour must be between 0 and 10000.")
    if settings.token_max_lifetime_days < 0:
        raise InvalidSettingsError("The agent token lifetime must not be negative.")
    if len(settings.oauth_redirect_hosts) > 50:
        raise InvalidSettingsError("At most 50 redirect hosts may be listed.")
    try:
        settings.oauth_redirect_hosts = normalise_hosts(settings.oauth_redirect_hosts)
    except ValueError as e:
        raise InvalidSettingsError(
            f"{e.args[0]!r} is not a host name. List bare host names such as chatgpt.com, "
            "without scheme, path, port or wildcard."
        ) from e


def validate_privacy(settings: PrivacySettings, *, peering: bool = False) -> None:
    """`peering` is the state of the peering feature, which a peers default
    needs."""
    if settings.default_recipe_visibility not in RECIPE_VISIBILITIES:
        raise InvalidSettingsError(
            "The default visibility must be private, household, shared, instance, peers or public."
        )
    if settings.default_recipe_visibility == "public" and not settings.allow_public_recipes:
        raise PublicRecipesNotAllowedError(
            "The default visibility can only be public while public recipes are allowed."
        )
    if settings.default_recipe_visibility == "peers" and not peering:
        raise PeerRecipesNotAllowedError(
            "The default visibility can only be paired instances while peering is on."
        )


RETENTION_MAX_DAYS = 3650
SHOPPING_MAX_WINDOW_HOURS = 24 * 30


def validate_shopping(settings: ShoppingSettings) -> None:
    if not 1 <= settings.bought_window_hours <= SHOPPING_MAX_WINDOW_HOURS:
        raise InvalidSettingsError(
            f"The recently bought window must be between 1 and {SHOPPING_MAX_WINDOW_HOURS} hours."
        )
    if not 0 <= settings.idle_list_days <= RETENTION_MAX_DAYS:
        raise InvalidSettingsError(f"The idle days must be between 0 and {RETENTION_MAX_DAYS}.")


def validate_retention(settings: RetentionSettings) -> None:
    for name in (
        "security_log_days",
        "agent_calls_days",
        "webhook_deliveries_days",
        "recipe_revisions_days",
    ):
        if not 0 <= getattr(settings, name) <= RETENTION_MAX_DAYS:
            raise InvalidSettingsError(f"{name} must be between 0 and {RETENTION_MAX_DAYS} days.")


def validate_maintenance(settings: MaintenanceSettings) -> None:
    unknown = set(settings.messages) - CONTENT_LOCALES
    if unknown:
        raise InvalidSettingsError(f"Unknown languages: {', '.join(sorted(unknown))}.")
    if any(len(t) > BANNER_MAX_LENGTH for t in settings.messages.values()):
        raise InvalidSettingsError(
            f"A maintenance message holds at most {BANNER_MAX_LENGTH} characters."
        )
