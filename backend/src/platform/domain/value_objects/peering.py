"""
The peering protocol's constants and the catalogue of what this instance
offers a peer: the exchange formats with the versions it can send and read,
and its capabilities.

Platform owns pairing but knows no recipe concept, so the cookbook registers
its formats and capabilities from the composition root
(`src/bootstrap/peering.py`), the same way it registers webhook events.
"""

from dataclasses import dataclass

# The protocol version this release speaks. The URL path carries it
# (`/api/peering/v1`), and every peering request and answer names the
# version in use in the `Cuisine-Peering-Version` header.
CURRENT_PROTOCOL_VERSION = 1
# The support window: the current and the previous protocol version.
SUPPORTED_PROTOCOL_VERSIONS: tuple[int, ...] = tuple(
    v for v in (CURRENT_PROTOCOL_VERSION - 1, CURRENT_PROTOCOL_VERSION) if v >= 1
)

VERSION_HEADER = "Cuisine-Peering-Version"
# The sending instance's `instance_id`, which names the secret that signs
# the request.
PEER_HEADER = "Cuisine-Peer"
# Standard Webhooks headers, shared by every signed peering request.
MESSAGE_ID_HEADER = "webhook-id"
TIMESTAMP_HEADER = "webhook-timestamp"
SIGNATURE_HEADER = "webhook-signature"


@dataclass(frozen=True)
class PeeringFormat:
    name: str
    # The versions this instance can send and read over peering, oldest
    # first: the current one and the one before it.
    versions: tuple[int, ...]
    # A pairing is refused when the two instances share no version of a
    # required format, or when the peer does not know it at all.
    required: bool = False


_FORMATS: dict[str, PeeringFormat] = {}
_CAPABILITIES: set[str] = set()


def register_peering_format(fmt: PeeringFormat) -> None:
    """Adds a format to the catalogue. Registering the same format twice is
    a no-op, so imports may repeat."""
    known = _FORMATS.get(fmt.name)
    if known is not None and known != fmt:
        raise ValueError(f"Peering format {fmt.name!r} is registered twice.")
    _FORMATS[fmt.name] = fmt


def register_peering_capability(name: str) -> None:
    _CAPABILITIES.add(name)


def peering_formats() -> list[PeeringFormat]:
    return sorted(_FORMATS.values(), key=lambda f: f.name)


def peering_capabilities() -> list[str]:
    return sorted(_CAPABILITIES)
