from datetime import datetime
from uuid import UUID

from sqlalchemy import case
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.peer_models import PeerInvitationModel
from src.platform.adapters.outbound.persistence.models.peer_models import PeerModel
from src.platform.adapters.outbound.persistence.repositories._common import copy_entity_to_row
from src.platform.adapters.outbound.persistence.repositories._common import entity_from_row
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.domain.entities.peer import MirrorVisibility
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer import PeerInvitation
from src.platform.domain.entities.peer import PeerRevokedBy
from src.platform.domain.entities.peer import PeerStatus


def _peer(row: PeerModel) -> Peer:
    try:
        visibility = MirrorVisibility(row.mirror_visibility)
    except ValueError:
        # An unknown value reads as the group choice without a group, which
        # shows mirrors to nobody: the safe side.
        visibility = MirrorVisibility.GROUP
    return Peer(
        id=row.id,
        public_id=row.public_id,
        instance_id=row.instance_id,
        name=row.name,
        base_url=row.base_url,
        app_version=row.app_version,
        protocol_version=row.protocol_version,
        format_versions={
            str(k): int(v) for k, v in dict(row.format_versions or {}).items() if isinstance(v, int)
        },
        capabilities=[str(c) for c in row.capabilities or []],
        status=PeerStatus(row.status),
        revoked_by=PeerRevokedBy(row.revoked_by) if row.revoked_by else None,
        # Empty when no configured key decrypts it, which fails every
        # signature until the pairing is renewed.
        inbound_secret=row.inbound_secret or "",
        outbound_secret=row.outbound_secret or "",
        users_may_share=row.users_may_share,
        accept_incoming=row.accept_incoming,
        sync_all=row.sync_all,
        mirror_visibility=visibility,
        mirror_group_id=row.mirror_group_id if visibility == MirrorVisibility.GROUP else None,
        created=row.created,
        paired_at=row.paired_at,
        revoked_at=row.revoked_at,
        last_contact_at=row.last_contact_at,
        changed=row.changed,
    )


class SqlAlchemyPeerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_all(self) -> list[Peer]:
        rows = await self._db.scalars(
            select(PeerModel).order_by(
                case((PeerModel.status == PeerStatus.ACTIVE.value, 0), else_=1), PeerModel.name
            )
        )
        return [_peer(r) for r in rows.all()]

    async def list_active(self) -> list[Peer]:
        rows = await self._db.scalars(
            select(PeerModel)
            .where(PeerModel.status == PeerStatus.ACTIVE.value)
            .order_by(PeerModel.id)
        )
        return [_peer(r) for r in rows.all()]

    async def get(self, peer_id: int) -> Peer | None:
        row = await self._db.get(PeerModel, peer_id, populate_existing=True)
        return _peer(row) if row is not None else None

    async def touch_contact(self, peer_id: int, at: datetime) -> None:
        # One column, so a request that only proves contact never
        # overwrites what another request changed on the record.
        await self._db.execute(
            update(PeerModel)
            .where(PeerModel.id == peer_id)
            .values(last_contact_at=at)
            .execution_options(synchronize_session=False)
        )

    async def get_by_public_id(self, public_id: str) -> Peer | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(PeerModel).where(PeerModel.public_id == uid))
        return _peer(row) if row is not None else None

    async def get_by_instance_id(self, instance_id: UUID) -> Peer | None:
        row = await self._db.scalar(select(PeerModel).where(PeerModel.instance_id == instance_id))
        return _peer(row) if row is not None else None

    async def save(self, peer: Peer) -> Peer:
        row = await self._db.get(PeerModel, peer.id) if peer.id else None
        if row is None:
            row = PeerModel(public_id=peer.public_id)
            self._db.add(row)
        row.instance_id = peer.instance_id
        row.name = peer.name
        row.base_url = peer.base_url
        row.app_version = peer.app_version
        row.protocol_version = peer.protocol_version
        row.format_versions = dict(peer.format_versions)
        row.capabilities = list(peer.capabilities)
        row.status = peer.status.value
        row.revoked_by = peer.revoked_by.value if peer.revoked_by else None
        row.inbound_secret = peer.inbound_secret
        row.outbound_secret = peer.outbound_secret
        row.users_may_share = peer.users_may_share
        row.accept_incoming = peer.accept_incoming
        row.sync_all = peer.sync_all
        row.mirror_visibility = peer.mirror_visibility.value
        row.mirror_group_id = peer.mirror_group_id
        row.created = peer.created
        row.paired_at = peer.paired_at
        row.revoked_at = peer.revoked_at
        row.last_contact_at = peer.last_contact_at
        row.changed = peer.changed
        await self._db.flush()
        return _peer(row)


class SqlAlchemyPeerInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, invitation: PeerInvitation) -> PeerInvitation:
        row = PeerInvitationModel(public_id=invitation.public_id)
        copy_entity_to_row(invitation, row, skip=frozenset())
        self._db.add(row)
        await self._db.flush()
        return entity_from_row(PeerInvitation, row)

    async def get_by_public_id(self, public_id: str) -> PeerInvitation | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(PeerInvitationModel).where(PeerInvitationModel.public_id == uid)
        )
        return entity_from_row(PeerInvitation, row) if row is not None else None

    async def get_by_code_hash(self, code_hash: str) -> PeerInvitation | None:
        row = await self._db.scalar(
            select(PeerInvitationModel).where(PeerInvitationModel.code_hash == code_hash)
        )
        return entity_from_row(PeerInvitation, row) if row is not None else None

    async def list_open(self, now: datetime) -> list[PeerInvitation]:
        rows = await self._db.scalars(
            select(PeerInvitationModel)
            .where(PeerInvitationModel.used_at.is_(None), PeerInvitationModel.expires_at > now)
            .order_by(PeerInvitationModel.created.desc(), PeerInvitationModel.id.desc())
        )
        return [entity_from_row(PeerInvitation, r) for r in rows.all()]

    async def claim(self, invitation: PeerInvitation, *, peer_id: int, now: datetime) -> bool:
        result = await self._db.execute(
            update(PeerInvitationModel)
            .where(PeerInvitationModel.id == invitation.id, PeerInvitationModel.used_at.is_(None))
            .values(used_at=now, peer_id=peer_id)
            .execution_options(synchronize_session=False)
        )
        claimed = bool(getattr(result, "rowcount", 0))
        if claimed:
            invitation.used_at = now
            invitation.peer_id = peer_id
        return claimed

    async def delete(self, invitation: PeerInvitation) -> None:
        await self._db.execute(
            delete(PeerInvitationModel).where(PeerInvitationModel.id == invitation.id)
        )
        await self._db.flush()

    async def purge_expired_before(self, cutoff: datetime) -> int:
        result = await self._db.execute(
            delete(PeerInvitationModel).where(PeerInvitationModel.expires_at < cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)
