from collections.abc import Collection
from typing import Any

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.user_models import UserGroupMemberModel
from src.platform.adapters.outbound.persistence.models.user_models import UserGroupModel
from src.platform.adapters.outbound.persistence.models.user_models import UserModel
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.const import SYSTEM_LOGIN
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.display import AmountStyle
from src.platform.domain.value_objects.language import Language
from src.platform.domain.value_objects.theme import ThemePreset
from src.platform.domain.value_objects.theme import ThemePrimary
from src.platform.domain.value_objects.theme import ThemeSurface


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _to_entities(self, rows: list[UserModel]) -> list[User]:
        """Maps rows and loads every user's groups in one query."""
        ids = [row.id for row in rows]
        memberships: dict[int, list[tuple[int, list[str]]]] = {i: [] for i in ids}
        if ids:
            result = await self._db.execute(
                select(UserGroupMemberModel.user_id, UserGroupModel.id, UserGroupModel.permissions)
                .join(UserGroupModel, UserGroupModel.id == UserGroupMemberModel.group_id)
                .where(UserGroupMemberModel.user_id.in_(ids))
            )
            for user_id, group_id, permissions in result.all():
                memberships[user_id].append((group_id, list(permissions or [])))
        return [self._map(row, memberships.get(row.id, [])) for row in rows]

    @staticmethod
    def _map(row: UserModel, groups: list[tuple[int, list[str]]]) -> User:
        group_permissions = sorted({p for _, perms in groups for p in perms})
        return User(
            id=row.id,
            public_id=row.public_id,
            full_name=row.full_name,
            email=row.email,
            created=row.created,
            nickname=row.nickname,
            show_nickname=row.show_nickname,
            hashed_password=row.hashed_password,
            is_active=row.is_active,
            is_systemuser=row.is_systemuser,
            is_service_account=row.is_service_account,
            permissions=list(row.permissions or []),
            language=Language(row.language),
            theme_preset=ThemePreset(row.theme_preset),
            theme_surface=ThemeSurface(row.theme_surface),
            theme_primary=ThemePrimary(row.theme_primary),
            theme_dark_mode=row.theme_dark_mode,
            amount_style=AmountStyle(row.amount_style),
            share_restrictions_with_hosts=row.share_restrictions_with_hosts,
            default_recipe_visibility=row.default_recipe_visibility,
            show_name_on_public_recipes=row.show_name_on_public_recipes,
            show_name_on_paired_instances=row.show_name_on_paired_instances,
            recipe_show_tips=row.recipe_show_tips,
            recipe_show_notes=row.recipe_show_notes,
            recipe_show_cooked=row.recipe_show_cooked,
            recipe_show_rating=row.recipe_show_rating,
            recipe_highlight_mentions=row.recipe_highlight_mentions,
            keep_screen_on=row.keep_screen_on,
            avatar_file_id=row.avatar_file_id,
            privacy_acknowledged_version=row.privacy_acknowledged_version,
            privacy_acknowledged_at=row.privacy_acknowledged_at,
            consent_health_data_at=row.consent_health_data_at,
            consent_ai_agents_at=row.consent_ai_agents_at,
            token_version=row.token_version,
            last_logged_in=row.last_logged_in,
            totp_secret=row.totp_secret,
            totp_enabled=row.totp_enabled,
            group_ids=sorted(group_id for group_id, _ in groups),
            group_permissions=group_permissions,
        )

    async def _one(self, row: UserModel | None) -> User | None:
        if row is None:
            return None
        return (await self._to_entities([row]))[0]

    async def get(self, user_id: int) -> User | None:
        return await self._one(await self._db.get(UserModel, user_id))

    async def get_by_public_id(self, public_id: str) -> User | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(UserModel).where(UserModel.public_id == uid))
        return await self._one(row)

    async def avatar_in_use(self, file_id: int) -> bool:
        count = await self._db.scalar(
            select(func.count()).select_from(UserModel).where(UserModel.avatar_file_id == file_id)
        )
        return bool(count)

    async def avatar_file_ids(self, file_ids: Collection[int]) -> set[int]:
        wanted = sorted(set(file_ids))
        found: set[int] = set()
        for start in range(0, len(wanted), 500):
            rows = await self._db.scalars(
                select(UserModel.avatar_file_id).where(
                    UserModel.avatar_file_id.in_(wanted[start : start + 500])
                )
            )
            found |= {f for f in rows.all() if f is not None}
        return found

    async def get_by_login(self, login: str) -> User | None:
        if login.strip().lower() == SYSTEM_LOGIN:
            row = await self._db.scalar(select(UserModel).where(UserModel.is_systemuser.is_(True)))
            return await self._one(row)
        return await self.get_by_email(login)

    async def get_by_email(self, email: str) -> User | None:
        needle = email.strip().lower()
        if not needle:
            return None
        row = await self._db.scalar(select(UserModel).where(func.lower(UserModel.email) == needle))
        return await self._one(row)

    async def _taken(self, column: Any, value: str, exclude_id: int | None) -> bool:
        query = (
            select(func.count())
            .select_from(UserModel)
            .where(func.lower(column) == value.strip().lower())
        )
        if exclude_id is not None:
            query = query.where(UserModel.id != exclude_id)
        return bool(await self._db.scalar(query))

    async def email_taken(self, email: str, exclude_id: int | None = None) -> bool:
        return await self._taken(UserModel.email, email, exclude_id)

    async def list_all(
        self,
        *,
        include_service_accounts: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[User]:
        """The accounts by name; `limit` and `offset` page through them in
        that order, and without a limit every account is returned."""
        query = select(UserModel).order_by(func.lower(UserModel.full_name), UserModel.id)
        if not include_service_accounts:
            query = query.where(UserModel.is_service_account.is_(False))
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        rows = list((await self._db.scalars(query)).all())
        return await self._to_entities(rows)

    async def save(self, user: User) -> User:
        row = await self._db.get(UserModel, user.id) if user.id else None
        if row is None:
            row = UserModel(public_id=user.public_id, created=user.created)
            self._db.add(row)
        row.full_name = user.full_name
        row.email = user.email
        row.nickname = user.nickname
        row.show_nickname = user.show_nickname
        row.hashed_password = user.hashed_password
        row.is_active = user.is_active
        row.is_systemuser = user.is_systemuser
        row.is_service_account = user.is_service_account
        row.permissions = sorted(set(user.permissions))
        row.language = user.language.value
        row.theme_preset = user.theme_preset.value
        row.theme_surface = user.theme_surface.value
        row.theme_primary = user.theme_primary.value
        row.theme_dark_mode = user.theme_dark_mode
        row.amount_style = user.amount_style.value
        row.share_restrictions_with_hosts = user.share_restrictions_with_hosts
        row.default_recipe_visibility = user.default_recipe_visibility
        row.show_name_on_public_recipes = user.show_name_on_public_recipes
        row.show_name_on_paired_instances = user.show_name_on_paired_instances
        row.recipe_show_tips = user.recipe_show_tips
        row.recipe_show_notes = user.recipe_show_notes
        row.recipe_show_cooked = user.recipe_show_cooked
        row.recipe_show_rating = user.recipe_show_rating
        row.recipe_highlight_mentions = user.recipe_highlight_mentions
        row.keep_screen_on = user.keep_screen_on
        row.avatar_file_id = user.avatar_file_id
        row.privacy_acknowledged_version = user.privacy_acknowledged_version
        row.privacy_acknowledged_at = user.privacy_acknowledged_at
        row.consent_health_data_at = user.consent_health_data_at
        row.consent_ai_agents_at = user.consent_ai_agents_at
        row.token_version = user.token_version
        row.last_logged_in = user.last_logged_in
        row.totp_secret = user.totp_secret
        row.totp_enabled = user.totp_enabled
        await self._db.flush()
        await self._db.execute(
            delete(UserGroupMemberModel).where(UserGroupMemberModel.user_id == row.id)
        )
        for group_id in sorted(set(user.group_ids)):
            self._db.add(UserGroupMemberModel(user_id=row.id, group_id=group_id))
        await self._db.flush()
        stored = await self._one(row)
        assert stored is not None
        return stored

    async def delete(self, user: User) -> None:
        row = await self._db.get(UserModel, user.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()
