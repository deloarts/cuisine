"""Permission grants, session expiry, password rules, token lifetimes and
content types."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_session import UserSession
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import InvalidPermissionError
from src.platform.domain.exceptions import SystemUserProtectedError
from src.platform.domain.exceptions import WeakPasswordError
from src.platform.domain.services.content_types import content_disposition
from src.platform.domain.services.content_types import is_inline_safe
from src.platform.domain.services.content_types import safe_file_name
from src.platform.domain.services.login_rules import assert_can_disable_totp
from src.platform.domain.services.login_rules import assert_can_use_passkeys
from src.platform.domain.services.login_rules import effective_trusted_device_days
from src.platform.domain.services.login_rules import totp_enrolment_required
from src.platform.domain.services.password_rules import assert_password_acceptable
from src.platform.domain.services.permission_rules import assert_grantable_by
from src.platform.domain.services.permission_rules import assert_grantable_to_token
from src.platform.domain.services.session_rules import session_cookie_max_age
from src.platform.domain.services.session_rules import session_expired
from src.platform.domain.services.session_rules import session_hard_expiry
from src.platform.domain.services.token_lifetime import assert_token_lifetime
from src.platform.domain.value_objects.permission import Permission

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _user(**kwargs: object) -> User:
    return User(
        full_name="U",
        email="u@example.com",
        created=NOW,
        hashed_password="x",
        **kwargs,  # type: ignore[arg-type]
    )


def test_effective_permissions_are_the_union_of_direct_and_group_grants() -> None:
    user = _user(permissions=["read:settings"], group_permissions=["write:users", "read:settings"])
    assert user.effective_permissions == ["read:settings", "write:users"]
    assert user.has_permission("write:users")
    assert not user.has_permission("write:settings")


def test_system_user_passes_every_check() -> None:
    assert _user(is_systemuser=True).has_permission("write:settings")


def test_grant_is_capped_at_the_granters_permissions() -> None:
    granter = _user(permissions=["write:users", "read:settings"])
    assert_grantable_by(granter, ["read:settings"])
    with pytest.raises(InvalidPermissionError):
        assert_grantable_by(granter, ["write:settings"])


def test_unknown_permission_is_refused_even_for_the_system_user() -> None:
    with pytest.raises(InvalidPermissionError):
        assert_grantable_by(_user(is_systemuser=True), ["write:everything"])


def test_tokens_never_carry_instance_control() -> None:
    root = _user(is_systemuser=True)
    assert_grantable_to_token(root, [Permission.READ_SETTINGS])
    for blocked in (Permission.WRITE_SETTINGS, Permission.WRITE_USERS, Permission.WRITE_GROUPS):
        with pytest.raises(InvalidPermissionError):
            assert_grantable_to_token(root, [blocked])


def _session(created: datetime, last_seen: datetime) -> UserSession:
    return UserSession(user_id=1, created=created, last_seen_at=last_seen)


def test_session_expires_after_idle_timeout() -> None:
    settings = SecuritySettings(session_timeout_minutes=60, session_max_lifetime_days=30)
    fresh = _session(NOW - timedelta(minutes=10), NOW - timedelta(minutes=10))
    idle = _session(NOW - timedelta(hours=2), NOW - timedelta(hours=2))
    assert not session_expired(fresh, settings, NOW)
    assert session_expired(idle, settings, NOW)


def test_session_expires_after_absolute_lifetime_however_active() -> None:
    settings = SecuritySettings(session_timeout_minutes=60, session_max_lifetime_days=1)
    busy = _session(NOW - timedelta(days=2), NOW - timedelta(minutes=1))
    assert session_expired(busy, settings, NOW)


def test_revoked_session_is_expired() -> None:
    session = _session(NOW, NOW)
    session.revoked_at = NOW
    assert session_expired(session, SecuritySettings(), NOW)


def test_system_user_session_ends_15_minutes_after_sign_in_however_active() -> None:
    settings = SecuritySettings(session_timeout_minutes=0, session_max_lifetime_days=30)
    young = _session(NOW - timedelta(minutes=14), NOW)
    old = _session(NOW - timedelta(minutes=15), NOW)
    assert not session_expired(young, settings, NOW, is_systemuser=True)
    assert session_expired(old, settings, NOW, is_systemuser=True)
    assert not session_expired(old, settings, NOW)
    assert session_hard_expiry(old, settings, is_systemuser=True) == NOW
    assert session_cookie_max_age(settings, is_systemuser=True) == 15 * 60


def test_system_user_always_needs_its_second_factor() -> None:
    system = _user(is_systemuser=True)
    cook = _user()
    assert totp_enrolment_required(system, enforce_totp=False)
    assert not totp_enrolment_required(cook, enforce_totp=False)
    assert totp_enrolment_required(cook, enforce_totp=True)
    assert effective_trusted_device_days(system, 30) == 0
    assert effective_trusted_device_days(cook, 30) == 30
    with pytest.raises(SystemUserProtectedError):
        assert_can_disable_totp(system)
    with pytest.raises(SystemUserProtectedError):
        assert_can_use_passkeys(system)
    assert_can_disable_totp(cook)
    assert_can_use_passkeys(cook)


@pytest.mark.parametrize(
    "password",
    ["short", "x" * 73, "Cook1234@Example.com"],
)
def test_weak_passwords_are_refused(password: str) -> None:
    with pytest.raises(WeakPasswordError):
        assert_password_acceptable(password, 10, email="cook1234@example.com")


def test_acceptable_password() -> None:
    assert_password_acceptable("correct horse battery", 10, email="u@example.com")


def test_token_lifetime_cap() -> None:
    assert_token_lifetime(NOW + timedelta(days=30), 365, NOW)
    assert_token_lifetime(None, 0, NOW)
    with pytest.raises(InvalidInputError):
        assert_token_lifetime(None, 365, NOW)
    with pytest.raises(InvalidInputError):
        assert_token_lifetime(NOW + timedelta(days=400), 365, NOW)
    with pytest.raises(InvalidInputError):
        assert_token_lifetime(NOW - timedelta(days=1), 0, NOW)


def test_only_raster_images_and_pdf_render_inline() -> None:
    assert is_inline_safe("image/webp")
    assert is_inline_safe("application/pdf; charset=binary")
    assert not is_inline_safe("image/svg+xml")
    assert not is_inline_safe("text/html")


def test_content_disposition_is_header_safe_and_keeps_unicode() -> None:
    header = content_disposition('Käse "Spätzle"\r\n.pdf', inline=False)
    assert header.startswith("attachment; ")
    assert "\r" not in header and "\n" not in header
    assert "filename*=UTF-8''K%C3%A4se" in header
    assert safe_file_name("../../etc/passwd") == "passwd"
    assert safe_file_name("") == "file"
