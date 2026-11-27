"""
The admin settings, one dataclass per section. Each section is stored as a
whole and has a default for every field, so a fresh database works before an
administrator has saved anything.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.platform.domain.value_objects.display import BannerSeverity
from src.platform.domain.value_objects.display import DateFormat
from src.platform.domain.value_objects.display import TimeFormat
from src.platform.domain.value_objects.display import UnitSystem
from src.platform.domain.value_objects.display import Weekday
from src.platform.domain.value_objects.language import Language
from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


@dataclass
class GeneralSettings:
    # Shown in the browser title, the login page and outgoing mail.
    instance_name: str = "Cuisine"
    # The language of the login page and of new accounts.
    default_language: Language = Language.EN_GB
    # Branding: an accent colour as #rrggbb (empty keeps the theme's own)
    # and a background photo for the sign-in screens, the public id of a
    # stored image. The login page shows it, so it is served without a
    # session.
    accent_color: str = ""
    login_background_file_id: str | None = None
    # The faint steam rising behind the sign-in card. Visitors who ask their
    # browser for reduced motion never see it either way.
    login_steam: bool = True
    # Display defaults every user sees.
    unit_system: UnitSystem = UnitSystem.METRIC
    date_format: DateFormat = DateFormat.DMY_DOT
    time_format: TimeFormat = TimeFormat.H24
    first_day_of_week: Weekday = Weekday.MONDAY


# The enum fields of GeneralSettings, for the repository to restore from JSON.
GENERAL_ENUM_FIELDS: dict[str, type[StrValueEnum]] = {
    "default_language": Language,
    "unit_system": UnitSystem,
    "date_format": DateFormat,
    "time_format": TimeFormat,
    "first_day_of_week": Weekday,
}


@dataclass
class SecuritySettings:
    # When on, every account must set up TOTP; a login without it is walked
    # through enrolment before it gets a session.
    enforce_totp: bool = False
    min_password_length: int = 10
    # Idle timeout of a web session.
    session_timeout_minutes: int = 60 * 24 * 7
    # Absolute lifetime of a web session, however active it stays.
    session_max_lifetime_days: int = 30
    # "Trust this device" skips the TOTP step for this many days; 0 turns it off.
    totp_trusted_device_days: int = 30
    # Failed logins per name or address before a lockout; 0 means unlimited.
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    # Whether any request may authenticate with an API key.
    enable_api_key_auth: bool = False
    # Ceiling on the lifetime of a new PAT or API key; 0 lifts the cap.
    token_max_lifetime_days: int = 365


@dataclass
class IntegrationSettings:
    # USDA FoodData Central, the public domain (CC0) nutrient database the
    # ingredient editor can prefill nutrition from. DEMO_KEY works without
    # registering but allows only a few requests per hour; a free key from
    # api.data.gov lifts that. The key is stored encrypted.
    usda_enabled: bool = True
    usda_api_key: str = "DEMO_KEY"


@dataclass
class AgentSettings:
    # Whether AI agents may connect through the MCP surface at all.
    enabled: bool = True
    # Tool calls one token may make per minute.
    calls_per_minute: int = 120
    # Drafts (recipes, ingredients) one token may create per hour.
    drafts_per_hour: int = 30
    # Ceiling on the lifetime of a token carrying use:mcp; 0 lifts the cap,
    # leaving only the general token cap.
    token_max_lifetime_days: int = 30
    # Whether hosted AI clients (ChatGPT, claude.ai) may connect through
    # OAuth. Off refuses new approvals and every OAuth token; agents with a
    # personal access token are not affected.
    oauth_enabled: bool = True
    # The hosts an OAuth client may redirect to, matched exactly; empty
    # allows any host. Checked at registration and at every approval.
    oauth_redirect_hosts: list[str] = field(default_factory=list)


# The recipe visibilities, as the cookbook names them, narrowest first.
RECIPE_VISIBILITIES = ("private", "household", "shared", "instance", "peers", "public")


@dataclass
class PrivacySettings:
    """A fresh instance runs in peers mode: Cuisine is built to share, so
    every recipe is visible to every signed-in member and every paired
    instance, and users may not narrow it. Instance mode, private mode, user
    choice and public recipes are the administrator's options. These
    defaults apply only to a section that was never saved; stored settings
    are never rewritten."""

    # The visibility new recipes get: private, household, shared, instance,
    # peers or public (peers only while peering is on, public only while
    # public recipes are allowed).
    default_recipe_visibility: str = "peers"
    # Whether users choose a recipe's visibility (and their own default).
    # Off locks every new recipe to the default: peers mode with "peers",
    # instance mode with "instance", public mode with "public", private mode
    # with anything narrower.
    users_may_change_visibility: bool = False
    # Whether "public" (anyone, without signing in) is offered. While off, a
    # stored "public" reads as "instance"; switching never rewrites rows.
    allow_public_recipes: bool = False
    # Whether search engines may index the public recipe pages (robots.txt
    # and the pages' robots meta). It applies only while public recipes are
    # allowed (`indexing_allowed`).
    index_public_recipes: bool = False

    @property
    def indexing_allowed(self) -> bool:
        return self.allow_public_recipes and self.index_public_recipes

    def effective_visibility(self, visibility: str, *, peering: bool = False) -> str:
        """The visibility that applies to a stored value: "public" reads as
        "instance" while public recipes are not allowed, and "peers" reads as
        "instance" while peering (`FeatureSettings.peering`) is off."""
        if visibility == "public" and not self.allow_public_recipes:
            return "instance"
        if visibility == "peers" and not peering:
            return "instance"
        return visibility


@dataclass
class ShoppingSettings:
    """Read and enforced by the cookbook's shopping lists."""

    # How long a ticked item stays under "Recently bought" on a continuous
    # list before it is deleted.
    bought_window_hours: int = 12
    # A normal list nobody used for this many days deletes itself; 0 turns
    # that off.
    idle_list_days: int = 30


@dataclass
class MailSettings:
    enabled: bool = False
    host: str = ""
    port: int = 587
    # "starttls" upgrades a plain connection, "tls" connects with TLS
    # straight away (port 465), "none" sends in the clear.
    security: str = "starttls"
    username: str = ""
    # Stored encrypted; the API never returns it.
    password: str = ""
    # The From address.
    sender: str = ""
    # Wrapped around the sender in the From header; empty sends the bare
    # address.
    sender_name: str = ""
    # Reply-To on every mail; empty sends none.
    reply_to: str = ""
    # Off accepts a relay whose certificate the system trust store cannot
    # validate, such as a self-signed one on the home network.
    verify_certificate: bool = True
    # Mails the instance sends per hour at most; operational alerts beyond
    # it are dropped and logged. 0 lifts the limit.
    send_limit_per_hour: int = 60
    # Who receives operational alerts (failed backups, a webhook switched
    # off, maintenance mode, storage warnings).
    alert_recipients: list[str] = field(default_factory=list)


@dataclass
class NotificationSettings:
    # Whether events are sent to the webhook subscriptions at all.
    webhooks_enabled: bool = True
    # Whether a webhook may target an address on a private network, such
    # as a home automation server next to the instance. Loopback,
    # link-local, metadata and the stack's own services are refused anyway.
    allow_private_webhook_targets: bool = True


@dataclass
class BannerSettings:
    """The one in-app banner every page shows while it is active, including
    the login page."""

    enabled: bool = False
    severity: BannerSeverity = BannerSeverity.INFO
    # The message per content locale (en-GB, de-AT); a locale without text
    # falls back to en-GB, then to any text there is.
    messages: dict[str, str] = field(default_factory=dict)
    # An optional window; outside it the banner is off.
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    # Whether a user may close it for themselves.
    dismissible: bool = True


@dataclass
class FeatureSettings:
    """The switches for whole features, in one place. The agent, webhook
    and USDA switches are the same values the agents, notifications and
    integrations sections show as their `enabled` flags."""

    agents: bool = True
    webhooks: bool = True
    households: bool = True
    dinner_guests: bool = True
    usda: bool = True
    # Pairing with other Cuisine instances, on for a fresh instance since its
    # default visibility is peers; while off, every peering route answers 404
    # and a peers recipe reads as instance.
    peering: bool = True


@dataclass
class MaintenanceSettings:
    """While on, the app is read-only: every write is refused with 503,
    except signing in and out and switching maintenance off."""

    enabled: bool = False
    # Shown in the banner, per content locale; empty uses the built-in text.
    messages: dict[str, str] = field(default_factory=dict)
    since: datetime | None = None


@dataclass
class RetentionSettings:
    """How long logs and histories are kept, in days. The nightly purge
    removes older entries; 0 keeps them forever."""

    security_log_days: int = 365
    agent_calls_days: int = 90
    webhook_deliveries_days: int = 30
    # Read and enforced by the cookbook.
    recipe_revisions_days: int = 365


@dataclass(frozen=True)
class MailTemplateText:
    subject: str
    body: str


@dataclass
class MailTemplateSettings:
    """Administrator overrides of the built-in mail templates, keyed by
    template key, then content locale. A missing entry uses the default."""

    overrides: dict[str, dict[str, MailTemplateText]] = field(default_factory=dict)
