"""The file content store contract, run against the postgres and local
providers, the upload path through the local provider, and moving files
between providers with the storage CLI's use case."""

from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from PIL import Image

from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.persistence.models.stored_file_models import StoredFileModel
from src.platform.adapters.outbound.persistence.repositories.stored_file_repository import (
    SqlAlchemyStoredFileRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.adapters.outbound.storage.local_store import LocalContentStore
from src.platform.adapters.outbound.storage.postgres_store import PostgresContentStore
from src.platform.application.use_cases.files.move_storage import MoveStorage
from src.platform.ports.outbound.file_content_store import THUMBNAIL
from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import IFileContentStore
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF


async def _file_row(db: object) -> ContentRef:
    """A stored_files row, since the database provider keys content by it."""
    row = StoredFileModel(
        public_id=uuid4(),
        file_name="a.pdf",
        content_type="application/pdf",
        size=3,
        content_hash="x",
        created=now_utc(),
    )
    db.add(row)  # type: ignore[attr-defined]
    await db.flush()  # type: ignore[attr-defined]
    return ContentRef(file_id=row.id, public_id=row.public_id)


@pytest.fixture(params=["postgres", "local"])
async def store_and_ref(
    request: pytest.FixtureRequest, tmp_path: Path
) -> AsyncIterator[tuple[IFileContentStore, ContentRef]]:
    async with SessionLocal() as db:
        ref = await _file_row(db)
        store: IFileContentStore = (
            PostgresContentStore(db)
            if request.param == "postgres"
            else LocalContentStore(str(tmp_path))
        )
        yield store, ref


async def test_content_store_contract(store_and_ref: tuple[IFileContentStore, ContentRef]) -> None:
    store, ref = store_and_ref
    await store.check()
    assert await store.get(ref) is None
    assert not await store.exists(ref)
    await store.put(ref, b"one", "application/pdf")
    await store.put(ref, b"two", "application/pdf")
    assert await store.get(ref) == b"two"
    assert await store.exists(ref)
    thumb = ContentRef(ref.file_id, ref.public_id, THUMBNAIL)
    assert await store.get(thumb) is None
    await store.delete(ref)
    await store.delete(ref)
    assert await store.get(ref) is None
    # Both stream through the backend.
    assert (
        store.url_for(ref, file_name="a.pdf", content_type="application/pdf", inline=True) is None
    )


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (40, 30), (10, 120, 200)).save(out, format="PNG")
    return out.getvalue()


async def test_uploads_and_reads_through_the_local_provider(
    admin: httpx.AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = LocalContentStore(str(tmp_path))
    monkeypatch.setattr(deps, "active_content_store", lambda _db: local)
    uploaded = await admin.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("p.png", _png(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]
    assert (tmp_path / "files" / file_id / "original").is_file()
    assert (tmp_path / "files" / file_id / "thumbnail").is_file()
    content = await admin.get(f"/api/v1/web/files/{file_id}/content")
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/webp"
    # Re-encoding and the ETag apply to every provider.
    again = await admin.get(
        f"/api/v1/web/files/{file_id}/content", headers={"If-None-Match": content.headers["etag"]}
    )
    assert again.status_code == 304
    assert (await admin.delete(f"/api/v1/web/files/{file_id}", headers=CSRF)).status_code == 204
    assert not (tmp_path / "files" / file_id / "original").exists()


async def test_moving_files_copies_verifies_and_removes_the_source(
    admin: httpx.AsyncClient, tmp_path: Path
) -> None:
    for name in ("a.png", "b.png"):
        response = await admin.post(
            "/api/v1/web/files", headers=CSRF, files={"file": (name, _png(), "image/png")}
        )
        assert response.status_code == 201
    async with SessionLocal() as db:
        move = MoveStorage(files=SqlAlchemyStoredFileRepository(db), uow=SqlAlchemyUnitOfWork(db))
        postgres, local = PostgresContentStore(db), LocalContentStore(str(tmp_path))

        copied = await move.copy(postgres, local)
        assert copied.ok and copied.files == 2 and copied.copied == 4
        again = await move.copy(postgres, local)
        assert again.skipped == 4 and again.copied == 0
        assert (await move.verify(local)).ok

        with pytest.raises(ValueError):
            await move.remove_source(local, local)
        removed = await move.remove_source(postgres, local)
        assert removed.ok and removed.removed == 4
        assert not (await move.verify(postgres)).ok


async def test_a_corrupted_copy_is_reported_and_blocks_removal(
    admin: httpx.AsyncClient, tmp_path: Path
) -> None:
    await admin.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("a.png", _png(), "image/png")}
    )
    async with SessionLocal() as db:
        files = SqlAlchemyStoredFileRepository(db)
        move = MoveStorage(files=files, uow=SqlAlchemyUnitOfWork(db))
        postgres, local = PostgresContentStore(db), LocalContentStore(str(tmp_path))
        await move.copy(postgres, local)
        stored = (await files.list_all())[0]
        await local.put(ContentRef(stored.id, stored.public_id), b"broken", stored.content_type)
        report = await move.verify(local)
        assert not report.ok and "hash mismatch" in report.problems[0]
        blocked = await move.remove_source(postgres, local)
        assert not blocked.ok and blocked.removed == 0
        assert (await move.verify(postgres)).ok
