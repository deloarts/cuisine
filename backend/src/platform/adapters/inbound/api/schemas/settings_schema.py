from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime
from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema
from src.platform.domain.value_objects.display import BannerSeverity
from src.platform.domain.value_objects.display import DateFormat
from src.platform.domain.value_objects.display import TimeFormat
from src.platform.domain.value_objects.display import UnitSystem
from src.platform.domain.value_objects.display import Weekday
from src.platform.domain.value_objects.language import Language


class GeneralSettingsSchema(RequestSchema):
    instance_name: str = Field(min_length=1, max_length=64)
    default_language: Language
    # Branding: #rrggbb or empty, and for the sign-in background the id of
    # an uploaded image (POST /files) or null.
    accent_color: str = Field(default="", max_length=7)
    login_background_file_id: str | None = Field(default=None, max_length=64)
    login_steam: bool = True
    unit_system: UnitSystem = UnitSystem.METRIC
    date_format: DateFormat = DateFormat.DMY_DOT
    time_format: TimeFormat = TimeFormat.H24
    first_day_of_week: Weekday = Weekday.MONDAY


class SecuritySettingsSchema(RequestSchema):
    enforce_totp: bool
    min_password_length: int = Field(ge=8, le=72)
    session_timeout_minutes: int = Field(ge=5)
    session_max_lifetime_days: int = Field(ge=1)
    totp_trusted_device_days: int = Field(ge=0, le=365)
    max_login_attempts: int = Field(ge=1)
    lockout_duration_minutes: int = Field(ge=0)
    enable_api_key_auth: bool
    token_max_lifetime_days: int = Field(ge=0)


class MailSettingsRequest(RequestSchema):
    enabled: bool
    host: str = Field(max_length=255)
    port: int = Field(ge=1, le=65535)
    # starttls upgrades a plain connection (TLS), tls connects with TLS at
    # once (SSL, port 465), none sends in the clear.
    security: Literal["starttls", "tls", "none"]
    username: str = Field(max_length=255)
    # None keeps the stored password; an empty string clears it.
    password: str | None = Field(default=None, max_length=1024)
    sender: str = Field(max_length=255)
    sender_name: str = Field(default="", max_length=128)
    reply_to: str = Field(default="", max_length=255)
    verify_certificate: bool = True
    send_limit_per_hour: int = Field(default=60, ge=0, le=10_000)
    alert_recipients: list[str] = Field(default_factory=list, max_length=20)


class MailSettingsResponse(ResponseSchema):
    enabled: bool
    host: str
    port: int
    security: str
    username: str
    password_set: bool
    sender: str
    sender_name: str
    reply_to: str
    verify_certificate: bool
    send_limit_per_hour: int
    alert_recipients: list[str]


class TestMailRequest(RequestSchema):
    # Defaults to the acting user's own address.
    to: str | None = Field(default=None, max_length=255)


class FeatureSettingsSchema(RequestSchema):
    agents: bool
    webhooks: bool
    households: bool
    dinner_guests: bool
    usda: bool
    peering: bool


class RetentionSettingsSchema(RequestSchema):
    security_log_days: int = Field(ge=0, le=3650)
    agent_calls_days: int = Field(ge=0, le=3650)
    webhook_deliveries_days: int = Field(ge=0, le=3650)
    recipe_revisions_days: int = Field(ge=0, le=3650)


class MaintenanceRequest(RequestSchema):
    enabled: bool
    messages: dict[Literal["en-GB", "de-AT"], str] = Field(default_factory=dict)


class MaintenanceResponse(ResponseSchema):
    enabled: bool
    messages: dict[str, str]
    since: datetime | None


class PublicMaintenanceResponse(ResponseSchema):
    enabled: bool
    message: str | None
    since: datetime | None


class IntegrationSettingsRequest(RequestSchema):
    usda_enabled: bool
    # None keeps the stored key; DEMO_KEY is USDA's shared demonstration key.
    usda_api_key: str | None = Field(default=None, max_length=255)


class IntegrationSettingsResponse(ResponseSchema):
    usda_enabled: bool
    usda_api_key_set: bool
    usda_uses_demo_key: bool


class PrivacySettingsSchema(RequestSchema):
    # "public" only while allow_public_recipes is on (422
    # PublicRecipesNotAllowedError otherwise), "peers" only while peering is
    # on (422 PeerRecipesNotAllowedError otherwise).
    default_recipe_visibility: Literal[
        "private", "household", "shared", "instance", "peers", "public"
    ]
    users_may_change_visibility: bool
    # While off, "public" is not offered and a stored "public" reads as
    # "instance". Changing it publishes a new privacy statement version.
    allow_public_recipes: bool = False
    # Whether search engines may index the public recipe pages; applies
    # only while public recipes are allowed. Changing only this publishes no
    # new privacy statement version.
    index_public_recipes: bool = False


class ShoppingSettingsSchema(RequestSchema):
    # How long ticked items stay under "Recently bought" on continuous lists.
    bought_window_hours: int = Field(ge=1, le=720)
    # Days after which an unused normal list deletes itself; 0 turns it off.
    idle_list_days: int = Field(ge=0, le=3650)


class AgentSettingsSchema(RequestSchema):
    enabled: bool
    calls_per_minute: int = Field(ge=1, le=10_000)
    drafts_per_hour: int = Field(ge=0, le=10_000)
    token_max_lifetime_days: int = Field(ge=0)
    oauth_enabled: bool = True
    oauth_redirect_hosts: list[str] = Field(default_factory=list, max_length=50)


class PublicInfoResponse(ResponseSchema):
    """What the login page needs before anybody signed in."""

    instance_name: str
    default_language: Language
    version: str
    accent_color: str
    # GET /api/v1/public/branding/login-background serves the sign-in
    # background when set. The key changes with the image, so a client puts
    # it in the URL to skip a cached copy of the previous one; null without
    # a background.
    login_background_key: str | None
    # Whether the sign-in screens show the steam animation.
    login_steam: bool
    unit_system: UnitSystem
    date_format: DateFormat
    time_format: TimeFormat
    first_day_of_week: Weekday
    maintenance: PublicMaintenanceResponse
    features: FeatureSettingsSchema
    # instance, peers, public, private or user_choice, with the default
    # visibility.
    privacy_mode: str
    default_recipe_visibility: str
    # Which legal pages are published (GET /api/v1/public/legal/{kind}).
    imprint_published: bool
    privacy_statement_published: bool
    # Whether public recipes can be read without signing in
    # (/api/v1/public/recipes), so the login page links to them, and whether
    # search engines may index those pages (only ever true while allowed).
    allow_public_recipes: bool
    index_public_recipes: bool


class WebAppIconResponse(ResponseSchema):
    src: str
    sizes: str
    type: str
    # "any" for an icon shown as drawn, "maskable" for one the system cuts
    # its own shape out of.
    purpose: str


class WebAppManifestResponse(ResponseSchema):
    """The web app manifest (W3C Web Application Manifest) that lets a
    phone or a desktop browser install the instance as an app under its own
    name. Paths are absolute, since the manifest is served below /api while
    the app lives at the root."""

    id: str
    name: str
    short_name: str
    lang: str
    dir: str
    start_url: str
    scope: str
    display: str
    theme_color: str
    background_color: str
    icons: list[WebAppIconResponse]


class NotificationSettingsSchema(RequestSchema):
    webhooks_enabled: bool
    allow_private_webhook_targets: bool


ContentLocale = Literal["en-GB", "de-AT"]


class BannerSettingsSchema(RequestSchema):
    enabled: bool
    severity: BannerSeverity
    messages: dict[ContentLocale, str]
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    dismissible: bool = True


class PublicBannerResponse(ResponseSchema):
    severity: BannerSeverity
    message: str
    # The locale actually served.
    locale: str
    dismissible: bool
    ends_at: datetime | None
    # Changes whenever the banner's content changes, so a dismissal stored
    # under the old key does not hide a new message.
    key: str
