"""The nightly sweep of uploads that nothing refers to."""

from datetime import timedelta
from io import BytesIO
from typing import Any
from uuid import UUID

import httpx
from PIL import Image
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update

from src.bootstrap.nightly_jobs import run_nightly_once
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.persistence.models.stored_file_models import (
    StoredFileContentModel,
)
from src.platform.adapters.outbound.persistence.models.stored_file_models import StoredFileModel
from src.platform.adapters.outbound.persistence.models.user_models import UserModel
from src.platform.adapters.outbound.persistence.repositories.stored_file_repository import (
    SqlAlchemyStoredFileRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.application.use_cases.files.sweep_unused_files import UNUSED_FILE_GRACE
from src.platform.application.use_cases.files.sweep_unused_files import SweepResult
from src.platform.application.use_cases.files.sweep_unused_files import SweepUnusedFiles
from src.platform.domain.entities.stored_file import StoredFile
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (64, 64), (200, 120, 40)).save(out, format="PNG")
    return out.getvalue()


async def _upload(client: httpx.AsyncClient) -> str:
    uploaded = await client.post(
        f"{WEB}/files", headers=CSRF, files={"file": ("photo.png", _png(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    return str(uploaded.json()["id"])


async def _age(*public_ids: str, older_than: timedelta = UNUSED_FILE_GRACE) -> None:
    async with SessionLocal() as db:
        await db.execute(
            update(StoredFileModel)
            .where(StoredFileModel.public_id.in_([UUID(p) for p in public_ids]))
            .values(created=now_utc() - older_than - timedelta(hours=1))
        )
        await db.commit()


async def _exists(public_id: str) -> bool:
    async with SessionLocal() as db:
        file_id = await db.scalar(
            select(StoredFileModel.id).where(StoredFileModel.public_id == UUID(public_id))
        )
        return file_id is not None


async def _sweep() -> SweepResult:
    async with SessionLocal() as db:
        return await deps.sweep_unused_files(Platform(db)).run()


async def _steps(cook: httpx.AsyncClient, name: str) -> list[tuple[str, list[dict[str, Any]]]]:
    salt = await make_ingredient(cook, f"Salz {name}", english=f"Salt {name}")
    return [("Würzen", [{"ingredient_id": salt["id"]}])]


async def test_the_nightly_job_deletes_an_old_unused_upload_and_keeps_a_fresh_one(
    cook: httpx.AsyncClient,
) -> None:
    old = await _upload(cook)
    fresh = await _upload(cook)
    await _age(old)
    async with SessionLocal() as db:
        old_id = await db.scalar(
            select(StoredFileModel.id).where(StoredFileModel.public_id == UUID(old))
        )

    await run_nightly_once(force=True)

    assert not await _exists(old)
    assert await _exists(fresh)
    assert (await cook.get(f"{WEB}/files/{old}/content")).status_code == 404
    assert (await cook.get(f"{WEB}/files/{fresh}/content")).status_code == 200
    async with SessionLocal() as db:
        left = await db.scalar(
            select(func.count())
            .select_from(StoredFileContentModel)
            .where(StoredFileContentModel.file_id == old_id)
        )
    assert left == 0


async def test_the_sweep_reports_count_and_bytes(cook: httpx.AsyncClient) -> None:
    first, second = await _upload(cook), await _upload(cook)
    await _age(first, second)
    async with SessionLocal() as db:
        rows = (
            await db.scalars(
                select(StoredFileModel).where(
                    StoredFileModel.public_id.in_([UUID(first), UUID(second)])
                )
            )
        ).all()
        expected = sum(r.size + (r.thumbnail_size or 0) for r in rows)

    result = await _sweep()

    assert result == SweepResult(removed=2, removed_bytes=expected, content_failures=0)
    assert await _sweep() == SweepResult(removed=0, removed_bytes=0, content_failures=0)


async def test_files_a_recipe_step_avatar_or_branding_uses_stay(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    cover, step_image, background = await _upload(cook), await _upload(cook), await _upload(admin)
    body = recipe_payload("Bebildert", await _steps(cook, "Bild"), cover_image_id=cover)
    body["steps"][0]["image_id"] = step_image
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert created.status_code == 201, created.text

    avatar = await cook.put(
        f"{WEB}/users/me/avatar", headers=CSRF, files={"file": ("me.png", _png(), "image/png")}
    )
    assert avatar.status_code == 200, avatar.text
    avatar_id = str(avatar.json()["avatar_id"])

    general = (await admin.get(f"{WEB}/settings/general")).json()
    saved = await admin.put(
        f"{WEB}/settings/general",
        headers=CSRF,
        json=general | {"login_background_file_id": background},
    )
    assert saved.status_code == 200, saved.text

    kept = (cover, step_image, avatar_id, background)
    await _age(*kept)
    assert (await _sweep()).removed == 0
    for public_id in kept:
        assert await _exists(public_id), public_id


async def test_an_image_only_a_revision_names_stays_until_the_revision_goes(
    cook: httpx.AsyncClient,
) -> None:
    first, second = await _upload(cook), await _upload(cook)
    steps = await _steps(cook, "Revision")
    recipe = await make_recipe(cook, "Umgestellt", steps, cover_image_id=first)
    saved = await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json=recipe_payload("Umgestellt", steps, cover_image_id=second),
    )
    assert saved.status_code == 200, saved.text
    await _age(first, second)

    assert (await _sweep()).removed == 0
    assert await _exists(first)

    # Once no revision names it, the old cover is unused.
    async with SessionLocal() as db:
        revisions = (await db.scalars(select(RecipeRevisionModel))).all()
        stale = [r.id for r in revisions if r.snapshot.get("cover_image_id") == first]
        assert stale
        await db.execute(delete(RecipeRevisionModel).where(RecipeRevisionModel.id.in_(stale)))
        await db.commit()
    assert (await _sweep()).removed == 1
    assert not await _exists(first)
    assert await _exists(second)


class _AttachingFiles(SqlAlchemyStoredFileRepository):
    """Makes the file an avatar from another session, as a request that
    commits between the sweep's first check and its lock would."""

    async def lock(self, file_id: int) -> StoredFile | None:
        async with SessionLocal() as other:
            await other.execute(
                update(UserModel)
                .where(UserModel.email == "cook@example.com")
                .values(avatar_file_id=file_id)
            )
            await other.commit()
        return await super().lock(file_id)


async def test_a_file_attached_after_the_first_check_stays(cook: httpx.AsyncClient) -> None:
    upload = await _upload(cook)
    await _age(upload)

    async with SessionLocal() as db:
        p = Platform(db)
        sweep = SweepUnusedFiles(
            file_repo=_AttachingFiles(db), access=deps.file_access(p), uow=p.uow
        )
        result = await sweep.run()

    assert result.removed == 0
    assert await _exists(upload)
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["avatar_id"] == upload
