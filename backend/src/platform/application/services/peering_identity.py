"""
Who this instance is to its peers, and the identity part of the peering
messages: what the handshake and `/hello` carry about an instance.

The messages are plain dicts on the wire. Readers ignore fields they do not
know, so a newer release of the same protocol version can add fields.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.services.peering_rules import PEER_SECRET_PREFIX
from src.platform.domain.services.peering_rules import Negotiated
from src.platform.domain.value_objects.peering import SUPPORTED_PROTOCOL_VERSIONS
from src.platform.domain.value_objects.peering import peering_capabilities
from src.platform.domain.value_objects.peering import peering_formats
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository

NAME_MAX = 128
LIST_MAX = 64


@dataclass(frozen=True)
class InstanceIdentity:
    instance_id: UUID
    name: str
    base_url: str
    app_version: str
    protocol_versions: tuple[int, ...]
    formats: dict[str, tuple[int, ...]]
    capabilities: tuple[str, ...]

    @property
    def current_protocol(self) -> int:
        return max(self.protocol_versions)


@dataclass(frozen=True)
class PeerIdentity:
    """What another instance says about itself."""

    instance_id: UUID
    name: str
    base_url: str
    app_version: str
    protocol_versions: list[int]
    formats: dict[str, list[int]]
    capabilities: list[str]


def required_formats() -> set[str]:
    return {f.name for f in peering_formats() if f.required}


class PeeringIdentity:
    def __init__(
        self, *, settings_repo: ISettingsRepository, base_url: str, app_version: str
    ) -> None:
        self._settings = settings_repo
        self._base_url = base_url.rstrip("/")
        self._app_version = app_version

    @property
    def base_url(self) -> str:
        return self._base_url

    async def current(self) -> InstanceIdentity:
        general = await self._settings.get_general()
        return InstanceIdentity(
            instance_id=await self._settings.instance_id(),
            name=general.instance_name,
            base_url=self._base_url,
            app_version=self._app_version,
            protocol_versions=SUPPORTED_PROTOCOL_VERSIONS,
            formats={f.name: f.versions for f in peering_formats()},
            capabilities=tuple(peering_capabilities()),
        )


def identity_message(identity: InstanceIdentity) -> dict[str, Any]:
    return {
        "instance_id": str(identity.instance_id),
        "name": identity.name,
        "base_url": identity.base_url,
        "app_version": identity.app_version,
        "protocol_versions": list(identity.protocol_versions),
        "formats": {name: list(versions) for name, versions in identity.formats.items()},
        "capabilities": list(identity.capabilities),
    }


def negotiated_message(negotiated: Negotiated) -> dict[str, Any]:
    return {
        "protocol_version": negotiated.protocol_version,
        "format_versions": dict(negotiated.format_versions),
    }


def _bad(what: str) -> InvalidPeerConfigurationError:
    return InvalidPeerConfigurationError(f"The other instance sent an invalid {what}.")


def _int_list(value: Any, what: str) -> list[int]:
    if not isinstance(value, list) or len(value) > LIST_MAX:
        raise _bad(what)
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in value):
        raise _bad(what)
    return sorted(set(value))


def read_identity(data: Any) -> PeerIdentity:
    """Reads the identity fields of a peering message. Raises
    InvalidPeerConfigurationError for a missing or malformed field."""
    if not isinstance(data, dict):
        raise _bad("answer")
    try:
        instance_id = UUID(str(data.get("instance_id")))
    except ValueError as exc:
        raise _bad("instance id") from exc
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise _bad("name")
    base_url = data.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise _bad("base URL")
    app_version = data.get("app_version", "")
    formats_raw = data.get("formats", {})
    if not isinstance(formats_raw, dict) or len(formats_raw) > LIST_MAX:
        raise _bad("format list")
    capabilities = data.get("capabilities", [])
    if not isinstance(capabilities, list) or len(capabilities) > LIST_MAX:
        raise _bad("capability list")
    return PeerIdentity(
        instance_id=instance_id,
        name=name.strip()[:NAME_MAX],
        base_url=base_url.strip(),
        app_version=str(app_version)[:64] if isinstance(app_version, str) else "",
        protocol_versions=_int_list(data.get("protocol_versions"), "protocol version list"),
        formats={
            str(key)[:64]: _int_list(value, "format list") for key, value in formats_raw.items()
        },
        capabilities=sorted({str(c)[:64] for c in capabilities if isinstance(c, str)}),
    )


def read_negotiated(data: dict[str, Any]) -> Negotiated:
    version = data.get("protocol_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise _bad("protocol version")
    formats = data.get("format_versions", {})
    if not isinstance(formats, dict) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in formats.values()
    ):
        raise _bad("format version list")
    return Negotiated(
        protocol_version=version, format_versions={str(k): int(v) for k, v in formats.items()}
    )


def read_secret(data: dict[str, Any]) -> str:
    secret = data.get("secret")
    if not isinstance(secret, str) or not valid_secret(secret):
        raise _bad("secret")
    return secret


def valid_secret(secret: str) -> bool:
    return secret.startswith(PEER_SECRET_PREFIX) and 32 <= len(secret) <= 256
