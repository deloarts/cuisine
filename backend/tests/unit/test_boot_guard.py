"""The production boot guard."""

import pytest

from src.platform.infrastructure.config.boot_guard import UnsafeConfigurationError
from src.platform.infrastructure.config.boot_guard import assert_safe_configuration
from src.platform.infrastructure.config.boot_guard import problems
from src.platform.infrastructure.config.settings import cfg

STRONG_A = "a" * 40
STRONG_B = "b" * 40


def _settings(**overrides: object):  # type: ignore[no-untyped-def]
    settings = cfg.model_copy(deep=True)
    settings.debug = False
    settings.domain = "https://cuisine.example.com"
    settings.security.secret_key = STRONG_A
    settings.security.encryption_key = STRONG_B
    settings.init.password = "a-real-password"
    for key, value in overrides.items():
        target, _, attr = key.rpartition("__")
        obj = getattr(settings, target) if target else settings
        setattr(obj, attr, value)
    return settings


def test_strong_configuration_passes() -> None:
    assert problems(_settings()) == []


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"security__secret_key": "change_me"}, "sample value"),
        ({"security__encryption_key": "short"}, "at least 32"),
        ({"security__encryption_key": STRONG_A}, "must differ"),
        ({"init__password": "change_me"}, "INIT__PASSWORD"),
        ({"domain": "http://cuisine.example.com"}, "https://"),
    ],
)
def test_unsafe_configuration_is_refused(override: dict[str, object], message: str) -> None:
    with pytest.raises(UnsafeConfigurationError, match=message):
        assert_safe_configuration(_settings(**override))


def test_debug_mode_skips_the_guard() -> None:
    assert problems(_settings(debug=True, **{"security__secret_key": "x"})) == []


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("postgresql+psycopg://cuisine:change_me@postgres:5432/cuisine", "sample value"),
        ("postgresql+psycopg://cuisine:@postgres:5432/cuisine", "sample value"),
        ("postgresql+psycopg://cuisine:short@postgres:5432/cuisine", "at least 16"),
    ],
)
def test_a_weak_database_password_is_refused(url: str, message: str) -> None:
    with pytest.raises(UnsafeConfigurationError, match=message):
        assert_safe_configuration(_settings(database__url=url))


def test_a_strong_database_password_passes() -> None:
    url = "postgresql+psycopg://cuisine:Zm9vYmFyYmF6cXV1eC0xMjM0NTY3@postgres:5432/cuisine"
    assert problems(_settings(database__url=url)) == []
