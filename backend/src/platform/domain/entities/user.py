"""
Pure domain entity. No SQLAlchemy, no Pydantic, no FastAPI.
The in-memory representation of an account once loaded from storage.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.platform.domain.value_objects.display import AmountStyle
from src.platform.domain.value_objects.display import CookModeLayout
from src.platform.domain.value_objects.language import Language
from src.platform.domain.value_objects.theme import ThemePreset
from src.platform.domain.value_objects.theme import ThemePrimary
from src.platform.domain.value_objects.theme import ThemeSurface
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class User(Entity):
    # Identity. The e-mail address is what the user signs in with.
    full_name: str
    email: str
    created: datetime
    # An optional short name the user goes by, such as "Bubu".
    nickname: str | None = None

    # Auth
    hashed_password: str

    # Flags. The system user is the account seeded from the INIT__ values
    # on every start; it passes every permission check and cannot be
    # deleted or deactivated, so the instance always keeps an administrator.
    is_active: bool = True
    is_systemuser: bool = False
    # The non-interactive identity behind an API key. It never logs in and
    # holds exactly the permissions its key was granted.
    is_service_account: bool = False

    # Permissions granted to this user directly. What the user may do is
    # effective_permissions, which adds the permissions of their groups.
    permissions: list[str] = field(default_factory=list)

    # Preferences
    language: Language = Language.EN_GB
    theme_preset: ThemePreset = ThemePreset.AURA
    theme_surface: ThemeSurface = ThemeSurface.NEUTRAL
    theme_primary: ThemePrimary = ThemePrimary.CUISINE
    theme_dark_mode: bool = False
    amount_style: AmountStyle = AmountStyle.DECIMALS
    # Opt-in: others planning a meal may learn that a recipe does not suit
    # this user as a guest, never which restriction or that it is this user.
    # Off by default; the API never tells anyone else whether it is on.
    share_restrictions_with_hosts: bool = False
    # The visibility the user's new recipes start with, when the privacy
    # settings let users choose; None follows the instance default.
    default_recipe_visibility: str | None = None
    # Whether other people see the nickname instead of the full name, see
    # display_name. Only takes effect while a nickname is set.
    show_nickname: bool = False
    # Whether the user's display name is shown on their public recipes to
    # visitors who are not signed in. Off by default: no author is shown.
    show_name_on_public_recipes: bool = False
    # Whether the user's display name travels with recipes shared to paired
    # instances. On by default.
    show_name_on_paired_instances: bool = True
    # Which of the cards below a recipe the user wants to see: the author's
    # tips, the user's own notes, the log of who cooked it, and the rating.
    # Every card is shown by default.
    recipe_show_tips: bool = True
    recipe_show_notes: bool = True
    recipe_show_cooked: bool = True
    recipe_show_rating: bool = True
    # Whether the recipe page highlights the ingredients, recipes and
    # equipment a step's text mentions. On by default.
    recipe_highlight_mentions: bool = True
    # Whether an open recipe page or shopping list keeps the phone's screen
    # from turning off, where the browser supports it. On by default.
    keep_screen_on: bool = True
    # How cook mode shows the steps: one per screen or all in one column.
    cook_mode_layout: CookModeLayout = CookModeLayout.STEP
    # The stored image shown as the user's avatar, or None for the initials.
    avatar_file_id: int | None = None

    # The privacy statement version the user acknowledged, and when. A newer
    # published version blocks the user until they acknowledge it again.
    privacy_acknowledged_version: int | None = None
    privacy_acknowledged_at: datetime | None = None
    # Voluntary consents, each the time it was given or None. Health data
    # covers allergies and intolerances; AI agents covers agent tokens.
    consent_health_data_at: datetime | None = None
    consent_ai_agents_at: datetime | None = None

    # Raised to invalidate every token issued before, see ForceLogout.
    token_version: int = 0
    last_logged_in: datetime | None = None

    # 2FA. The secret is stored encrypted at rest by the persistence layer.
    totp_secret: str | None = None
    totp_enabled: bool = False

    # The groups this user belongs to and the union of their permissions.
    # Only the user repository loads them.
    group_ids: list[int] = field(default_factory=list)
    group_permissions: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """The name shown to other people wherever this user appears: the
        nickname when the user chose to go by it, otherwise the full name."""
        nickname = (self.nickname or "").strip()
        return nickname if self.show_nickname and nickname else self.full_name

    @property
    def effective_permissions(self) -> list[str]:
        """The direct grants plus everything the user's groups grant, sorted."""
        return sorted(set(self.permissions) | set(self.group_permissions))

    def has_permission(self, permission: str) -> bool:
        """System users pass all checks; everyone else must hold the
        permission directly or through one of their groups."""
        if self.is_systemuser:
            return True
        return permission in self.permissions or permission in self.group_permissions
