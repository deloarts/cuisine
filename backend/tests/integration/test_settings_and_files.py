"""The admin settings and the database-backed file storage."""

from io import BytesIO

import httpx
import pytest
from PIL import Image

from src.platform.adapters.inbound.api.v1 import files_router
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login


def _jpeg_with_exif() -> bytes:
    image = Image.new("RGB", (64, 48), (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"  # Make
    out = BytesIO()
    image.save(out, format="JPEG", exif=exif.tobytes())
    return out.getvalue()


async def test_public_info_needs_no_session(client: httpx.AsyncClient) -> None:
    info = (await client.get("/api/v1/public/info")).json()
    assert info["instance_name"] == "Cuisine"
    assert info["default_language"] == "enGB"


async def test_settings_need_read_settings(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (await other_client.get("/api/v1/web/settings/general")).status_code == 403


async def test_general_settings_round_trip(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    saved = await admin.put(
        "/api/v1/web/settings/general",
        headers=CSRF,
        json={"instance_name": "Omas Küche", "default_language": "enGB"},
    )
    assert saved.status_code == 200
    assert (await client.get("/api/v1/public/info")).json()["instance_name"] == "Omas Küche"


async def test_login_steam_is_on_by_default_and_can_be_turned_off(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    assert (await client.get("/api/v1/public/info")).json()["login_steam"] is True

    saved = await admin.put(
        "/api/v1/web/settings/general",
        headers=CSRF,
        json={"instance_name": "Cuisine", "default_language": "enGB", "login_steam": False},
    )
    assert saved.json()["login_steam"] is False
    assert (await client.get("/api/v1/public/info")).json()["login_steam"] is False


async def test_out_of_range_security_setting_is_refused(admin: httpx.AsyncClient) -> None:
    security = (await admin.get("/api/v1/web/settings/security")).json()
    refused = await admin.put(
        "/api/v1/web/settings/security", headers=CSRF, json={**security, "min_password_length": 3}
    )
    assert refused.status_code == 422


async def test_mail_password_is_never_returned_and_kept_when_omitted(
    admin: httpx.AsyncClient,
) -> None:
    body = {
        "enabled": True,
        "host": "smtp.example.com",
        "port": 587,
        "security": "starttls",
        "username": "cuisine",
        "password": "smtp-secret",
        "sender": "cuisine@example.com",
    }
    saved = await admin.put("/api/v1/web/settings/mail", headers=CSRF, json=body)
    assert saved.status_code == 200
    assert "password" not in saved.json()
    assert saved.json()["password_set"] is True

    body.pop("password")
    again = await admin.put(
        "/api/v1/web/settings/mail", headers=CSRF, json={**body, "host": "mail.example.com"}
    )
    assert again.json()["password_set"] is True
    assert again.json()["host"] == "mail.example.com"


async def test_image_upload_is_reencoded_without_metadata(admin: httpx.AsyncClient) -> None:
    uploaded = await admin.post(
        "/api/v1/web/files",
        headers=CSRF,
        files={"file": ("photo.jpg", _jpeg_with_exif(), "image/jpeg")},
    )
    assert uploaded.status_code == 201, uploaded.text
    meta = uploaded.json()
    assert meta["content_type"] == "image/webp"
    assert meta["file_name"] == "photo.webp"
    assert (meta["width"], meta["height"]) == (64, 48)
    assert meta["has_thumbnail"] is True

    content = await admin.get(f"/api/v1/web/files/{meta['id']}/content")
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/webp"
    assert content.headers["content-disposition"].startswith("inline")
    assert content.headers["x-content-type-options"] == "nosniff"
    assert b"SecretCam" not in content.content
    with Image.open(BytesIO(content.content)) as stored:
        assert not stored.getexif()

    etag = content.headers["etag"]
    cached = await admin.get(
        f"/api/v1/web/files/{meta['id']}/content", headers={"If-None-Match": etag}
    )
    assert cached.status_code == 304

    thumb = await admin.get(f"/api/v1/web/files/{meta['id']}/content?variant=thumbnail")
    assert thumb.status_code == 200
    assert thumb.headers["etag"] != etag


async def test_pdf_upload_is_kept_as_is(admin: httpx.AsyncClient) -> None:
    pdf = b"%PDF-1.4\n%fake but signed\n"
    uploaded = await admin.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("menu.pdf", pdf, "application/pdf")}
    )
    assert uploaded.status_code == 201
    content = await admin.get(f"/api/v1/web/files/{uploaded.json()['id']}/content")
    assert content.content == pdf


async def test_html_and_svg_uploads_are_refused(admin: httpx.AsyncClient) -> None:
    for name, kind in (("x.html", "text/html"), ("x.svg", "image/svg+xml")):
        refused = await admin.post(
            "/api/v1/web/files", headers=CSRF, files={"file": (name, b"<script>", kind)}
        )
        assert refused.status_code == 415


async def test_fake_image_and_fake_pdf_are_refused(admin: httpx.AsyncClient) -> None:
    image = await admin.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("a.png", b"not a png", "image/png")}
    )
    pdf = await admin.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("a.pdf", b"<html>", "application/pdf")}
    )
    assert image.status_code == pdf.status_code == 415


async def test_any_signed_in_user_uploads_and_reads_only_their_own(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    """An upload nothing uses yet is private to its uploader."""
    pdf = b"%PDF-1.4\n"
    uploaded = (
        await admin.post(
            "/api/v1/web/files", headers=CSRF, files={"file": ("a.pdf", pdf, "application/pdf")}
        )
    ).json()
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")

    own = await other_client.post(
        "/api/v1/web/files", headers=CSRF, files={"file": ("b.pdf", pdf, "application/pdf")}
    )
    assert own.status_code == 201
    mine = await other_client.get(f"/api/v1/web/files/{own.json()['id']}/content")
    assert mine.status_code == 200
    foreign = await other_client.get(f"/api/v1/web/files/{uploaded['id']}/content")
    assert foreign.status_code == 404


async def test_unknown_or_malformed_file_id_is_404(admin: httpx.AsyncClient) -> None:
    assert (await admin.get("/api/v1/web/files/not-a-uuid")).status_code == 404
    assert (
        await admin.get("/api/v1/web/files/00000000-0000-0000-0000-000000000000")
    ).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/web/files"),
        ("GET", "/api/v1/web/files/00000000-0000-0000-0000-000000000000"),
        ("GET", "/api/v1/web/files/00000000-0000-0000-0000-000000000000/content"),
        ("DELETE", "/api/v1/web/files/00000000-0000-0000-0000-000000000000"),
    ],
)
async def test_file_routes_need_a_session(
    visitor: httpx.AsyncClient, method: str, path: str
) -> None:
    files = {"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")} if method == "POST" else None
    response = await visitor.request(method, path, headers=CSRF, files=files)
    assert response.status_code == 401


async def test_file_metadata_is_read_by_its_uploader(admin: httpx.AsyncClient) -> None:
    uploaded = await admin.post(
        "/api/v1/web/files",
        headers=CSRF,
        files={"file": ("menu.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    meta = (await admin.get(f"/api/v1/web/files/{uploaded.json()['id']}")).json()
    assert (meta["file_name"], meta["size"], meta["has_thumbnail"]) == ("menu.pdf", 9, False)


async def test_pdf_is_stored_with_the_server_side_content_type(admin: httpx.AsyncClient) -> None:
    uploaded = await admin.post(
        "/api/v1/web/files",
        headers=CSRF,
        files={"file": ("menu.pdf", b"%PDF-1.4\n", "Application/PDF; name=evil")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["content_type"] == "application/pdf"
    content = await admin.get(f"/api/v1/web/files/{uploaded.json()['id']}/content")
    assert content.headers["content-type"] == "application/pdf"


async def test_oversized_upload_is_refused_before_it_is_read_whole(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(files_router, "MAX_UPLOAD_BYTES", 16)
    refused = await admin.post(
        "/api/v1/web/files",
        headers=CSRF,
        files={"file": ("big.pdf", b"%PDF-1.4\n" + b"x" * 64, "application/pdf")},
    )
    assert refused.status_code == 413


async def test_uploader_deletes_an_unused_file_and_others_cannot(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    uploaded = await admin.post(
        "/api/v1/web/files",
        headers=CSRF,
        files={"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    file_id = uploaded.json()["id"]
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    foreign = await other_client.delete(f"/api/v1/web/files/{file_id}", headers=CSRF)
    assert foreign.status_code == 404

    assert (await admin.delete(f"/api/v1/web/files/{file_id}", headers=CSRF)).status_code == 204
    assert (await admin.get(f"/api/v1/web/files/{file_id}")).status_code == 404
