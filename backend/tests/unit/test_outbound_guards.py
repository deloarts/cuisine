"""The outbound target rules shared by webhooks and the SMTP server, the
permission rule for managing accounts, and the HSTS scheme check."""

import logging
from collections.abc import Sequence

import aiosmtplib
import pytest

from src.platform.adapters.inbound.api.middleware.security_headers import _is_https
from src.platform.adapters.outbound.external.smtp_mail_service import DELIVERY_FAILED_MESSAGE
from src.platform.adapters.outbound.external.smtp_mail_service import SmtpMailService
from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.exceptions import MailDeliveryError
from src.platform.domain.exceptions import UserOutranksActorError
from src.platform.domain.services.permission_rules import assert_may_manage
from src.shared_kernel.domain.services.clock import now_utc


def _guard(addresses: Sequence[str]) -> WebhookTargetGuard:
    async def resolve(_host: str, _port: int) -> Sequence[str]:
        return addresses

    return WebhookTargetGuard(resolver=resolve)


@pytest.mark.parametrize("address", ["fd00:ec2::254", "100.100.100.200"])
async def test_cloud_metadata_addresses_are_refused_with_private_targets_allowed(
    address: str,
) -> None:
    with pytest.raises(InvalidWebhookConfigurationError, match="never sends requests"):
        await _guard([address]).check("https://hooks.example.com/", allow_private=True)


async def test_neighbouring_private_addresses_still_pass() -> None:
    await _guard(["fd00:ec2::253", "100.100.100.201"]).check(
        "https://hooks.example.com/", allow_private=True
    )


def _mail(host: str) -> MailSettings:
    return MailSettings(enabled=True, host=host, port=1025, security="none", sender="a@b.c")


@pytest.mark.parametrize("host", ["localhost", "postgres", "redis", "127.0.0.1", "169.254.169.254"])
async def test_the_smtp_host_refuses_the_stack_and_loopback(host: str) -> None:
    service = SmtpMailService(_guard(["127.0.0.1"]))
    with pytest.raises(MailDeliveryError, match="never sends requests"):
        await service.send(_mail(host), to="x@example.com", subject="s", text="t")


async def test_a_failed_delivery_hides_the_server_answer(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def refuse(*_args: object, **_kwargs: object) -> None:
        raise aiosmtplib.SMTPException("220 internal-relay.lan ESMTP Postfix")

    monkeypatch.setattr(aiosmtplib, "send", refuse)
    # The dev stack's mail catcher and a relay on the home network pass.
    for host in ("mailpit", "relay.home.example"):
        service = SmtpMailService(_guard(["192.168.1.10"]))
        with (
            caplog.at_level(logging.WARNING, logger="cuisine"),
            pytest.raises(MailDeliveryError) as raised,
        ):
            await service.send(_mail(host), to="x@example.com", subject="s", text="t")
        assert str(raised.value) == DELIVERY_FAILED_MESSAGE
    assert "internal-relay.lan" in caplog.text


def _user(user_id: int, permissions: list[str], **extra: object) -> User:
    return User(
        id=user_id,
        full_name=f"User {user_id}",
        email=f"u{user_id}@example.com",
        created=now_utc(),
        hashed_password="x",
        permissions=permissions,
        **extra,  # type: ignore[arg-type]
    )


def test_managing_needs_every_effective_permission_of_the_target() -> None:
    manager = _user(1, ["write:users"])
    with pytest.raises(UserOutranksActorError, match="read:settings"):
        assert_may_manage(manager, _user(2, [], group_permissions=["read:settings"]))
    with pytest.raises(UserOutranksActorError):
        assert_may_manage(manager, _user(3, [], is_systemuser=True))
    assert_may_manage(manager, _user(4, ["write:users"]))
    assert_may_manage(manager, manager)
    assert_may_manage(_user(5, [], is_systemuser=True), _user(6, ["write:settings"]))


@pytest.mark.parametrize(
    ("scheme", "headers", "expected"),
    [
        ("https", [], True),
        ("http", [], False),
        # The raw header is the server's business; only the scheme counts.
        ("http", [(b"x-forwarded-proto", b"https")], False),
    ],
)
def test_hsts_reads_the_scheme_only(
    scheme: str, headers: list[tuple[bytes, bytes]], expected: bool
) -> None:
    assert _is_https({"type": "http", "scheme": scheme, "headers": headers}) is expected
