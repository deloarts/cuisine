"""
Refuses to start a production backend with secrets that would make it
unsafe: missing, the sample value from .env.example, too short, or the same
key used twice. The database password inside DATABASE__URL, which is the
POSTGRES_PASSWORD of the stack, gets the same check. Debug mode skips the
check, so dev setups keep working with short throwaway keys.
"""

from urllib.parse import unquote
from urllib.parse import urlsplit

from src.platform.infrastructure.config.settings import Settings

MIN_KEY_LENGTH = 32
# The install script generates 32 characters; anything shorter than this
# was typed by hand.
MIN_DATABASE_PASSWORD_LENGTH = 16
SAMPLE_VALUES = frozenset({"change_me", "changeme", "secret", ""})


class UnsafeConfigurationError(RuntimeError):
    """The configuration must be fixed before the backend may start."""


def storage_problems(settings: Settings) -> list[str]:
    """What the seaweedfs provider is missing. Checked in debug mode too,
    since the app cannot serve a file without it."""
    s = settings.storage
    if s.provider != "seaweedfs":
        return []
    found: list[str] = []
    if not s.endpoint_url:
        found.append("STORAGE__ENDPOINT_URL is required for the seaweedfs provider.")
    if not s.access_key or not s.secret_key:
        found.append("STORAGE__ACCESS_KEY and STORAGE__SECRET_KEY are required for seaweedfs.")
    elif not settings.debug and s.secret_key.strip().lower() in SAMPLE_VALUES:
        found.append("STORAGE__SECRET_KEY still has the sample value.")
    if not settings.debug and not s.public_endpoint_url:
        found.append("STORAGE__PUBLIC_ENDPOINT_URL is required for seaweedfs outside debug mode.")
    return found


def database_password_problems(url: str) -> list[str]:
    """A sample or short password in the database URL. A URL without a
    password, such as SQLite's, has nothing to check."""
    try:
        password = urlsplit(url).password
    except ValueError:
        return []
    if password is None:
        return []
    password = unquote(password)
    if password.strip().lower() in SAMPLE_VALUES:
        return ["The password in DATABASE__URL (POSTGRES_PASSWORD) still has the sample value."]
    if len(password) < MIN_DATABASE_PASSWORD_LENGTH:
        return [
            "The password in DATABASE__URL (POSTGRES_PASSWORD) needs at least "
            f"{MIN_DATABASE_PASSWORD_LENGTH} characters."
        ]
    return []


def problems(settings: Settings) -> list[str]:
    if settings.debug:
        return storage_problems(settings)
    found: list[str] = storage_problems(settings)
    keys = {
        "SECURITY__SECRET_KEY": settings.security.secret_key,
        "SECURITY__ENCRYPTION_KEY": settings.security.encryption_key,
    }
    for name, value in keys.items():
        if value.strip().lower() in SAMPLE_VALUES:
            found.append(f"{name} still has the sample value.")
        elif len(value) < MIN_KEY_LENGTH:
            found.append(f"{name} needs at least {MIN_KEY_LENGTH} characters.")
    if keys["SECURITY__SECRET_KEY"] == keys["SECURITY__ENCRYPTION_KEY"]:
        found.append("SECURITY__SECRET_KEY and SECURITY__ENCRYPTION_KEY must differ.")
    found.extend(database_password_problems(settings.database.url))
    if settings.init.password.strip().lower() in SAMPLE_VALUES:
        found.append("INIT__PASSWORD still has the sample value.")
    if not settings.domain.startswith("https://"):
        found.append("DOMAIN must be an https:// URL outside debug mode.")
    return found


def assert_safe_configuration(settings: Settings) -> None:
    found = problems(settings)
    if found:
        raise UnsafeConfigurationError(
            "Refusing to start: " + " ".join(found) + " See .env.example."
        )
