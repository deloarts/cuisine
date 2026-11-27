"""Repositories of the OAuth clients, grants and tokens."""

from datetime import datetime

from sqlalchemy import delete
from sqlalchemy import exists
from sqlalchemy import or_
from sqlalchemy import update

from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthClientModel
from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthGrantModel
from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthTokenModel
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    _SimpleRepository,
)
from src.platform.domain.entities.oauth import OAuthClient
from src.platform.domain.entities.oauth import OAuthGrant
from src.platform.domain.entities.oauth import OAuthToken
from src.shared_kernel.domain.services.clock import now_utc


class SqlAlchemyOAuthClientRepository(_SimpleRepository[OAuthClient, OAuthClientModel]):
    entity_cls = OAuthClient
    model_cls = OAuthClientModel

    async def get(self, client_pk: int) -> OAuthClient | None:
        return self._entity(await self._db.get(OAuthClientModel, client_pk))

    async def get_by_client_id(self, client_id: str) -> OAuthClient | None:
        return await self._first(OAuthClientModel.client_id == client_id)

    async def delete_unused(self, created_before: datetime) -> int:
        has_grant = exists().where(OAuthGrantModel.client_id == OAuthClientModel.id)
        result = await self._db.execute(
            delete(OAuthClientModel).where(OAuthClientModel.created < created_before, ~has_grant)
        )
        await self._db.flush()
        return int(getattr(result, "rowcount", 0) or 0)


class SqlAlchemyOAuthGrantRepository(_SimpleRepository[OAuthGrant, OAuthGrantModel]):
    entity_cls = OAuthGrant
    model_cls = OAuthGrantModel

    async def get(self, grant_id: int) -> OAuthGrant | None:
        return self._entity(await self._db.get(OAuthGrantModel, grant_id))

    async def list_active_for_user(self, user_id: int) -> list[OAuthGrant]:
        now = now_utc()
        return await self._all(
            OAuthGrantModel.user_id == user_id,
            OAuthGrantModel.revoked_at.is_(None),
            or_(OAuthGrantModel.expires_at.is_(None), OAuthGrantModel.expires_at > now),
            order_by=OAuthGrantModel.created.desc(),
        )

    async def delete_ended(self, ended_before: datetime) -> int:
        # The tokens go with their grant through ON DELETE CASCADE.
        result = await self._db.execute(
            delete(OAuthGrantModel).where(
                or_(
                    OAuthGrantModel.revoked_at < ended_before,
                    OAuthGrantModel.expires_at < ended_before,
                )
            )
        )
        await self._db.flush()
        return int(getattr(result, "rowcount", 0) or 0)


class SqlAlchemyOAuthTokenRepository(_SimpleRepository[OAuthToken, OAuthTokenModel]):
    entity_cls = OAuthToken
    model_cls = OAuthTokenModel

    async def get_by_token_hash(self, token_hash: str) -> OAuthToken | None:
        return await self._first(OAuthTokenModel.token_hash == token_hash)

    async def revoke_for_grant(self, grant_id: int, now: datetime) -> int:
        result = await self._db.execute(
            update(OAuthTokenModel)
            .where(OAuthTokenModel.grant_id == grant_id, OAuthTokenModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self._db.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_expired(self, expired_before: datetime) -> int:
        result = await self._db.execute(
            delete(OAuthTokenModel).where(OAuthTokenModel.expires_at < expired_before)
        )
        await self._db.flush()
        return int(getattr(result, "rowcount", 0) or 0)
