"""
Account administration. There is no open sign-up: an administrator with
write:users creates every account.

Nobody can grant more than they hold. Adding direct permissions or putting
a user into a group is checked against the acting administrator's own
permissions, so write:users alone never escalates. Acting on an account,
by changing its address, password, avatar, activity, permissions or
groups, by resetting its two-factor authentication, signing it out or
deleting it,
needs every effective permission of that account (`assert_may_manage`),
so write:users never reaches an account with more rights than the actor.
The system user cannot be deleted, deactivated or changed by anyone but
itself, so the instance always keeps an administrator.

A new account gets the welcome mail in its language when mail is set up.
It names the sign-in address and never the password, which the
administrator hands over themselves.
"""

import logging
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.mailer import Mailer
from src.platform.application.services.mailer import content_locale
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.services.webhook_publisher import WebhookPublisher
from src.platform.application.use_cases.account.avatar import delete_avatar_of
from src.platform.application.use_cases.account.avatar import remove_avatar_of
from src.platform.application.use_cases.account.avatar import replace_avatar_of
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import DuplicateUserError
from src.platform.domain.exceptions import SystemUserProtectedError
from src.platform.domain.exceptions import UserGroupNotFoundError
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.domain.services.password_rules import assert_password_acceptable
from src.platform.domain.services.permission_rules import assert_grantable_by
from src.platform.domain.services.permission_rules import assert_may_manage
from src.platform.domain.value_objects.language import Language
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.domain.value_objects.webhook_event import USER_CREATED
from src.platform.domain.value_objects.webhook_event import USER_DELETED
from src.platform.ports.outbound.image_processor import IImageProcessor
from src.platform.ports.outbound.password_hasher import IPasswordHasher
from src.platform.ports.outbound.repositories.api_key_repository import IApiKeyRepository
from src.platform.ports.outbound.repositories.security_event_repository import (
    ISecurityEventRepository,
)
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.trusted_device_repository import (
    ITrustedDeviceRepository,
)
from src.platform.ports.outbound.repositories.user_group_repository import IUserGroupRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

log = logging.getLogger("cuisine")


@dataclass(frozen=True)
class CreateUserCommand:
    full_name: str
    email: str
    password: str
    permissions: list[str]
    group_ids: list[str]
    language: Language | None = None
    is_active: bool = True
    nickname: str | None = None
    show_nickname: bool = False


@dataclass(frozen=True)
class UpdateUserCommand:
    """Every field is optional; None leaves it as it is. A password sets a
    new one and signs the user out everywhere."""

    full_name: str | None = None
    # An empty string clears the nickname.
    nickname: str | None = None
    show_nickname: bool | None = None
    email: str | None = None
    password: str | None = None
    permissions: list[str] | None = None
    group_ids: list[str] | None = None
    language: Language | None = None
    is_active: bool | None = None


class ManageUsers:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        group_repo: IUserGroupRepository,
        session_repo: IUserSessionRepository,
        trusted_device_repo: ITrustedDeviceRepository,
        settings_repo: ISettingsRepository,
        hasher: IPasswordHasher,
        key_repo: IApiKeyRepository,
        event_repo: ISecurityEventRepository,
        file_repo: IStoredFileRepository,
        images: IImageProcessor,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        webhooks: WebhookPublisher | None = None,
        mailer: Mailer | None = None,
    ) -> None:
        self._mailer = mailer
        self._files = file_repo
        self._images = images
        self._webhooks = webhooks
        self._users = user_repo
        self._groups = group_repo
        self._sessions = session_repo
        self._devices = trusted_device_repo
        self._settings = settings_repo
        self._hasher = hasher
        self._keys = key_repo
        self._events = event_repo
        self._audit = audit
        self._uow = uow

    async def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[User]:
        return await self._users.list_all(limit=limit, offset=offset)

    async def get(self, public_id: str) -> User:
        user = await self._users.get_by_public_id(public_id)
        if user is None or user.is_service_account:
            raise UserNotFoundError("No such user.")
        return user

    async def _resolve_groups(self, actor: User, public_ids: list[str]) -> list[int]:
        groups = await self._groups.get_many_by_public_id(public_ids)
        if len(groups) != len(set(public_ids)):
            raise UserGroupNotFoundError("One of the groups does not exist.")
        for group in groups:
            assert_grantable_by(actor, group.permissions)
        return [g.id for g in groups]

    async def _assert_unique(self, email: str, exclude_id: int | None) -> None:
        if await self._users.email_taken(email, exclude_id):
            raise DuplicateUserError("This e-mail address is already in use.")

    async def create(self, actor: User, cmd: CreateUserCommand, *, context: RequestContext) -> User:
        email = cmd.email.strip()
        await self._assert_unique(email, None)
        security = await self._settings.get_security()
        assert_password_acceptable(cmd.password, security.min_password_length, email=email)
        assert_grantable_by(actor, cmd.permissions)
        group_ids = await self._resolve_groups(actor, cmd.group_ids)
        language = cmd.language or (await self._settings.get_general()).default_language
        user = await self._users.save(
            User(
                full_name=cmd.full_name.strip(),
                nickname=(cmd.nickname or "").strip() or None,
                show_nickname=cmd.show_nickname,
                email=email,
                created=now_utc(),
                hashed_password=await self._hasher.hash(cmd.password),
                is_active=cmd.is_active,
                permissions=sorted(set(cmd.permissions)),
                group_ids=group_ids,
                language=language,
            )
        )
        await self._audit.record(
            SecurityEventType.USER_CREATED, actor=actor, target=user, context=context
        )
        if self._webhooks is not None:
            # The delivery names the new user, so deleting them deletes it.
            await self._webhooks.publish(
                USER_CREATED.key,
                {
                    "user": {
                        "id": str(user.public_id),
                        "full_name": user.full_name,
                    }
                },
                subject_user_id=user.id,
            )
        await self._uow.commit()
        await self._send_welcome(actor, user)
        return user

    async def _send_welcome(self, actor: User, user: User) -> None:
        """Mails the welcome template to the new account. It runs after the
        commit and never raises: the account exists either way, and the
        administrator can still tell the person by hand."""
        if self._mailer is None or not user.is_active:
            return
        settings = await self._settings.get_mail()
        if not settings.enabled:
            return
        try:
            await self._mailer.send_template(
                MailTemplateKind.USER_CREATED,
                to=user.email,
                locale=content_locale(user.language.value),
                context={
                    "full_name": user.full_name,
                    "email": user.email,
                    "login_url": self._mailer.link("/login"),
                    "created_by": actor.full_name,
                },
            )
        except Exception:
            log.warning("The welcome mail for a new account could not be sent.", exc_info=True)

    async def update(
        self, actor: User, public_id: str, cmd: UpdateUserCommand, *, context: RequestContext
    ) -> User:
        user = await self.get(public_id)
        if user.is_systemuser and actor.id != user.id:
            raise SystemUserProtectedError("Only the system user can change itself.")
        email = cmd.email.strip() if cmd.email is not None else user.email
        if email != user.email:
            assert_may_manage(actor, user)
        await self._assert_unique(email, user.id)
        user.email = email
        if cmd.full_name is not None:
            user.full_name = cmd.full_name.strip()
        if cmd.nickname is not None:
            user.nickname = cmd.nickname.strip() or None
        if cmd.show_nickname is not None:
            user.show_nickname = cmd.show_nickname
        if cmd.language is not None:
            user.language = cmd.language
        events: list[tuple[SecurityEventType, dict[str, object]]] = []
        logout = False

        if cmd.permissions is not None and set(cmd.permissions) != set(user.permissions):
            if user.is_systemuser:
                raise SystemUserProtectedError("The system user always holds every permission.")
            # Removing a permission needs it as much as adding one does:
            # assert_may_manage covers what the account holds now.
            assert_may_manage(actor, user)
            assert_grantable_by(actor, set(cmd.permissions) - set(user.permissions))
            events.append(
                (
                    SecurityEventType.USER_PERMISSIONS_CHANGED,
                    {"before": sorted(user.permissions), "after": sorted(set(cmd.permissions))},
                )
            )
            user.permissions = sorted(set(cmd.permissions))
        if cmd.group_ids is not None:
            current = set(user.group_ids)
            wanted = set(await self._resolve_groups(actor, cmd.group_ids))
            if wanted != current:
                assert_may_manage(actor, user)
                events.append(
                    (
                        SecurityEventType.USER_GROUPS_CHANGED,
                        {"before": sorted(current), "after": sorted(wanted)},
                    )
                )
                user.group_ids = sorted(wanted)
        if cmd.is_active is not None and cmd.is_active != user.is_active:
            if user.is_systemuser or user.id == actor.id:
                raise SystemUserProtectedError("You cannot deactivate this account.")
            assert_may_manage(actor, user)
            user.is_active = cmd.is_active
            events.append(
                (
                    SecurityEventType.USER_REACTIVATED
                    if cmd.is_active
                    else SecurityEventType.USER_DEACTIVATED,
                    {},
                )
            )
            logout = not cmd.is_active
        if cmd.password is not None:
            assert_may_manage(actor, user)
            security = await self._settings.get_security()
            assert_password_acceptable(cmd.password, security.min_password_length, email=user.email)
            user.hashed_password = await self._hasher.hash(cmd.password)
            events.append((SecurityEventType.PASSWORD_CHANGED, {"by_admin": True}))
            logout = True
        if logout:
            await self._end_everything(user)

        saved = await self._users.save(user)
        events.append((SecurityEventType.USER_CHANGED, {}))
        for event_type, detail in events:
            await self._audit.record(
                event_type, actor=actor, target=saved, context=context, detail=detail
            )
        await self._uow.commit()
        return saved

    async def delete(
        self,
        actor: User,
        public_id: str,
        *,
        context: RequestContext,
        before_delete: Callable[[User], Awaitable[None]] | None = None,
    ) -> None:
        """Deletes the account without a trace. `before_delete` lets the
        cookbook hand over or remove the user's data in the same
        transaction. Credentials, the avatar, sessions, devices, tokens, the
        API keys the user created with their service accounts, group
        memberships and every security event involving the user go; one event remains,
        "a user account was deleted", naming the acting administrator only."""
        user = await self.get(public_id)
        if user.is_systemuser or user.id == actor.id or user.is_service_account:
            raise SystemUserProtectedError("You cannot delete this account.")
        assert_may_manage(actor, user)
        if before_delete is not None:
            await before_delete(user)
        for key in await self._keys.list_all():
            if key.creator_id == user.id:
                service = await self._users.get(key.service_user_id)
                if service is not None:
                    await self._events.delete_involving(service.id)
                    await self._users.delete(service)
        await self._events.delete_involving(user.id)
        await delete_avatar_of(self._files, user)
        await self._users.delete(user)
        await self._audit.record(
            SecurityEventType.USER_DELETED, actor=actor, context=context, detail={}
        )
        if self._webhooks is not None:
            # Nothing about the person: no id, no name.
            await self._webhooks.publish(USER_DELETED.key, {})
        await self._uow.commit()

    async def _avatar_target(self, actor: User, public_id: str) -> User:
        user = await self.get(public_id)
        if user.is_systemuser and actor.id != user.id:
            raise SystemUserProtectedError("Only the system user can change itself.")
        assert_may_manage(actor, user)
        return user

    async def replace_avatar(
        self,
        actor: User,
        public_id: str,
        *,
        data: bytes,
        file_name: str,
        content_type: str,
        context: RequestContext,
    ) -> User:
        """Sets someone's avatar, such as a photo the person sent in. The
        image belongs to the user, as if they had uploaded it."""
        user = await self._avatar_target(actor, public_id)
        saved = await replace_avatar_of(
            self._files,
            self._images,
            self._users,
            user,
            data=data,
            file_name=file_name,
            content_type=content_type,
        )
        await self._audit.record(
            SecurityEventType.USER_CHANGED, actor=actor, target=saved, context=context
        )
        await self._uow.commit()
        return saved

    async def remove_avatar(self, actor: User, public_id: str, *, context: RequestContext) -> User:
        """Removes someone's avatar, such as an unsuitable picture."""
        user = await self._avatar_target(actor, public_id)
        saved = await remove_avatar_of(self._files, self._users, user)
        await self._audit.record(
            SecurityEventType.USER_CHANGED, actor=actor, target=saved, context=context
        )
        await self._uow.commit()
        return saved

    async def reset_totp(self, actor: User, public_id: str, *, context: RequestContext) -> User:
        """For a user who lost their authenticator: two-factor goes off and
        their trusted devices are forgotten. With enforcement on, the next
        login walks them through enrolment again."""
        user = await self.get(public_id)
        if user.is_systemuser:
            raise SystemUserProtectedError(
                "Two-factor authentication of the system user can only be reset with "
                "`admin reset-totp system` on the server."
            )
        assert_may_manage(actor, user)
        user.totp_enabled = False
        user.totp_secret = None
        await self._devices.revoke_all(user.id, now_utc())
        saved = await self._users.save(user)
        await self._audit.record(
            SecurityEventType.TOTP_RESET, actor=actor, target=saved, context=context
        )
        await self._uow.commit()
        return saved

    async def force_logout(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        """Ends every session and token of the account. The system user can
        only be signed out by itself, which `assert_may_manage` enforces."""
        user = await self.get(public_id)
        assert_may_manage(actor, user)
        await self._end_everything(user)
        await self._users.save(user)
        await self._audit.record(
            SecurityEventType.USER_FORCED_LOGOUT, actor=actor, target=user, context=context
        )
        await self._uow.commit()

    async def _end_everything(self, user: User) -> None:
        """Every session and every token signed before ends."""
        user.token_version += 1
        await self._sessions.revoke_all(user.id, now_utc())
