from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr
from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema
from src.platform.domain.entities.user import User
from src.platform.domain.services.login_rules import totp_mandatory
from src.platform.domain.value_objects.display import AmountStyle
from src.platform.domain.value_objects.language import Language
from src.platform.domain.value_objects.theme import ThemePreset
from src.platform.domain.value_objects.theme import ThemePrimary
from src.platform.domain.value_objects.theme import ThemeSurface


class UserSummaryResponse(ResponseSchema):
    """What every signed-in user may see of another account. The display
    name is the nickname when the person chose to go by it, otherwise the
    full name, which then stays private to the person and the admins."""

    id: UUID
    display_name: str


class DirectoryUserResponse(UserSummaryResponse):
    """An entry of the people directory, with the avatar so pickers can show
    the face next to the name. Every signed-in user may read every avatar."""

    avatar_id: UUID | None


class UserResponse(ResponseSchema):
    id: UUID
    full_name: str
    nickname: str | None
    # Whether others see the nickname instead of the full name.
    show_nickname: bool
    # The name others see: the nickname when shown, otherwise the full name.
    display_name: str
    email: str
    is_active: bool
    is_systemuser: bool
    permissions: list[str]
    effective_permissions: list[str]
    group_ids: list[UUID]
    language: Language
    totp_enabled: bool
    # Whether two-factor authentication is mandatory for the account
    # whatever the security settings say: the system user and anyone holding
    # a settings permission. It cannot be turned off while this is true.
    totp_mandatory: bool
    created: datetime
    last_logged_in: datetime | None
    # The stored file shown as the avatar; its thumbnail is served by
    # /api/v1/web/files/{id}/content. Null shows the initials.
    avatar_id: UUID | None = None


class CurrentUserResponse(UserResponse):
    theme_preset: ThemePreset
    theme_surface: ThemeSurface
    theme_primary: ThemePrimary
    theme_dark_mode: bool
    # How small metric amounts in recipes read: exact decimals or kitchen
    # fractions of a litre or kilogram.
    amount_style: AmountStyle
    # Only ever shown to the user themselves.
    share_restrictions_with_hosts: bool
    default_recipe_visibility: str | None
    # Whether the display name shows on the user's public recipes and on
    # recipes shared with paired instances.
    show_name_on_public_recipes: bool
    show_name_on_paired_instances: bool
    # Which cards below a recipe the user sees: tips, own notes, the cook
    # log and the rating. All are on unless the user turned them off.
    recipe_show_tips: bool
    recipe_show_notes: bool
    recipe_show_cooked: bool
    recipe_show_rating: bool
    # Whether the recipe page highlights what a step's text mentions.
    recipe_highlight_mentions: bool
    # Whether an open recipe or shopping list keeps the screen on.
    keep_screen_on: bool
    # Whether the user must acknowledge the current privacy statement
    # before anything else works, and which version that is.
    privacy_acknowledgement_pending: bool = False
    privacy_version: int | None = None
    privacy_acknowledged_version: int | None = None
    # The instance's privacy mode, for the account page to show read-only.
    privacy_mode: "PrivacyModeResponse | None" = None
    # When each voluntary consent was given, or null.
    consent_health_data_at: datetime | None = None
    consent_ai_agents_at: datetime | None = None


class PrivacyModeResponse(ResponseSchema):
    # instance, peers, public, private or user_choice
    mode: str
    default_visibility: str
    allow_public_recipes: bool = False


CurrentUserResponse.model_rebuild()


def user_response[R: UserResponse](
    cls: type[R],
    user: User,
    group_public_ids: dict[int, UUID],
    file_public_ids: dict[int, UUID],
) -> R:
    data = {
        "id": user.public_id,
        "full_name": user.full_name,
        "nickname": user.nickname,
        "show_nickname": user.show_nickname,
        "display_name": user.display_name,
        "email": user.email,
        "is_active": user.is_active,
        "is_systemuser": user.is_systemuser,
        "permissions": sorted(user.permissions),
        "effective_permissions": user.effective_permissions,
        "group_ids": [group_public_ids[g] for g in user.group_ids if g in group_public_ids],
        "language": user.language,
        "totp_enabled": user.totp_enabled,
        "totp_mandatory": totp_mandatory(user),
        "created": user.created,
        "last_logged_in": user.last_logged_in,
        "avatar_id": file_public_ids.get(user.avatar_file_id) if user.avatar_file_id else None,
        "theme_preset": user.theme_preset,
        "theme_surface": user.theme_surface,
        "theme_primary": user.theme_primary,
        "theme_dark_mode": user.theme_dark_mode,
        "amount_style": user.amount_style,
        "share_restrictions_with_hosts": user.share_restrictions_with_hosts,
        "default_recipe_visibility": user.default_recipe_visibility,
        "show_name_on_public_recipes": user.show_name_on_public_recipes,
        "show_name_on_paired_instances": user.show_name_on_paired_instances,
        "recipe_show_tips": user.recipe_show_tips,
        "recipe_show_notes": user.recipe_show_notes,
        "recipe_show_cooked": user.recipe_show_cooked,
        "recipe_show_rating": user.recipe_show_rating,
        "recipe_highlight_mentions": user.recipe_highlight_mentions,
        "keep_screen_on": user.keep_screen_on,
    }
    return cls.model_validate(data)


class UpdateOwnProfileRequest(RequestSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=128)
    # An empty string clears the nickname.
    nickname: str | None = Field(default=None, max_length=64)
    show_nickname: bool | None = None
    email: EmailStr | None = None
    language: Language | None = None
    theme_preset: ThemePreset | None = None
    theme_surface: ThemeSurface | None = None
    theme_primary: ThemePrimary | None = None
    theme_dark_mode: bool | None = None
    amount_style: AmountStyle | None = None
    share_restrictions_with_hosts: bool | None = None
    # "public" only while the instance allows public recipes (422
    # PublicRecipesNotAllowedError otherwise), "peers" only while peering is
    # on (422 PeerRecipesNotAllowedError otherwise).
    default_recipe_visibility: (
        Literal["private", "household", "shared", "instance", "peers", "public"] | None
    ) = None
    show_name_on_public_recipes: bool | None = None
    show_name_on_paired_instances: bool | None = None
    recipe_show_tips: bool | None = None
    recipe_show_notes: bool | None = None
    recipe_show_cooked: bool | None = None
    recipe_show_rating: bool | None = None
    recipe_highlight_mentions: bool | None = None
    keep_screen_on: bool | None = None


class ChangePasswordRequest(RequestSchema):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class CreateUserRequest(RequestSchema):
    full_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
    permissions: list[str] = Field(default_factory=list)
    group_ids: list[UUID] = Field(default_factory=list)
    language: Language | None = None
    is_active: bool = True
    nickname: str | None = Field(default=None, max_length=64)
    show_nickname: bool = False


class UpdateUserRequest(RequestSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=128)
    # An empty string clears the nickname.
    nickname: str | None = Field(default=None, max_length=64)
    show_nickname: bool | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=1, max_length=1024)
    permissions: list[str] | None = None
    group_ids: list[UUID] | None = None
    language: Language | None = None
    is_active: bool | None = None


class PasswordConfirmationRequest(RequestSchema):
    password: str = Field(min_length=1, max_length=1024)
