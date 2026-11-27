"""The rules behind the admin area: webhook signing, retries and targets,
storage warnings, the banner, notice texts and the storage boot checks."""

import base64
import hashlib
import hmac
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

import pytest

from src.platform.adapters.outbound.external.webhook.httpx_sender import sign_payload
from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.adapters.outbound.storage.s3_store import S3ContentStore
from src.platform.domain.entities.notice import Notice
from src.platform.domain.entities.notice import NoticeText
from src.platform.domain.entities.settings import BannerSettings
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import InvalidSettingsError
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.services.banner_rules import banner_is_active
from src.platform.domain.services.banner_rules import banner_message
from src.platform.domain.services.notice_rules import notice_text
from src.platform.domain.services.notice_rules import validate_notice_texts
from src.platform.domain.services.settings_rules import validate_banner
from src.platform.domain.services.storage_rules import storage_warnings
from src.platform.domain.services.webhook_rules import MAX_ATTEMPTS
from src.platform.domain.services.webhook_rules import new_webhook_secret
from src.platform.domain.services.webhook_rules import next_attempt_after
from src.platform.domain.value_objects.storage_warning import StorageWarning
from src.platform.domain.value_objects.webhook_event import WebhookEventType
from src.platform.domain.value_objects.webhook_event import is_webhook_event
from src.platform.domain.value_objects.webhook_event import register_webhook_event
from src.platform.infrastructure.config.boot_guard import storage_problems
from src.platform.infrastructure.config.settings import Settings
from src.platform.ports.outbound.file_content_store import ContentRef

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


# ── Webhooks ──────────────────────────────────────────────────────────


def test_signature_follows_standard_webhooks() -> None:
    secret = new_webhook_secret()
    assert secret.startswith("whsec_")
    key = base64.b64decode(secret.removeprefix("whsec_"))
    expected = base64.b64encode(
        hmac.new(key, b"msg_1.1700000000.{}", hashlib.sha256).digest()
    ).decode()
    assert sign_payload(secret, "msg_1", 1700000000, "{}") == f"v1,{expected}"


def test_malformed_secret_is_refused() -> None:
    with pytest.raises(ValueError):
        sign_payload("whsec_not base64!", "id", 1, "{}")


def test_retries_back_off_and_end() -> None:
    first = next_attempt_after(1, NOW)
    second = next_attempt_after(2, NOW)
    assert first is not None and second is not None
    assert NOW < first < second
    assert next_attempt_after(MAX_ATTEMPTS, NOW) is None


def test_catalogue_takes_new_events_once() -> None:
    event = WebhookEventType("test.thing", "A test event.")
    register_webhook_event(event)
    register_webhook_event(event)
    assert is_webhook_event("test.thing")
    with pytest.raises(ValueError):
        register_webhook_event(WebhookEventType("test.thing", "Something else."))


def _guard(addresses: Sequence[str]) -> WebhookTargetGuard:
    async def resolve(_host: str, _port: int) -> Sequence[str]:
        return addresses

    return WebhookTargetGuard(resolver=resolve)


async def test_guard_accepts_public_and_private_hosts() -> None:
    await _guard(["93.184.216.34"]).check("https://hooks.example.com/x", allow_private=False)
    await _guard(["192.168.1.20"]).check("http://homeassistant.lan/hook", allow_private=True)


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/hook",
        "http://backend:3000/hook",
        "http://seaweedfs:8333/objects",
        "http://127.0.0.1/hook",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/hook",
        "ftp://hooks.example.com/hook",
        "https://user:pass@hooks.example.com/hook",
    ],
)
async def test_guard_refuses_the_instance_itself(url: str) -> None:
    with pytest.raises(InvalidWebhookConfigurationError):
        await _guard(["93.184.216.34"]).check(url, allow_private=True)


async def test_guard_refuses_private_targets_when_switched_off() -> None:
    with pytest.raises(InvalidWebhookConfigurationError):
        await _guard(["10.0.0.5"]).check("http://nas.lan/hook", allow_private=False)


async def test_guard_checks_every_resolved_address() -> None:
    with pytest.raises(InvalidWebhookConfigurationError):
        await _guard(["93.184.216.34", "127.0.0.1"]).check(
            "https://sneaky.example.com", allow_private=True
        )


# ── Storage ───────────────────────────────────────────────────────────


def test_postgres_provider_with_fresh_backup_only_warns_to_copy_backups_off() -> None:
    warnings = storage_warnings(
        provider="postgres",
        endpoint_url=None,
        backups_visible=True,
        newest_backup=NOW - timedelta(hours=3),
        now=NOW,
    )
    assert warnings == [StorageWarning.BACKUPS_ON_DATABASE_HOST]


def test_local_provider_warns_about_host_and_backup() -> None:
    warnings = storage_warnings(
        provider="local", endpoint_url=None, backups_visible=False, newest_backup=None, now=NOW
    )
    assert warnings == [
        StorageWarning.FILES_ON_DATABASE_HOST,
        StorageWarning.FILES_NOT_IN_BACKUP,
        StorageWarning.BACKUPS_NOT_VISIBLE,
    ]


def test_bundled_seaweedfs_is_on_the_database_host_but_a_remote_one_is_not() -> None:
    bundled = storage_warnings(
        provider="seaweedfs",
        endpoint_url="http://seaweedfs:8333",
        backups_visible=True,
        newest_backup=NOW - timedelta(days=3),
        now=NOW,
    )
    remote = storage_warnings(
        provider="seaweedfs",
        endpoint_url="https://s3.example.com",
        backups_visible=True,
        newest_backup=None,
        now=NOW,
    )
    assert StorageWarning.FILES_ON_DATABASE_HOST in bundled
    assert StorageWarning.BACKUP_STALE in bundled
    assert StorageWarning.FILES_ON_DATABASE_HOST not in remote
    assert StorageWarning.NO_BACKUP_YET in remote
    assert StorageWarning.FILES_NOT_IN_BACKUP in remote


def test_presigned_urls_are_signed_for_the_public_origin_and_keep_the_rules() -> None:
    store = S3ContentStore(
        bucket="objects",
        access_key="cuisine",
        secret_key="secret-secret-secret-secret",
        endpoint_url="http://seaweedfs:8333",
        public_endpoint_url="https://cuisine.example.com",
        region="us-east-1",
        use_ssl=False,
    )
    ref = ContentRef(file_id=1, public_id=uuid4())
    image = store.url_for(ref, file_name="a.webp", content_type="image/webp", inline=True)
    page = store.url_for(ref, file_name="a.html", content_type="text/html", inline=True)
    assert image is not None and page is not None
    assert image.url.startswith(f"https://cuisine.example.com/objects/{ref.key}?")
    assert "inline" in image.url
    # An unsafe type downloads even when inline was asked for.
    assert "attachment" in page.url


def _settings(**storage: object) -> Settings:
    return Settings(
        debug=False,
        security={"secret_key": "x" * 40, "encryption_key": "y" * 40},
        database={"url": "sqlite://"},
        redis={"url": "redis://localhost"},
        init={"full_name": "A", "mail": "a@example.com", "password": "pw"},
        storage=storage,
    )


def test_boot_guard_wants_a_complete_seaweedfs_configuration() -> None:
    assert storage_problems(_settings(provider="postgres")) == []
    found = storage_problems(_settings(provider="seaweedfs"))
    assert any("ENDPOINT_URL" in p for p in found)
    assert any("PUBLIC_ENDPOINT_URL" in p for p in found)
    complete = storage_problems(
        _settings(
            provider="seaweedfs",
            endpoint_url="http://seaweedfs:8333",
            public_endpoint_url="https://cuisine.example.com",
            access_key="cuisine",
            secret_key="a-long-enough-secret-value",
        )
    )
    assert complete == []


# ── Banner and notices ────────────────────────────────────────────────


def test_banner_is_active_only_inside_its_window() -> None:
    banner = BannerSettings(
        enabled=True,
        messages={"en-GB": "Maintenance tonight", "de-AT": "Heute Abend Wartung"},
        starts_at=NOW - timedelta(hours=1),
        ends_at=NOW + timedelta(hours=1),
    )
    assert banner_is_active(banner, NOW)
    assert not banner_is_active(banner, NOW + timedelta(hours=2))
    assert not banner_is_active(BannerSettings(enabled=True, messages={}), NOW)
    assert banner_message(banner, "de-AT") == "Heute Abend Wartung"
    only_german = BannerSettings(enabled=True, messages={"de-AT": "Nur Deutsch"})
    assert banner_message(only_german, "en-GB") == "Nur Deutsch"


def test_banner_needs_a_message_and_an_order() -> None:
    with pytest.raises(InvalidSettingsError):
        validate_banner(BannerSettings(enabled=True, messages={}))
    with pytest.raises(InvalidSettingsError):
        validate_banner(
            BannerSettings(enabled=False, messages={"en-GB": "x"}, starts_at=NOW, ends_at=NOW)
        )


def test_notice_texts_drop_blank_locales_and_fall_back() -> None:
    texts = validate_notice_texts(
        {"en-GB": NoticeText("New", "Hello"), "de-AT": NoticeText(" ", " ")}
    )
    assert set(texts) == {"en-GB"}
    notice = Notice(texts=texts, created=NOW, changed=NOW)
    assert notice_text(notice, "de-AT") == ("en-GB", NoticeText("New", "Hello"))
    with pytest.raises(InvalidInputError):
        validate_notice_texts({"en-GB": NoticeText("", "Body without title")})
