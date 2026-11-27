"""Mail and its templates, maintenance mode, retention, "back up now", the
log viewer, feature switches, legal pages with the blocking privacy
statement, consents and the groups directory."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.bootstrap.nightly_jobs import run_nightly_once
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.external.system.backup_control import FileBackupControl
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemySecurityEventRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.infrastructure.logging.logger import log
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import ADMIN
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login

WEB = "/api/v1/web"


class FakeMail:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(
        self, settings: MailSettings, *, to: str, subject: str, text: str, html: str | None = None
    ) -> None:
        self.sent.append({"to": to, "subject": subject, "text": text, "html": html})


@pytest.fixture
def mail(monkeypatch: pytest.MonkeyPatch) -> FakeMail:
    fake = FakeMail()
    monkeypatch.setattr(deps, "mail_service", lambda: fake)
    return fake


async def _enable_mail(admin: httpx.AsyncClient, **extra: Any) -> None:
    body = {
        "enabled": True,
        "host": "mail.example.com",
        "port": 587,
        "security": "starttls",
        "username": "",
        "sender": "cuisine@example.com",
        "sender_name": "Our Kitchen",
        "reply_to": "kitchen@example.com",
        "verify_certificate": False,
        "send_limit_per_hour": 60,
        "alert_recipients": ["ops@example.com"],
    } | extra
    saved = await admin.put(f"{WEB}/settings/mail", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text


# ── Mail ──────────────────────────────────────────────────────────────


async def test_mail_settings_round_trip_and_test_mail(
    admin: httpx.AsyncClient, mail: FakeMail
) -> None:
    refused = await admin.post(f"{WEB}/settings/mail/test", headers=CSRF)
    assert refused.status_code == 400
    await _enable_mail(admin)
    read = (await admin.get(f"{WEB}/settings/mail")).json()
    assert read["sender_name"] == "Our Kitchen"
    assert read["alert_recipients"] == ["ops@example.com"]
    sent = await admin.post(
        f"{WEB}/settings/mail/test", headers=CSRF, json={"to": "me@example.com"}
    )
    assert sent.status_code == 204, sent.text
    assert mail.sent[0]["to"] == "me@example.com"
    assert mail.sent[0]["subject"] == "Cuisine: test mail"
    assert "mail delivery works" in mail.sent[0]["text"]


async def test_new_user_gets_the_welcome_mail_without_the_password(
    admin: httpx.AsyncClient, mail: FakeMail, make_user: MakeUser
) -> None:
    await make_user("quiet")
    assert mail.sent == []

    await _enable_mail(admin)
    await make_user("anna", password="anna-password-1")
    await make_user("lena", language="deAT")
    await make_user("idle", is_active=False)

    assert [m["to"] for m in mail.sent] == ["anna@example.com", "lena@example.com"]
    english, german = mail.sent
    assert english["subject"] == "Welcome to Cuisine"
    assert "Hello Anna," in english["text"]
    assert "anna@example.com" in english["text"]
    assert "/login" in (english["html"] or "")
    assert "anna-password-1" not in english["text"] + (english["html"] or "")
    assert german["subject"] == "Willkommen bei Cuisine"
    assert "Hallo Lena," in german["text"]


async def test_a_failing_welcome_mail_never_fails_the_creation(
    admin: httpx.AsyncClient, mail: FakeMail, make_user: MakeUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _enable_mail(admin)

    async def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise ConnectionError("the server hung up")

    monkeypatch.setattr(mail, "send", refuse)
    created = await make_user("anna")
    assert created["email"] == "anna@example.com"


async def test_bad_alert_recipient_is_refused(admin: httpx.AsyncClient) -> None:
    body = {
        "enabled": False,
        "host": "",
        "port": 587,
        "security": "starttls",
        "username": "",
        "sender": "",
        "alert_recipients": ["not an address"],
    }
    assert (await admin.put(f"{WEB}/settings/mail", headers=CSRF, json=body)).status_code == 422


async def test_templates_default_edit_preview_and_files(
    admin: httpx.AsyncClient, mail: FakeMail
) -> None:
    kinds = {k["kind"]: k for k in (await admin.get(f"{WEB}/settings/mail/templates")).json()}
    assert set(kinds) == {"test_mail", "operational_alert", "user_created"}
    german = next(t for t in kinds["test_mail"]["templates"] if t["locale"] == "de-AT")
    assert german["customized"] is False and "Testmail" in german["subject"]

    preview = await admin.post(
        f"{WEB}/settings/mail/templates/test_mail/preview",
        headers=CSRF,
        json={"subject": "Hi {{ full_name }}", "body": "<p>{{ full_name }} at {{ domain }}</p>"},
    )
    assert preview.json() == {
        "subject": "Hi Anna",
        "html": "<p>Anna at https://cuisine.example.com</p>",
    }
    broken = await admin.put(
        f"{WEB}/settings/mail/templates/test_mail",
        headers=CSRF,
        json={"en-GB": {"subject": "x", "body": "{% if %}"}},
    )
    assert broken.status_code == 422

    custom = "<html><head><title>Custom {{ instance_name }}</title></head><body>Hello</body></html>"
    imported = await admin.post(
        f"{WEB}/settings/mail/templates/test_mail/import",
        headers=CSRF,
        data={"locale": "en-GB"},
        files={"file": ("test_mail.en-GB.html", custom.encode(), "text/html")},
    )
    assert imported.status_code == 204, imported.text
    exported = await admin.get(
        f"{WEB}/settings/mail/templates/test_mail/export", params={"locale": "en-GB"}
    )
    assert "Custom {{ instance_name }}" in exported.text
    assert "attachment" in exported.headers["content-disposition"]

    await _enable_mail(admin)
    await admin.post(f"{WEB}/settings/mail/test", headers=CSRF)
    assert mail.sent[-1]["subject"] == "Custom Cuisine"

    reset = await admin.put(
        f"{WEB}/settings/mail/templates/test_mail",
        headers=CSRF,
        json={"en-GB": {"subject": "", "body": ""}},
    )
    assert reset.status_code == 204
    after = {k["kind"]: k for k in (await admin.get(f"{WEB}/settings/mail/templates")).json()}
    english = next(t for t in after["test_mail"]["templates"] if t["locale"] == "en-GB")
    assert english["customized"] is False


async def test_template_values_are_escaped(admin: httpx.AsyncClient, mail: FakeMail) -> None:
    await _enable_mail(admin)
    await admin.put(
        f"{WEB}/settings/mail/templates/test_mail",
        headers=CSRF,
        json={"en-GB": {"subject": "Hi", "body": "<p>{{ full_name }}</p>"}},
    )
    me = (await admin.get(f"{WEB}/users/me")).json()
    await admin.patch(f"{WEB}/users/me", headers=CSRF, json={"full_name": "<b>Boss</b>"})
    await admin.post(f"{WEB}/settings/mail/test", headers=CSRF)
    assert mail.sent[-1]["html"] == "<p>&lt;b&gt;Boss&lt;/b&gt;</p>"
    assert me["is_systemuser"] is True


# ── Maintenance ───────────────────────────────────────────────────────


async def test_maintenance_makes_the_app_read_only(
    admin: httpx.AsyncClient, client: httpx.AsyncClient, mail: FakeMail
) -> None:
    await _enable_mail(admin)
    switched = await admin.put(
        f"{WEB}/settings/maintenance",
        headers=CSRF,
        json={"enabled": True, "messages": {"en-GB": "Upgrading, back at 9."}},
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["since"] is not None
    assert any("Maintenance mode" in m["subject"] for m in mail.sent)

    refused = await admin.post(f"{WEB}/groups", headers=CSRF, json={"name": "x"})
    assert refused.status_code == 503
    assert refused.json()["code"] == "MaintenanceModeError"
    assert refused.json()["detail"] == "Upgrading, back at 9."
    assert (await admin.get(f"{WEB}/users/me")).status_code == 200
    info = (await client.get("/api/v1/public/info")).json()
    assert info["maintenance"] == {
        "enabled": True,
        "message": "Upgrading, back at 9.",
        "since": switched.json()["since"],
    }
    off = await admin.put(f"{WEB}/settings/maintenance", headers=CSRF, json={"enabled": False})
    assert off.status_code == 200
    assert (await admin.post(f"{WEB}/groups", headers=CSRF, json={"name": "x"})).status_code == 201


# ── Retention, backups, logs ──────────────────────────────────────────


async def test_nightly_purge_follows_the_retention(admin: httpx.AsyncClient) -> None:
    await admin.put(
        f"{WEB}/settings/retention",
        headers=CSRF,
        json={
            "security_log_days": 30,
            "agent_calls_days": 30,
            "webhook_deliveries_days": 30,
            "recipe_revisions_days": 30,
        },
    )
    async with SessionLocal() as db:
        await SqlAlchemySecurityEventRepository(db).add(
            SecurityEvent(
                event_type=SecurityEventType.LOGIN,
                outcome=SecurityEventOutcome.SUCCESS,
                created=now_utc() - timedelta(days=40),
            )
        )
        await db.commit()
    before = (await admin.get(f"{WEB}/security-events")).json()["total"]
    assert await run_nightly_once(force=True) is True
    assert await run_nightly_once() is False
    after = (await admin.get(f"{WEB}/security-events")).json()["total"]
    assert after == before - 1


async def test_back_up_now_and_failed_backup_alert(
    admin: httpx.AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mail: FakeMail
) -> None:
    assert (await admin.post(f"{WEB}/admin/backups/run", headers=CSRF)).status_code == 503
    control = FileBackupControl(str(tmp_path))
    monkeypatch.setattr(deps, "backup_control", lambda: control)
    assert (await admin.post(f"{WEB}/admin/backups/run", headers=CSRF)).status_code == 202
    assert (tmp_path / "request").is_file()
    assert (await admin.post(f"{WEB}/admin/backups/run", headers=CSRF)).status_code == 409
    storage = (await admin.get(f"{WEB}/admin/storage")).json()
    assert storage["backup_now_available"] is True
    assert storage["backup_requested"] is True

    (tmp_path / "request").unlink()
    (tmp_path / "status.json").write_text(
        json.dumps(
            {
                "trigger": "manual",
                "started": "2026-11-21T03:00:00Z",
                "finished": None,
                "ok": False,
                "file": None,
            }
        )
    )
    await _enable_mail(admin)
    await run_nightly_once(force=True)
    alerts = [m for m in mail.sent if "database backup" in m["subject"].lower()]
    assert alerts and alerts[0]["to"] == "ops@example.com"
    await run_nightly_once(force=True)
    assert len([m for m in mail.sent if "database backup" in m["subject"].lower()]) == 1

    guidance = (await admin.get(f"{WEB}/admin/backups/restore-guidance")).json()
    assert any(step["command"] and "pg_restore" in step["command"] for step in guidance)


async def test_log_viewer_redacts_secrets(admin: httpx.AsyncClient) -> None:
    log.warning("Connecting with password=hunter2hunter2 and Bearer abcdefghijklmnop")
    entries = (await admin.get(f"{WEB}/admin/logs")).json()
    message = next(e["message"] for e in entries if "Connecting with" in e["message"])
    assert "hunter2" not in message and "abcdefghijklmnop" not in message
    assert "[redacted]" in message


# ── Feature switches ──────────────────────────────────────────────────


async def test_feature_switches_are_one_source(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    features = (await admin.get(f"{WEB}/settings/features")).json()
    # Every switch starts on, peering included.
    assert all(features.values())
    await admin.put(f"{WEB}/settings/features", headers=CSRF, json=features | {"agents": False})
    assert (await admin.get(f"{WEB}/settings/agents")).json()["enabled"] is False
    agents = (await admin.get(f"{WEB}/settings/agents")).json() | {"enabled": True}
    await admin.put(f"{WEB}/settings/agents", headers=CSRF, json=agents)
    assert (await admin.get(f"{WEB}/settings/features")).json()["agents"] is True
    info = (await client.get("/api/v1/public/info")).json()
    assert info["features"]["households"] is True


# ── Legal and the privacy statement ───────────────────────────────────


async def _publish_privacy(admin: httpx.AsyncClient) -> dict[str, Any]:
    draft = (await admin.get(f"{WEB}/admin/legal/privacy/draft")).json()["body"]
    published = await admin.post(
        f"{WEB}/admin/legal/privacy", headers=CSRF, json={"texts": {"en-GB": draft}}
    )
    assert published.status_code == 201, published.text
    body: dict[str, Any] = published.json()
    return body


async def test_draft_names_the_real_configuration(admin: httpx.AsyncClient) -> None:
    draft = (await admin.get(f"{WEB}/admin/legal/privacy/draft")).json()["body"]
    assert "kept for 14 days" in draft
    assert "{{ privacy_mode }}" in draft
    german = (
        await admin.get(f"{WEB}/admin/legal/privacy/draft", params={"locale": "de-AT"})
    ).json()["body"]
    assert "14 Tage aufbewahrt" in german


@pytest.mark.usefixtures("user_choice_privacy")
async def test_privacy_statement_blocks_until_acknowledged(
    admin: httpx.AsyncClient,
    client: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
) -> None:
    page = await _publish_privacy(admin)
    assert "The mode is the administrator's decision" in page["body"]
    assert "**your choice**" in page["body"]
    # The publishing admin has read it.
    assert (await admin.get(f"{WEB}/groups")).status_code == 200

    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    me = (await other_client.get(f"{WEB}/users/me")).json()
    assert me["privacy_acknowledgement_pending"] is True
    assert me["privacy_mode"] == {
        "mode": "user_choice",
        "default_visibility": "instance",
        "allow_public_recipes": False,
    }
    blocked = await other_client.get(f"{WEB}/users/directory")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "PrivacyAcknowledgementRequiredError"
    public = await client.get("/api/v1/public/legal/privacy")
    assert public.json()["version"] == page["version"]

    stale = await other_client.post(
        f"{WEB}/users/me/privacy/acknowledge", headers=CSRF, json={"version": 99}
    )
    assert stale.status_code == 409
    ack = await other_client.post(
        f"{WEB}/users/me/privacy/acknowledge", headers=CSRF, json={"version": page["version"]}
    )
    assert ack.status_code == 204
    assert (await other_client.get(f"{WEB}/users/directory")).status_code == 200

    # A new privacy mode is a new statement version that everyone confirms.
    await admin.put(
        f"{WEB}/settings/privacy",
        headers=CSRF,
        json={"default_recipe_visibility": "instance", "users_may_change_visibility": False},
    )
    assert (await other_client.get(f"{WEB}/users/directory")).status_code == 403
    renewed = (await client.get("/api/v1/public/legal/privacy")).json()
    assert renewed["version"] == page["version"] + 1
    assert "**instance**" in renewed["body"]
    info = (await client.get("/api/v1/public/info")).json()
    assert info["privacy_mode"] == "instance"

    declined = await other_client.post(f"{WEB}/users/me/privacy/decline", headers=CSRF)
    assert declined.status_code == 204
    assert (await other_client.get(f"{WEB}/users/me")).status_code == 401


async def test_imprint_is_public_and_versioned(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    assert (await client.get("/api/v1/public/legal/imprint")).status_code == 404
    for text in ("Kitchen of Anna", "Kitchen of Anna and Ben"):
        await admin.post(
            f"{WEB}/admin/legal/imprint", headers=CSRF, json={"texts": {"en-GB": text}}
        )
    page = (await client.get("/api/v1/public/legal/imprint", params={"locale": "de-AT"})).json()
    assert page["version"] == 2 and page["body"] == "Kitchen of Anna and Ben"
    history = (await admin.get(f"{WEB}/admin/legal/imprint/versions")).json()
    assert [v["version"] for v in history] == [2, 1]


# ── Consents ──────────────────────────────────────────────────────────


async def test_agent_tokens_need_the_ai_agents_consent(admin: httpx.AsyncClient) -> None:
    expires = (now_utc() + timedelta(days=10)).isoformat()
    token = {"name": "agent", "permissions": ["use:mcp"], "expires_at": expires}
    refused = await admin.post(f"{WEB}/users/me/personal-access-tokens", headers=CSRF, json=token)
    assert refused.status_code == 403
    assert refused.json()["code"] == "ConsentRequiredError"
    consents = (await admin.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)).json()
    assert next(c for c in consents if c["kind"] == "ai_agents")["granted"] is True
    created = await admin.post(f"{WEB}/users/me/personal-access-tokens", headers=CSRF, json=token)
    assert created.status_code == 201, created.text

    withdrawn = await admin.delete(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    assert next(c for c in withdrawn.json() if c["kind"] == "ai_agents")["granted"] is False
    tokens = (await admin.get(f"{WEB}/users/me/personal-access-tokens")).json()
    assert not [t for t in tokens if "use:mcp" in t["permissions"]]


async def test_withdrawing_health_data_erases_through_the_registered_port(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await admin.put(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    erased: list[int] = []

    class Eraser:
        async def erase(self, user_id: int) -> int:
            erased.append(user_id)
            return 3

    monkeypatch.setattr(deps, "_health_data_eraser", [lambda _db: Eraser()])
    withdrawn = await admin.delete(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    assert withdrawn.status_code == 200
    assert len(erased) == 1
    me = (await admin.get(f"{WEB}/users/me")).json()
    assert me["consent_health_data_at"] is None


async def test_withdrawing_health_data_without_an_eraser_is_refused(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(deps, "_health_data_eraser", [])
    await admin.put(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    refused = await admin.delete(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    assert refused.status_code == 403


# ── Directory and backup retention ────────────────────────────────────


async def test_groups_directory_and_backup_retention_for_everyone(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await admin.post(f"{WEB}/groups", headers=CSRF, json={"name": "Family"})
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    directory = (await other_client.get(f"{WEB}/groups/directory")).json()
    assert [g["name"] for g in directory] == ["Family"]
    assert set(directory[0]) == {"id", "name"}
    retention = (await other_client.get(f"{WEB}/settings/backup-retention")).json()
    assert retention["keep_days"] == 14
    assert retention["gone_by"] == (now_utc().date() + timedelta(days=15)).isoformat()
    assert ADMIN["login"] == "system"


# ── Log table filters ─────────────────────────────────────────────────


async def test_security_log_filters_sort_and_range(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    await client.post("/api/v1/auth/login", json={"login": "system", "password": "wrong"})
    failed = (
        await admin.get(
            f"{WEB}/security-events", params={"event_type": "login", "outcome": "failure"}
        )
    ).json()
    assert failed["total"] == 1
    assert {e["outcome"] for e in failed["items"]} == {"failure"}
    logins = (
        await admin.get(f"{WEB}/security-events", params={"event_type": "login", "sort": "oldest"})
    ).json()
    assert logins["total"] == 2
    assert logins["items"][0]["created"] <= logins["items"][-1]["created"]
    today = now_utc().date()
    future = (
        await admin.get(
            f"{WEB}/security-events", params={"date_from": (today + timedelta(days=1)).isoformat()}
        )
    ).json()
    assert future["total"] == 0
    bad = await admin.get(
        f"{WEB}/security-events",
        params={"date_from": today.isoformat(), "date_to": (today - timedelta(days=1)).isoformat()},
    )
    assert bad.status_code == 422
    own = (await admin.get(f"{WEB}/users/me/security-events", params={"outcome": "success"})).json()
    assert all(e["outcome"] == "success" for e in own["items"])


async def test_agent_call_filters_and_tool_list(admin: httpx.AsyncClient) -> None:
    from src.platform.adapters.outbound.persistence.repositories.agent_call_repository import (
        SqlAlchemyAgentCallRepository,
    )
    from src.platform.domain.entities.agent_call import AgentCall
    from src.platform.domain.value_objects.agent import AgentCallOutcome
    from src.platform.domain.value_objects.agent import AgentTokenKind

    me = (await admin.get(f"{WEB}/users/me")).json()
    async with SessionLocal() as db:
        from src.platform.adapters.outbound.persistence.repositories.user_repository import (
            SqlAlchemyUserRepository,
        )

        user = await SqlAlchemyUserRepository(db).get_by_public_id(me["id"])
        assert user is not None
        repo = SqlAlchemyAgentCallRepository(db)
        for tool, outcome in (
            ("search_recipes", AgentCallOutcome.OK),
            ("create_recipe_draft", AgentCallOutcome.ERROR),
            ("search_recipes", AgentCallOutcome.REFUSED),
        ):
            await repo.append(
                AgentCall(
                    called_at=now_utc(),
                    user_id=user.id,
                    token_kind=AgentTokenKind.PAT,
                    token_id=1,
                    token_name="agent",
                    tool=tool,
                    outcome=outcome,
                )
            )
        await db.commit()
    tools = (await admin.get(f"{WEB}/agent-calls/tools")).json()
    assert tools == ["create_recipe_draft", "search_recipes"]
    searches = (await admin.get(f"{WEB}/agent-calls", params={"tool": "search_recipes"})).json()
    assert searches["total"] == 2
    errors = (await admin.get(f"{WEB}/users/me/agent-calls", params={"outcome": "error"})).json()
    assert [c["tool"] for c in errors["items"]] == ["create_recipe_draft"]
    assert (await admin.get(f"{WEB}/users/me/agent-calls/tools")).json() == tools
