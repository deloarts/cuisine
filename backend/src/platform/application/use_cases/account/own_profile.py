"""The signed-in user's own profile, preferences and password."""

from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.oauth.grants import ManageOwnOAuthGrants
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import DuplicateUserError
from src.platform.domain.exceptions import PasswordConfirmationError
from src.platform.domain.exceptions import PeerRecipesNotAllowedError
from src.platform.domain.exceptions import PublicRecipesNotAllowedError
from src.platform.domain.services.password_rules import assert_password_acceptable
from src.platform.domain.value_objects.display import AmountStyle
from src.platform.domain.value_objects.language import Language
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.domain.value_objects.theme import ThemePreset
from src.platform.domain.value_objects.theme import ThemePrimary
from src.platform.domain.value_objects.theme import ThemeSurface
from src.platform.ports.outbound.password_hasher import IPasswordHasher
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class UpdateOwnProfileCommand:
    """Every field is optional; None leaves it as it is."""

    full_name: str | None = None
    # An empty string clears the nickname.
    nickname: str | None = None
    show_nickname: bool | None = None
    email: str | None = None
    language: Language | None = None
    theme_preset: ThemePreset | None = None
    theme_surface: ThemeSurface | None = None
    theme_primary: ThemePrimary | None = None
    theme_dark_mode: bool | None = None
    amount_style: AmountStyle | None = None
    share_restrictions_with_hosts: bool | None = None
    default_recipe_visibility: str | None = None
    show_name_on_public_recipes: bool | None = None
    show_name_on_paired_instances: bool | None = None
    recipe_show_tips: bool | None = None
    recipe_show_notes: bool | None = None
    recipe_show_cooked: bool | None = None
    recipe_show_rating: bool | None = None
    recipe_highlight_mentions: bool | None = None
    keep_screen_on: bool | None = None


class UpdateOwnProfile:
    def __init__(
        self, *, user_repo: IUserRepository, settings_repo: ISettingsRepository, uow: IUnitOfWork
    ) -> None:
        self._users = user_repo
        self._settings = settings_repo
        self._uow = uow

    async def execute(self, user: User, cmd: UpdateOwnProfileCommand) -> User:
        if cmd.email is not None and cmd.email.strip().lower() != user.email.lower():
            if await self._users.email_taken(cmd.email, exclude_id=user.id):
                raise DuplicateUserError("This e-mail address is already in use.")
            user.email = cmd.email.strip()
        if cmd.full_name is not None:
            user.full_name = cmd.full_name.strip()
        if cmd.nickname is not None:
            user.nickname = cmd.nickname.strip() or None
        if (
            cmd.default_recipe_visibility == "public"
            and user.default_recipe_visibility != "public"
            and not (await self._settings.get_privacy()).allow_public_recipes
        ):
            raise PublicRecipesNotAllowedError(
                "Public recipes are not allowed on this instance, so they cannot be your default."
            )
        if (
            cmd.default_recipe_visibility == "peers"
            and user.default_recipe_visibility != "peers"
            and not (await self._settings.get_features()).peering
        ):
            raise PeerRecipesNotAllowedError(
                "Peering is off on this instance, so paired instances cannot be your default."
            )
        for name in (
            "language",
            "theme_preset",
            "theme_surface",
            "theme_primary",
            "theme_dark_mode",
            "amount_style",
            "show_nickname",
            "share_restrictions_with_hosts",
            "default_recipe_visibility",
            "show_name_on_public_recipes",
            "show_name_on_paired_instances",
            "recipe_show_tips",
            "recipe_show_notes",
            "recipe_show_cooked",
            "recipe_show_rating",
            "recipe_highlight_mentions",
            "keep_screen_on",
        ):
            value = getattr(cmd, name)
            if value is not None:
                setattr(user, name, value)
        saved = await self._users.save(user)
        await self._uow.commit()
        return saved


class ChangeOwnPassword:
    """Needs the current password. Every other session of the user ends and
    every connected OAuth app is revoked, so a password change also throws
    out whoever might have the old one or approved an app with a stolen
    session. The token version stays, so the current session lives on."""

    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        session_repo: IUserSessionRepository,
        settings_repo: ISettingsRepository,
        hasher: IPasswordHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        oauth_grants: ManageOwnOAuthGrants | None = None,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._settings = settings_repo
        self._hasher = hasher
        self._audit = audit
        self._uow = uow
        self._oauth_grants = oauth_grants

    async def execute(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        current_session_id: str | None,
        context: RequestContext,
    ) -> None:
        if not await self._hasher.verify(current_password, user.hashed_password):
            await self._audit.record(
                SecurityEventType.PASSWORD_CONFIRMATION,
                actor=user,
                target=user,
                context=context,
                outcome=SecurityEventOutcome.FAILURE,
            )
            await self._uow.commit()
            raise PasswordConfirmationError("The current password is wrong.")
        security = await self._settings.get_security()
        assert_password_acceptable(new_password, security.min_password_length, email=user.email)
        user.hashed_password = await self._hasher.hash(new_password)
        await self._users.save(user)
        await self._sessions.revoke_all(user.id, now_utc(), except_public_id=current_session_id)
        if self._oauth_grants is not None:
            await self._oauth_grants.revoke_all(user, reason="password_changed", context=context)
        await self._audit.record(
            SecurityEventType.PASSWORD_CHANGED, actor=user, target=user, context=context
        )
        await self._uow.commit()


async def confirm_password(
    hasher: IPasswordHasher,
    audit: SecurityAudit,
    uow: IUnitOfWork,
    user: User,
    password: str,
    context: RequestContext,
) -> None:
    """Raises PasswordConfirmationError, logged as a failed confirmation,
    unless `password` is the user's current password."""
    if await hasher.verify(password, user.hashed_password):
        return
    await audit.record(
        SecurityEventType.PASSWORD_CONFIRMATION,
        actor=user,
        target=user,
        context=context,
        outcome=SecurityEventOutcome.FAILURE,
    )
    await uow.commit()
    raise PasswordConfirmationError("The password is wrong.")
