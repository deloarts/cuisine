"""The admin area's Host, Storage and backup, General (branding and display
defaults) and Notifications tabs: webhooks, the banner and in-app notices."""

from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image

from src.bootstrap.webhook_worker import deliver_once
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.infrastructure.config.settings import cfg
from src.platform.ports.outbound.webhook_sender import WebhookSendResult
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login

WEB = "/api/v1/web"


class FakeRedis:
    async def ping(self) -> bool:
        return True

    async def info(self, _section: str) -> dict[str, str]:
        return {"redis_version": "7.4.0"}


class FakeSender:
    """Records every request instead of sending it; answers `status`."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.status: int | None = 204

    async def post(self, **kwargs: Any) -> WebhookSendResult:
        self.sent.append(kwargs)
        error = None if self.status else "Connection failed."
        return WebhookSendResult(http_status=self.status, duration_ms=3, error=error)


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> FakeSender:
    fake = FakeSender()

    async def resolve(_host: str, _port: int) -> Sequence[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(deps, "_webhook_sender", lambda: fake)
    monkeypatch.setattr(deps, "webhook_guard", lambda: WebhookTargetGuard(resolver=resolve))
    return fake


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (32, 32), (0, 0, 0)).save(out, format="PNG")
    return out.getvalue()


# ── Host and storage ──────────────────────────────────────────────────


async def test_host_readings(admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_redis", lambda: FakeRedis())
    host = (await admin.get(f"{WEB}/admin/host")).json()
    assert host["cpu_count"] >= 1
    assert host["memory_total_bytes"] > 0
    services = {s["name"]: s for s in host["services"]}
    assert services["database"]["status"] == "ok"
    assert services["database"]["version"].startswith("sqlite")
    assert services["redis"]["version"] == "7.4.0"


async def test_admin_readings_need_read_settings(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    for path in ("/admin/host", "/admin/storage", "/admin/webhooks", "/admin/notices"):
        assert (await other_client.get(f"{WEB}{path}")).status_code == 403


async def test_storage_readings_and_backups(
    admin: httpx.AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await admin.post(f"{WEB}/files", headers=CSRF, files={"file": ("a.png", _png(), "image/png")})
    unseen = (await admin.get(f"{WEB}/admin/storage")).json()
    assert unseen["provider"] == "postgres"
    assert unseen["provider_reachable"] is True
    assert unseen["database"]["dialect"] == "sqlite"
    assert unseen["files"]["count"] == 1
    assert unseen["files"]["by_kind"][0]["kind"] == "image"
    assert unseen["warnings"] == ["backups_not_visible"]

    (tmp_path / "cuisine-20261121-030000.dump").write_bytes(b"dump")
    monkeypatch.setattr(cfg.backup, "dir", str(tmp_path))
    seen = (await admin.get(f"{WEB}/admin/storage")).json()
    assert seen["backups"]["visible"] is True
    assert seen["backups"]["files"][0]["name"] == "cuisine-20261121-030000.dump"
    assert "backups_not_visible" not in seen["warnings"]
    assert "backups_on_database_host" in seen["warnings"]


# ── General settings and branding ─────────────────────────────────────


async def test_branding_and_display_defaults_reach_the_login_page(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    general = (await admin.get(f"{WEB}/settings/general")).json()
    general.update(
        accent_color="#112233",
        date_format="yyyy-mm-dd",
        time_format="12h",
        first_day_of_week="sunday",
    )
    saved = await admin.put(f"{WEB}/settings/general", headers=CSRF, json=general)
    assert saved.status_code == 200, saved.text
    await admin.post("/api/v1/auth/logout", headers=CSRF)

    info = (await client.get("/api/v1/public/info")).json()
    assert info["accent_color"] == "#112233"
    assert "has_logo" not in info
    assert info["date_format"] == "yyyy-mm-dd"
    assert info["first_day_of_week"] == "sunday"


async def test_manifest_follows_the_general_settings(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    default = await client.get("/api/v1/public/manifest.webmanifest")
    assert default.status_code == 200
    assert default.headers["content-type"].startswith("application/manifest+json")
    body = default.json()
    assert body["name"] == "Cuisine"
    assert body["theme_color"] == "#c2410c"
    assert body["start_url"] == "/" and body["display"] == "standalone"
    assert {i["purpose"] for i in body["icons"]} == {"any", "maskable"}
    assert all(i["src"].startswith("/icons/") for i in body["icons"])

    general = (await admin.get(f"{WEB}/settings/general")).json()
    general.update(instance_name="Family Kitchen", default_language="deAT", accent_color="#112233")
    saved = await admin.put(f"{WEB}/settings/general", headers=CSRF, json=general)
    assert saved.status_code == 200, saved.text

    body = (await client.get("/api/v1/public/manifest.webmanifest")).json()
    assert body["name"] == body["short_name"] == "Family Kitchen"
    assert body["lang"] == "de-AT"
    assert body["theme_color"] == "#112233"


async def test_accent_color_must_be_hex(admin: httpx.AsyncClient) -> None:
    general = (await admin.get(f"{WEB}/settings/general")).json()
    general.update(accent_color="red")
    assert (
        await admin.put(f"{WEB}/settings/general", headers=CSRF, json=general)
    ).status_code == 422


async def test_the_logo_is_gone(admin: httpx.AsyncClient, client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/public/branding/logo")).status_code == 404
    general = (await admin.get(f"{WEB}/settings/general")).json()
    assert "logo_file_id" not in general
    refused = await admin.put(
        f"{WEB}/settings/general", headers=CSRF, json=general | {"logo_file_id": None}
    )
    assert refused.status_code == 422


async def test_login_background_is_served_without_a_session(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    general = (await admin.get(f"{WEB}/settings/general")).json()
    keys = []
    for name in ("a.png", "b.png"):
        photo = (
            await admin.post(
                f"{WEB}/files", headers=CSRF, files={"file": (name, _png(), "image/png")}
            )
        ).json()
        general["login_background_file_id"] = photo["id"]
        saved = await admin.put(f"{WEB}/settings/general", headers=CSRF, json=general)
        assert saved.status_code == 200, saved.text
        keys.append((await client.get("/api/v1/public/info")).json()["login_background_key"])
    await admin.post("/api/v1/auth/logout", headers=CSRF)

    assert all(keys) and keys[0] != keys[1]
    served = await client.get("/api/v1/public/branding/login-background")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"
    again = await client.get(
        "/api/v1/public/branding/login-background",
        headers={"If-None-Match": served.headers["ETag"]},
    )
    assert again.status_code == 304


async def test_login_background_must_be_a_stored_image(admin: httpx.AsyncClient) -> None:
    pdf = (
        await admin.post(
            f"{WEB}/files",
            headers=CSRF,
            files={"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")},
        )
    ).json()
    general = (await admin.get(f"{WEB}/settings/general")).json()
    for bad in (pdf["id"], "00000000-0000-0000-0000-000000000000"):
        general["login_background_file_id"] = bad
        refused = await admin.put(f"{WEB}/settings/general", headers=CSRF, json=general)
        assert refused.status_code == 422


async def test_no_login_background_answers_404(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/public/info")).json()["login_background_key"] is None
    served = await client.get("/api/v1/public/branding/login-background")
    assert served.status_code == 404


# ── Banner ────────────────────────────────────────────────────────────


async def test_banner_shows_on_the_public_surface_in_the_readers_language(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    assert (await client.get("/api/v1/public/banner")).json() is None
    saved = await admin.put(
        f"{WEB}/settings/banner",
        headers=CSRF,
        json={
            "enabled": True,
            "severity": "warning",
            "messages": {"en-GB": "Maintenance tonight", "de-AT": "Heute Abend Wartung"},
            "dismissible": False,
        },
    )
    assert saved.status_code == 200, saved.text
    banner = (await client.get("/api/v1/public/banner", params={"locale": "de-AT"})).json()
    assert banner["message"] == "Heute Abend Wartung"
    assert banner["severity"] == "warning"
    assert banner["dismissible"] is False
    first_key = banner["key"]

    changed = saved.json() | {"messages": {"en-GB": "Back at 9"}, "dismissible": True}
    await admin.put(f"{WEB}/settings/banner", headers=CSRF, json=changed)
    english = (await client.get("/api/v1/public/banner", params={"locale": "de-AT"})).json()
    assert english["message"] == "Back at 9"
    assert english["locale"] == "en-GB"
    assert english["key"] != first_key

    refused = await admin.put(
        f"{WEB}/settings/banner", headers=CSRF, json=changed | {"messages": {}}
    )
    assert refused.status_code == 422


# ── Webhooks ──────────────────────────────────────────────────────────


async def _webhook(admin: httpx.AsyncClient, events: list[str]) -> dict[str, Any]:
    created = await admin.post(
        f"{WEB}/admin/webhooks",
        headers=CSRF,
        json={"name": "Home", "url": "https://hooks.example.com/cuisine", "events": events},
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def test_webhook_secret_is_shown_once_and_events_include_the_cookbook(
    admin: httpx.AsyncClient, sender: FakeSender
) -> None:
    events = {e["key"] for e in (await admin.get(f"{WEB}/admin/webhooks/events")).json()}
    assert {"user.created", "user.deleted", "settings.changed", "recipe.published"} <= events
    hook = await _webhook(admin, ["user.created"])
    assert hook["secret"].startswith("whsec_")
    listed = (await admin.get(f"{WEB}/admin/webhooks")).json()
    assert "secret" not in listed[0]
    rotated = (
        await admin.post(f"{WEB}/admin/webhooks/{hook['id']}/rotate-secret", headers=CSRF)
    ).json()
    assert rotated["secret"] != hook["secret"]


@pytest.mark.parametrize(
    ("url", "events"),
    [
        ("http://backend:3000/x", ["user.created"]),
        ("https://hooks.example.com/x", ["no.such.event"]),
        ("https://hooks.example.com/x", []),
    ],
)
async def test_bad_webhooks_are_refused(
    admin: httpx.AsyncClient, sender: FakeSender, url: str, events: list[str]
) -> None:
    refused = await admin.post(
        f"{WEB}/admin/webhooks", headers=CSRF, json={"name": "x", "url": url, "events": events}
    )
    assert refused.status_code == 422


async def test_test_send_is_signed_and_logged(admin: httpx.AsyncClient, sender: FakeSender) -> None:
    hook = await _webhook(admin, ["user.created"])
    delivery = (await admin.post(f"{WEB}/admin/webhooks/{hook['id']}/test", headers=CSRF)).json()
    assert delivery["status"] == "succeeded"
    assert delivery["event"] == "ping"
    assert sender.sent[0]["secret"] == hook["secret"]
    assert sender.sent[0]["delivery_id"] == delivery["id"]
    log = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()
    assert log["total"] == 1


async def test_events_are_queued_sent_and_retried(
    admin: httpx.AsyncClient, make_user: MakeUser, sender: FakeSender
) -> None:
    hook = await _webhook(admin, ["user.created"])
    await make_user("cook")
    pending = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()["items"]
    assert pending[0]["status"] == "pending"
    assert pending[0]["payload"]["data"]["user"]["full_name"] == "Cook"

    sender.status = None
    assert await deliver_once() == 1
    failed = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()["items"][0]
    assert failed["status"] == "pending"
    assert failed["attempts"] == 1
    assert failed["error"] == "Connection failed."
    assert failed["next_attempt_at"] is not None

    sender.status = 200
    retried = (
        await admin.post(
            f"{WEB}/admin/webhooks/{hook['id']}/deliveries/{failed['id']}/retry", headers=CSRF
        )
    ).json()
    assert retried["status"] == "succeeded"
    # The receiver sees the same id on the retry, so it can drop duplicates.
    assert sender.sent[-1]["delivery_id"] == sender.sent[0]["delivery_id"]


async def test_switched_off_webhooks_queue_nothing(
    admin: httpx.AsyncClient, make_user: MakeUser, sender: FakeSender
) -> None:
    hook = await _webhook(admin, ["user.created"])
    await admin.put(
        f"{WEB}/settings/notifications",
        headers=CSRF,
        json={"webhooks_enabled": False, "allow_private_webhook_targets": True},
    )
    await make_user("cook")
    log = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()
    assert log["total"] == 0


async def test_settings_changes_name_fields_never_values(
    admin: httpx.AsyncClient, sender: FakeSender
) -> None:
    hook = await _webhook(admin, ["settings.changed"])
    general = (await admin.get(f"{WEB}/settings/general")).json()
    await admin.put(
        f"{WEB}/settings/general", headers=CSRF, json=general | {"instance_name": "Ours"}
    )
    item = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()["items"][0]
    assert item["payload"]["data"] == {"section": "general", "fields": ["instance_name"]}
    assert "Ours" not in str(item["payload"])


async def test_deleting_a_user_leaves_no_trace_in_the_webhook_log(
    admin: httpx.AsyncClient, make_user: MakeUser, sender: FakeSender
) -> None:
    hook = await _webhook(admin, ["user.created", "user.deleted"])
    victim = await make_user("victim")
    deleted = await admin.delete(
        f"{WEB}/users/{victim['id']}", headers=CSRF, params={"ownerless_visibility": "instance"}
    )
    assert deleted.status_code == 204, deleted.text
    log = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()["items"]
    assert [d["event"] for d in log] == ["user.deleted"]
    assert log[0]["payload"]["data"] == {}
    assert "victim" not in str(log).lower()


# ── Notices ───────────────────────────────────────────────────────────


async def test_notices_are_shown_until_acknowledged(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    created = await admin.post(
        f"{WEB}/admin/notices",
        headers=CSRF,
        json={
            "texts": {
                "en-GB": {"title": "New feature", "body": "**Meal plans** are here."},
                "de-AT": {"title": "Neu", "body": "**Wochenpläne** sind da."},
            }
        },
    )
    assert created.status_code == 201, created.text
    notice = created.json()
    assert notice["acknowledged"] == 0

    await make_user("cook", language="deAT")
    await login(other_client, "cook@example.com", "cook-password-1")
    pending = (await other_client.get(f"{WEB}/notices/pending")).json()
    assert [p["title"] for p in pending] == ["Neu"]
    ack = await other_client.post(f"{WEB}/notices/{notice['id']}/acknowledge", headers=CSRF)
    assert ack.status_code == 204
    assert (await other_client.get(f"{WEB}/notices/pending")).json() == []

    overview = (await admin.get(f"{WEB}/admin/notices/{notice['id']}/acknowledgements")).json()
    assert [a["user"]["display_name"] for a in overview["acknowledged"]] == ["Cook"]
    assert [p["display_name"] for p in overview["pending"]] == ["Test Admin"]

    # Switched off, nobody sees it, and an acknowledgement is refused.
    await admin.put(
        f"{WEB}/admin/notices/{notice['id']}",
        headers=CSRF,
        json={"texts": {"en-GB": {"title": "New feature", "body": ""}}, "active": False},
    )
    assert (await admin.get(f"{WEB}/notices/pending")).json() == []
    refused = await admin.post(f"{WEB}/notices/{notice['id']}/acknowledge", headers=CSRF)
    assert refused.status_code == 404


async def test_notice_needs_a_title(admin: httpx.AsyncClient) -> None:
    refused = await admin.post(
        f"{WEB}/admin/notices", headers=CSRF, json={"texts": {"en-GB": {"title": "", "body": "x"}}}
    )
    assert refused.status_code == 422


async def test_a_webhook_failing_for_good_is_switched_off(
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    sender: FakeSender,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.platform.application.use_cases.admin import webhooks as webhook_use_cases

    hook = await _webhook(admin, ["user.created"])
    # Every first failure is final here, so three users make three
    # deliveries that failed for good.
    monkeypatch.setattr(webhook_use_cases, "next_attempt_after", lambda _a, _n: None)
    sender.status = 500
    for name in ("one", "two", "three"):
        await make_user(name)
    await deliver_once()
    listed = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}")).json()
    assert listed["enabled"] is False
