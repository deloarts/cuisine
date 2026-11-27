"""Which requests maintenance mode refuses, and its message."""

from src.platform.domain.entities.settings import MaintenanceSettings

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Signing in and out, switching maintenance off, and the probes stay open.
# The MCP surface is closed as a whole, since its reads and writes share
# one route.
_OPEN_PREFIXES = ("/api/v1/auth/", "/api/v1/public/", "/health", "/ready")
_OPEN_PATHS = frozenset({"/api/v1/web/settings/maintenance"})
MCP_PATH = "/api/v1/mcp"

DEFAULT_MESSAGES = {
    "en-GB": "Cuisine is in maintenance and read-only for a moment. Please try again later.",
    "de-AT": "Cuisine wird gerade gewartet und ist kurz nur lesbar. Bitte versuch es später.",
}


def refused_in_maintenance(method: str, path: str) -> bool:
    if path.startswith(MCP_PATH):
        return True
    if method.upper() in SAFE_METHODS:
        return False
    if path in _OPEN_PATHS:
        return False
    return not path.startswith(_OPEN_PREFIXES)


def maintenance_message(settings: MaintenanceSettings, locale: str) -> str:
    for candidate in (locale, "en-GB"):
        text = settings.messages.get(candidate, "").strip()
        if text:
            return text
    return DEFAULT_MESSAGES.get(locale, DEFAULT_MESSAGES["en-GB"])
