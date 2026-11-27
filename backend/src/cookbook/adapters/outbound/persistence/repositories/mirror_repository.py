"""Mirrors, recipes waiting for a decision and catalogue mappings of paired
instances (`models/mirror_models.py`)."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.mirror_models import IncomingRecipeModel
from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerCatalogueMappingModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerSuggestionDismissalModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import RecipeMirrorModel
from src.cookbook.domain.entities.mirror import CatalogueMapping
from src.cookbook.domain.entities.mirror import IncomingKind
from src.cookbook.domain.entities.mirror import IncomingRecipe
from src.cookbook.domain.entities.mirror import IncomingStatus
from src.cookbook.domain.entities.mirror import MappingAction
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.mirror import RecipeMirror
from src.cookbook.domain.entities.mirror import SuggestionDismissal
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id

# The column holding the local entry of each kind of mapping.
_LOCAL = {
    MappingKind.UNIT: "unit_id",
    MappingKind.TAG: "tag_id",
    MappingKind.INGREDIENT: "ingredient_id",
    MappingKind.EQUIPMENT: "equipment_id",
}


def _mirror(row: RecipeMirrorModel) -> RecipeMirror:
    return RecipeMirror(
        recipe_id=row.recipe_id,
        peer_id=row.peer_id,
        origin_public_id=row.origin_public_id,
        etag=row.etag,
        source_revision=row.source_revision,
        source_author_name=row.source_author_name,
        document=dict(row.document or {}),
        files={str(k): str(v) for k, v in (row.files or {}).items()},
        extras=dict(row.extras or {}),
        accepted_at=row.accepted_at,
        updated_at=row.updated_at,
    )


def _incoming(row: IncomingRecipeModel) -> IncomingRecipe:
    return IncomingRecipe(
        id=row.id,
        public_id=row.public_id,
        peer_id=row.peer_id,
        origin_public_id=row.origin_public_id,
        status=IncomingStatus(row.status),
        kind=IncomingKind(row.kind),
        title=row.title,
        author_name=row.author_name,
        etag=row.etag,
        payload=bytes(row.payload),
        received_at=row.received_at,
        decided_at=row.decided_at,
    )


def _mapping(row: PeerCatalogueMappingModel) -> CatalogueMapping:
    kind = MappingKind(row.kind)
    local: Any = getattr(row, _LOCAL[kind])
    return CatalogueMapping(
        peer_id=row.peer_id,
        kind=kind,
        remote_id=row.remote_public_id,
        action=MappingAction(row.action) if row.action else None,
        local_id=local,
        created_here=row.created_here,
        matched_by=row.matched_by,
        remote_name=row.remote_name,
        remote_data=dict(row.remote_data or {}),
        updated=row.updated,
    )


class SqlAlchemyMirrorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    # ── Mirrors ──────────────────────────────────────────────────────

    async def get(self, recipe_id: int) -> RecipeMirror | None:
        row = await self._db.get(RecipeMirrorModel, recipe_id)
        return _mirror(row) if row is not None else None

    async def by_origin(self, peer_id: int, origin_public_id: UUID) -> RecipeMirror | None:
        row = await self._db.scalar(
            select(RecipeMirrorModel).where(
                RecipeMirrorModel.peer_id == peer_id,
                RecipeMirrorModel.origin_public_id == origin_public_id,
            )
        )
        return _mirror(row) if row is not None else None

    async def for_peer(self, peer_id: int) -> list[RecipeMirror]:
        rows = await self._db.scalars(
            select(RecipeMirrorModel)
            .where(RecipeMirrorModel.peer_id == peer_id)
            .order_by(RecipeMirrorModel.recipe_id)
        )
        return [_mirror(r) for r in rows.all()]

    async def with_author_avatar(self, file_public_id: str) -> list[int]:
        # The avatars sit in the extras JSON, whose shape differs between
        # SQLite and Postgres, so the few mirrors are scanned here.
        wanted = file_public_id.lower()
        rows = await self._db.execute(select(RecipeMirrorModel.recipe_id, RecipeMirrorModel.extras))
        found = []
        for recipe_id, extras in rows.all():
            variations = (extras or {}).get("variation_author_avatars") or {}
            avatars = {(extras or {}).get("author_avatar"), *variations.values()}
            if wanted in {str(a).lower() for a in avatars if a}:
                found.append(recipe_id)
        return found

    async def for_recipes(self, recipe_ids: list[int]) -> dict[int, RecipeMirror]:
        if not recipe_ids:
            return {}
        rows = await self._db.scalars(
            select(RecipeMirrorModel).where(
                RecipeMirrorModel.recipe_id.in_(sorted(set(recipe_ids)))
            )
        )
        return {r.recipe_id: _mirror(r) for r in rows.all()}

    async def save(self, mirror: RecipeMirror) -> RecipeMirror:
        row = await self._db.get(RecipeMirrorModel, mirror.recipe_id)
        if row is None:
            row = RecipeMirrorModel(recipe_id=mirror.recipe_id)
            self._db.add(row)
        row.peer_id = mirror.peer_id
        row.origin_public_id = mirror.origin_public_id
        row.etag = mirror.etag
        row.source_revision = mirror.source_revision
        row.source_author_name = mirror.source_author_name
        row.document = mirror.document
        row.files = dict(mirror.files)
        row.extras = mirror.extras
        row.accepted_at = mirror.accepted_at
        row.updated_at = mirror.updated_at
        await self._db.flush()
        return _mirror(row)

    # ── Waiting recipes ──────────────────────────────────────────────

    async def incoming(self, public_id: str) -> IncomingRecipe | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(IncomingRecipeModel).where(IncomingRecipeModel.public_id == uid)
        )
        return _incoming(row) if row is not None else None

    async def incoming_by_origin(
        self, peer_id: int, origin_public_id: UUID
    ) -> IncomingRecipe | None:
        row = await self._db.scalar(
            select(IncomingRecipeModel).where(
                IncomingRecipeModel.peer_id == peer_id,
                IncomingRecipeModel.origin_public_id == origin_public_id,
            )
        )
        return _incoming(row) if row is not None else None

    async def incoming_list(
        self, status: IncomingStatus | None = None, peer_id: int | None = None
    ) -> list[IncomingRecipe]:
        stmt = select(IncomingRecipeModel)
        if status is not None:
            stmt = stmt.where(IncomingRecipeModel.status == status.value)
        if peer_id is not None:
            stmt = stmt.where(IncomingRecipeModel.peer_id == peer_id)
        rows = await self._db.scalars(
            stmt.order_by(IncomingRecipeModel.received_at, IncomingRecipeModel.id)
        )
        return [_incoming(r) for r in rows.all()]

    async def save_incoming(self, item: IncomingRecipe) -> IncomingRecipe:
        row = await self._db.get(IncomingRecipeModel, item.id) if item.id else None
        if row is None:
            row = IncomingRecipeModel(public_id=item.public_id)
            self._db.add(row)
        row.peer_id = item.peer_id
        row.origin_public_id = item.origin_public_id
        row.status = item.status.value
        row.kind = item.kind.value
        row.title = item.title[:255]
        row.author_name = item.author_name[:255] if item.author_name else None
        row.etag = item.etag
        row.payload = item.payload
        row.received_at = item.received_at
        row.decided_at = item.decided_at
        await self._db.flush()
        return _incoming(row)

    async def delete_incoming(self, item_id: int) -> None:
        await self._db.execute(delete(IncomingRecipeModel).where(IncomingRecipeModel.id == item_id))
        await self._db.flush()

    # ── Catalogue mappings ───────────────────────────────────────────

    async def mappings(self, peer_id: int) -> list[CatalogueMapping]:
        rows = await self._db.scalars(
            select(PeerCatalogueMappingModel)
            .where(PeerCatalogueMappingModel.peer_id == peer_id)
            .order_by(PeerCatalogueMappingModel.kind, PeerCatalogueMappingModel.remote_name)
        )
        return [_mapping(r) for r in rows.all()]

    async def mapping(
        self, peer_id: int, kind: MappingKind, remote_id: str
    ) -> CatalogueMapping | None:
        row = await self._db.get(PeerCatalogueMappingModel, (peer_id, kind.value, remote_id))
        return _mapping(row) if row is not None else None

    async def save_mapping(self, mapping: CatalogueMapping) -> None:
        row = await self._db.get(
            PeerCatalogueMappingModel, (mapping.peer_id, mapping.kind.value, mapping.remote_id)
        )
        if row is None:
            row = PeerCatalogueMappingModel(
                peer_id=mapping.peer_id,
                kind=mapping.kind.value,
                remote_public_id=mapping.remote_id,
            )
            self._db.add(row)
        row.action = mapping.action.value if mapping.action is not None else None
        for kind, column in _LOCAL.items():
            setattr(
                row,
                column,
                mapping.local_id
                if kind is mapping.kind and mapping.action is MappingAction.MAP
                else None,
            )
        row.created_here = mapping.created_here
        row.matched_by = mapping.matched_by
        row.remote_name = mapping.remote_name[:255]
        row.remote_data = mapping.remote_data
        row.updated = mapping.updated
        await self._db.flush()

    async def repoint_mappings(self, kind: MappingKind, from_id: int, to_id: int) -> None:
        column = getattr(PeerCatalogueMappingModel, _LOCAL[kind])
        await self._db.execute(
            update(PeerCatalogueMappingModel)
            .where(PeerCatalogueMappingModel.kind == kind.value, column == from_id)
            .values({_LOCAL[kind]: to_id})
        )
        await self._db.flush()

    # ── Dismissed suggestions ────────────────────────────────────────

    async def dismissals(self, peer_id: int) -> list[SuggestionDismissal]:
        rows = await self._db.scalars(
            select(PeerSuggestionDismissalModel).where(
                PeerSuggestionDismissalModel.peer_id == peer_id
            )
        )
        return [
            SuggestionDismissal(
                peer_id=r.peer_id,
                kind=MappingKind(r.kind),
                remote_id=r.remote_public_id,
                field=r.field,
                value_hash=r.value_hash,
                dismissed_at=r.dismissed_at,
            )
            for r in rows.all()
        ]

    async def save_dismissal(self, dismissal: SuggestionDismissal) -> None:
        key = (dismissal.peer_id, dismissal.kind.value, dismissal.remote_id, dismissal.field)
        row = await self._db.get(PeerSuggestionDismissalModel, key)
        if row is None:
            row = PeerSuggestionDismissalModel(
                peer_id=dismissal.peer_id,
                kind=dismissal.kind.value,
                remote_public_id=dismissal.remote_id,
                field=dismissal.field,
            )
            self._db.add(row)
        row.value_hash = dismissal.value_hash
        row.dismissed_at = dismissal.dismissed_at
        await self._db.flush()

    async def purge_peer(self, peer_id: int) -> None:
        await self._db.execute(
            delete(PeerSuggestionDismissalModel).where(
                PeerSuggestionDismissalModel.peer_id == peer_id
            )
        )
        await self._db.execute(
            delete(IncomingRecipeModel).where(IncomingRecipeModel.peer_id == peer_id)
        )
        await self._db.execute(
            delete(PeerCatalogueMappingModel).where(PeerCatalogueMappingModel.peer_id == peer_id)
        )
        await self._db.flush()
