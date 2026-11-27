"""
Sends peering requests with httpx. Every request names the protocol version
in `Cuisine-Peering-Version`; every request but the handshake is signed with
the secret the peer issued (`peering_rules.sign_request`) and names this
instance in `Cuisine-Peer`.

The same safeguards as webhook deliveries apply: the target guard checks
the URL and every address its host resolves to, with the private network
switch of the notification settings, and the request goes to the first
checked address with the Host header and TLS server name kept as the
hostname, so a second DNS answer cannot redirect it. Outside debug mode only
https is accepted. Redirects are not followed, the request times out, and
an answer larger than `MAX_RESPONSE_BYTES` is dropped.
"""

import json
import ssl
import uuid
from typing import Any

import httpx

from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.const import API_PEERING
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.exceptions import PeerUnreachableError
from src.platform.domain.services.peering_rules import sign_request
from src.platform.domain.value_objects.peering import MESSAGE_ID_HEADER
from src.platform.domain.value_objects.peering import PEER_HEADER
from src.platform.domain.value_objects.peering import SIGNATURE_HEADER
from src.platform.domain.value_objects.peering import TIMESTAMP_HEADER
from src.platform.domain.value_objects.peering import VERSION_HEADER
from src.platform.ports.outbound.peer_client import PeerReply
from src.platform.ports.outbound.peer_client import PeerRequest
from src.shared_kernel.domain.services.clock import now_utc

TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BYTES = 1024 * 1024


class HttpxPeerClient:
    def __init__(
        self,
        guard: WebhookTargetGuard,
        *,
        require_https: bool,
        timeout_seconds: float = TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """`transport` replaces the network, for tests that route the
        request into another app in the same process."""
        self._guard = guard
        self._require_https = require_https
        self._timeout = timeout_seconds
        self._max_bytes = max_response_bytes
        self._transport = transport

    async def send(self, request: PeerRequest, *, allow_private: bool) -> PeerReply:
        url = f"{request.base_url.rstrip('/')}{API_PEERING}{request.target}"
        original = httpx.URL(url)
        if self._require_https and original.scheme != "https":
            raise InvalidPeerConfigurationError(
                "Peering needs https; plain http is accepted only in debug mode."
            )
        try:
            target = await self._guard.resolve(url, allow_private=allow_private, subject="peer")
        except InvalidWebhookConfigurationError as exc:
            raise InvalidPeerConfigurationError(str(exc)) from exc
        body = (
            b""
            if request.body is None
            else json.dumps(request.body, separators=(",", ":"), ensure_ascii=False).encode()
        )
        headers = {
            "Accept": "application/json",
            "User-Agent": "Cuisine-Peering",
            "Host": original.netloc.decode("ascii"),
            VERSION_HEADER: str(request.protocol_version),
        }
        if request.body is not None:
            headers["Content-Type"] = "application/json"
        for name, value in request.headers.items():
            headers.setdefault(name, value)
        if request.signing is not None:
            message_id = str(uuid.uuid4())
            timestamp = int(now_utc().timestamp())
            headers[PEER_HEADER] = str(request.signing.sender_instance_id)
            headers[MESSAGE_ID_HEADER] = message_id
            headers[TIMESTAMP_HEADER] = str(timestamp)
            headers[SIGNATURE_HEADER] = sign_request(
                request.signing.secret,
                message_id=message_id,
                timestamp=timestamp,
                method=request.method,
                target=request.target,
                body=body,
            )
        pinned = original.copy_with(host=target.addresses[0])
        try:
            async with (
                httpx.AsyncClient(
                    timeout=self._timeout, follow_redirects=False, transport=self._transport
                ) as client,
                client.stream(
                    request.method.upper(),
                    pinned,
                    content=body or None,
                    headers=headers,
                    extensions={"sni_hostname": target.host},
                ) as response,
            ):
                raw = await self._read_capped(
                    response, request.max_response_bytes or self._max_bytes
                )
                status = response.status_code
                version = response.headers.get(VERSION_HEADER)
                media_type = response.headers.get("Content-Type")
                etag = response.headers.get("ETag")
        except httpx.HTTPError as exc:
            raise PeerUnreachableError(_describe(exc)) from exc
        return PeerReply(
            status=status,
            data=_json_object(raw),
            protocol_version=version,
            body=raw,
            media_type=media_type,
            etag=etag,
        )

    async def _read_capped(self, response: httpx.Response, limit: int) -> bytes:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > limit:
                raise PeerUnreachableError("The other instance answered with too much data.")
            chunks.append(chunk)
        return b"".join(chunks)


def _json_object(raw: bytes) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _describe(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "The other instance did not answer in time."
    if isinstance(exc, httpx.ConnectError):
        cause: BaseException | None = exc
        seen: set[int] = set()
        while cause is not None and id(cause) not in seen:
            if isinstance(cause, ssl.SSLError):
                return "The TLS handshake or certificate check with the other instance failed."
            seen.add(id(cause))
            cause = cause.__cause__ or cause.__context__
        return "The other instance could not be reached."
    if isinstance(exc, httpx.RemoteProtocolError | httpx.LocalProtocolError):
        return "The other instance did not answer with valid HTTP."
    return "The request to the other instance failed."
