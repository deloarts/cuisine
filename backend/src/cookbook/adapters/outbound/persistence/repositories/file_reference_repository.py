"""
Which stored files the cookbook's records refer to. Covers and step images
are foreign keys and are matched in SQL. Revision snapshots and mirrors name
their files by public id inside JSON, whose shape differs between SQLite
and Postgres, so they are read and matched here, and only for the files the
foreign keys left over.
"""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.mirror_models import RecipeMirrorModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.cookbook.domain.services.revisions import snapshot_image_ids

# Large enough for few queries, small enough for every database's limit on
# bound parameters.
_CHUNK = 500


class SqlAlchemyFileReferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def referenced(self, files: Mapping[int, str], *, history: bool) -> set[int]:
        found: set[int] = set()
        ids = sorted(files)
        for start in range(0, len(ids), _CHUNK):
            chunk = ids[start : start + _CHUNK]
            covers = select(RecipeModel.cover_file_id).where(RecipeModel.cover_file_id.in_(chunk))
            steps = select(RecipeStepModel.image_file_id).where(
                RecipeStepModel.image_file_id.in_(chunk)
            )
            found |= {f for f in (await self._db.scalars(covers)).all() if f is not None}
            found |= {f for f in (await self._db.scalars(steps)).all() if f is not None}
        left = {public_id.lower(): file_id for file_id, public_id in files.items()}
        left = {p: f for p, f in left.items() if f not in found}
        if left:
            found |= {left[p] for p in await self._json_references(history=history) if p in left}
        return found

    async def _json_references(self, *, history: bool) -> set[str]:
        names: set[str] = set()
        if history:
            snapshots = await self._db.stream_scalars(select(RecipeRevisionModel.snapshot))
            async for snapshot in snapshots:
                names |= snapshot_image_ids(snapshot or {})
        mirrors = await self._db.execute(select(RecipeMirrorModel.files, RecipeMirrorModel.extras))
        for files, extras in mirrors.all():
            names |= {str(v).lower() for v in (files or {}).values() if v}
            variations = (extras or {}).get("variation_author_avatars") or {}
            avatars = {(extras or {}).get("author_avatar"), *variations.values()}
            names |= {str(a).lower() for a in avatars if a}
        return names
