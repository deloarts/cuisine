from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.legal_models import LegalVersionModel
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.legal import LegalVersion
from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.legal import PrivacyModeSnapshot


def _version(row: LegalVersionModel) -> LegalVersion:
    snapshot = None
    if row.privacy_mode:
        try:
            snapshot = PrivacyModeSnapshot(
                mode=PrivacyMode(row.privacy_mode.get("mode")),
                default_visibility=str(row.privacy_mode.get("default_visibility", "instance")),
                allow_public_recipes=bool(row.privacy_mode.get("allow_public_recipes", False)),
                peering_enabled=bool(row.privacy_mode.get("peering_enabled", False)),
            )
        except ValueError:
            snapshot = None
    return LegalVersion(
        id=row.id,
        public_id=row.public_id,
        kind=LegalKind(row.kind),
        version=row.version,
        texts={str(k): str(v) for k, v in dict(row.texts or {}).items()},
        published_at=row.published_at,
        published_by_id=row.published_by_id,
        privacy_mode=snapshot,
    )


class SqlAlchemyLegalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def current(self, kind: LegalKind) -> LegalVersion | None:
        row = await self._db.scalar(
            select(LegalVersionModel)
            .where(LegalVersionModel.kind == kind.value)
            .order_by(LegalVersionModel.version.desc())
            .limit(1)
        )
        return _version(row) if row is not None else None

    async def history(self, kind: LegalKind) -> list[LegalVersion]:
        rows = await self._db.scalars(
            select(LegalVersionModel)
            .where(LegalVersionModel.kind == kind.value)
            .order_by(LegalVersionModel.version.desc())
        )
        return [_version(r) for r in rows.all()]

    async def add(self, version: LegalVersion) -> LegalVersion:
        snapshot = version.privacy_mode
        row = LegalVersionModel(
            public_id=version.public_id,
            kind=version.kind.value,
            version=version.version,
            texts=dict(version.texts),
            privacy_mode=(
                {
                    "mode": snapshot.mode.value,
                    "default_visibility": snapshot.default_visibility,
                    "allow_public_recipes": snapshot.allow_public_recipes,
                    "peering_enabled": snapshot.peering_enabled,
                }
                if snapshot
                else None
            ),
            published_at=version.published_at,
            published_by_id=version.published_by_id,
        )
        self._db.add(row)
        await self._db.flush()
        return _version(row)
