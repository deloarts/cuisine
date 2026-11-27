"""
The connected apps of a person: the OAuth grants they approved, which they
list and revoke on their account page. Revoking a grant ends its access and
refresh tokens at once, so the app's next call is refused.
"""

from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.oauth import OAuthClient
from src.platform.domain.entities.oauth import OAuthGrant
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import OAuthGrantNotFoundError
from src.platform.domain.services.oauth_rules import ENDED_GRANT_RETENTION
from src.platform.domain.services.oauth_rules import UNUSED_CLIENT_LIFETIME
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthClientRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthGrantRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthTokenRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class ConnectedApp:
    grant: OAuthGrant
    client: OAuthClient | None


async def end_grant(
    grant: OAuthGrant,
    *,
    grants: IOAuthGrantRepository,
    tokens: IOAuthTokenRepository,
    now: datetime,
) -> None:
    """Marks the grant revoked and revokes every token it issued. The caller
    records the reason and commits."""
    grant.revoked_at = now
    await grants.save(grant)
    await tokens.revoke_for_grant(grant.id, now)


class ManageOwnOAuthGrants:
    def __init__(
        self,
        *,
        grant_repo: IOAuthGrantRepository,
        token_repo: IOAuthTokenRepository,
        client_repo: IOAuthClientRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._grants = grant_repo
        self._tokens = token_repo
        self._clients = client_repo
        self._audit = audit
        self._uow = uow

    async def list_all(self, user: User) -> list[ConnectedApp]:
        grants = await self._grants.list_active_for_user(user.id)
        clients: dict[int, OAuthClient | None] = {}
        for grant in grants:
            if grant.client_id not in clients:
                clients[grant.client_id] = await self._clients.get(grant.client_id)
        return [ConnectedApp(grant=g, client=clients[g.client_id]) for g in grants]

    async def revoke(self, user: User, public_id: str, *, context: RequestContext) -> None:
        grant = await self._grants.get_by_public_id(public_id)
        if grant is None or grant.user_id != user.id or grant.revoked_at is not None:
            raise OAuthGrantNotFoundError("No such connected app.")
        client = await self._clients.get(grant.client_id)
        await end_grant(grant, grants=self._grants, tokens=self._tokens, now=now_utc())
        await self._audit.record(
            SecurityEventType.OAUTH_GRANT_REVOKED,
            actor=user,
            target=user,
            context=context,
            detail={"client": client.name if client else None},
        )
        await self._uow.commit()

    async def revoke_all(self, user: User, *, reason: str, context: RequestContext) -> int:
        """Ends every connected app of the user, for a caller that commits
        (withdrawing the AI agents consent)."""
        now = now_utc()
        grants = await self._grants.list_active_for_user(user.id)
        for grant in grants:
            client = await self._clients.get(grant.client_id)
            await end_grant(grant, grants=self._grants, tokens=self._tokens, now=now)
            await self._audit.record(
                SecurityEventType.OAUTH_GRANT_REVOKED,
                actor=user,
                target=user,
                context=context,
                detail={"client": client.name if client else None, "reason": reason},
            )
        return len(grants)


class PurgeOAuthRecords:
    """Removes expired tokens, grants that ended a week ago and clients
    nobody approved within a day. Runs with the nightly retention purge,
    which commits."""

    def __init__(
        self,
        *,
        client_repo: IOAuthClientRepository,
        grant_repo: IOAuthGrantRepository,
        token_repo: IOAuthTokenRepository,
    ) -> None:
        self._clients = client_repo
        self._grants = grant_repo
        self._tokens = token_repo

    async def __call__(self, _retention: RetentionSettings) -> int:
        now = now_utc()
        removed = await self._tokens.delete_expired(now)
        removed += await self._grants.delete_ended(now - ENDED_GRANT_RETENTION)
        removed += await self._clients.delete_unused(now - UNUSED_CLIENT_LIFETIME)
        return removed
