"""
The webhook target policy. A URL passes when it is plain http or https
without credentials, its host is not one of the stack's own service names
or localhost, and every address the host resolves to is allowed.

Always refused, whatever the settings say: loopback, link-local (which
covers the 169.254.169.254 cloud metadata address and fe80::/10),
unspecified, multicast and reserved ranges, the cloud metadata addresses
that lie outside those ranges (AWS's fd00:ec2::254 and Alibaba's
100.100.100.200), and the IPv4-mapped IPv6 forms of all of these. Private
ranges such as RFC 1918 pass unless the admin setting that allows them is
off, since a home automation server on the household's network is a normal
receiver.

Every resolved address must pass, not just the first, so a hostname cannot
hide a forbidden address behind an allowed one. `check_host` applies the
same rules to a bare host name, for the SMTP server. Adapted from glados.
"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import IPv6Address

import httpx

from src.platform.domain.exceptions import InvalidWebhookConfigurationError

_RESOLVE_TIMEOUT_SECONDS = 5.0
# The compose service names, which resolve to the stack's own containers.
STACK_HOSTS = frozenset(
    {
        "localhost",
        "backend",
        "frontend",
        "postgres",
        "redis",
        "seaweedfs",
        "maintenance",
        "backup",
        "cloudflared",
        "mailpit",
    }
)

# Metadata endpoints that the range checks below do not catch: AWS's IPv6
# endpoint is a unique local address and Alibaba's sits in the CGNAT range,
# both of which pass while private targets are allowed.
CLOUD_METADATA_ADDRESSES: frozenset[IPv4Address | IPv6Address] = frozenset(
    {
        ipaddress.ip_address("fd00:ec2::254"),
        ipaddress.ip_address("100.100.100.200"),
    }
)

Resolver = Callable[[str, int], Awaitable[Sequence[str]]]


@dataclass(frozen=True)
class WebhookTarget:
    host: str
    addresses: tuple[str, ...]


async def _system_resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses: list[str] = []
    for _family, _type, _proto, _canonname, sockaddr in infos:
        address = str(sockaddr[0])
        if address not in addresses:
            addresses.append(address)
    return addresses


def _always_refused_address(ip: IPv4Address | IPv6Address) -> bool:
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_multicast
        or ip.is_reserved
        or (isinstance(ip, IPv4Address) and ip in ipaddress.ip_network("0.0.0.0/8"))
        or ip in CLOUD_METADATA_ADDRESSES
    )


class WebhookTargetGuard:
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        resolve_timeout_seconds: float = _RESOLVE_TIMEOUT_SECONDS,
    ) -> None:
        self._resolver = resolver or _system_resolve
        self._resolve_timeout = resolve_timeout_seconds

    async def check(self, url: str, *, allow_private: bool, subject: str = "webhook") -> None:
        await self.resolve(url, allow_private=allow_private, subject=subject)

    async def resolve(
        self, url: str, *, allow_private: bool, subject: str = "webhook"
    ) -> WebhookTarget:
        """`subject` names what the URL is for in the messages, such as
        "webhook" or "peer"."""
        parsed = _parse(url, subject)
        host = parsed.raw_host.decode("ascii").rstrip(".").lower()
        if not host:
            raise InvalidWebhookConfigurationError(f"The {subject} URL has no host.")
        return await self.check_host(
            host, parsed.port or _default_port(parsed), allow_private=allow_private, subject=subject
        )

    async def check_host(
        self,
        host: str,
        port: int,
        *,
        allow_private: bool,
        subject: str,
        stack_exceptions: frozenset[str] = frozenset(),
    ) -> WebhookTarget:
        """Checks a bare host name against the same rules as a URL.
        `stack_exceptions` names stack services that are a legitimate
        target for this caller, such as the dev stack's mail catcher."""
        host = host.strip().rstrip(".").lower()
        if not host:
            raise InvalidWebhookConfigurationError(f"The {subject} has no host.")
        if (host in STACK_HOSTS and host not in stack_exceptions) or host.endswith(".localhost"):
            raise _refused(host, subject)
        addresses = await self._addresses_of(host, port, subject)
        for address in addresses:
            ip = _unmapped(ipaddress.ip_address(address.split("%", 1)[0]))
            if _always_refused_address(ip):
                raise _refused(host, subject)
            if not allow_private and not ip.is_global:
                raise InvalidWebhookConfigurationError(
                    f"The {subject} host {host!r} is on a private network, and private "
                    "targets are switched off in the notification settings."
                )
        return WebhookTarget(host=host, addresses=tuple(addresses))

    async def _addresses_of(self, host: str, port: int, subject: str) -> list[str]:
        try:
            return [str(ipaddress.ip_address(host))]
        except ValueError:
            pass
        try:
            async with asyncio.timeout(self._resolve_timeout):
                addresses = list(await self._resolver(host, port))
        except (OSError, TimeoutError):
            addresses = []
        if not addresses:
            raise InvalidWebhookConfigurationError(f"The {subject} host {host!r} does not resolve.")
        return addresses


def _parse(url: str, subject: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
    except (httpx.InvalidURL, TypeError, ValueError) as exc:
        raise InvalidWebhookConfigurationError(f"The {subject} URL is not a valid URL.") from exc
    if parsed.scheme not in ("http", "https"):
        raise InvalidWebhookConfigurationError(
            f"The {subject} URL must start with http:// or https://."
        )
    if parsed.userinfo:
        raise InvalidWebhookConfigurationError(
            f"The {subject} URL must not carry a user name or password; the signature "
            "authenticates the request."
        )
    return parsed


def _default_port(parsed: httpx.URL) -> int:
    return 443 if parsed.scheme == "https" else 80


def _unmapped(ip: IPv4Address | IPv6Address) -> IPv4Address | IPv6Address:
    if isinstance(ip, IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def _refused(host: str, subject: str) -> InvalidWebhookConfigurationError:
    return InvalidWebhookConfigurationError(
        f"The {subject} host {host!r} points at an address Cuisine never sends requests to: "
        "the local host, a link-local or cloud metadata address, a multicast or reserved "
        "range, or one of the stack's own services."
    )
