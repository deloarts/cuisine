"""
Signed calls to a paired instance for the channel use cases, and the short
categories a failed call is recorded with. The categories are shown on the
peer page; the peer's own text is never stored.
"""

from typing import Any

from src.platform.application.services.peer_targets import private_targets_allowed
from src.platform.domain.entities.peer import Peer
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeerUnreachableError
from src.platform.ports.outbound.peer_client import IPeerClient
from src.platform.ports.outbound.peer_client import PeerReply
from src.platform.ports.outbound.peer_client import PeerRequest
from src.platform.ports.outbound.peer_client import PeerSigning
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository

# The peer could not be reached, timed out or answered no valid HTTP.
UNREACHABLE = "unreachable"
# The target guard or the https rule refused the peer's address.
INVALID_TARGET = "invalid_target"
# The peer answered with a status that is no success.
REFUSED = "refused"
# The peer answered something this instance cannot read.
INVALID_ANSWER = "invalid_answer"
# The registered consumer could not take an item in.
CONSUMER_FAILED = "consumer_failed"


class PeerCallFailed(Exception):
    """A call to a peer that did not succeed, with its category and the
    HTTP status when there was an answer."""

    def __init__(self, category: str, status: int | None = None) -> None:
        super().__init__(category)
        self.category = category
        self.status = status


class PeerCalls:
    def __init__(self, *, client: IPeerClient, settings_repo: ISettingsRepository) -> None:
        self._client = client
        self._settings = settings_repo

    async def send(
        self,
        peer: Peer,
        method: str,
        target: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        max_response_bytes: int | None = None,
    ) -> PeerReply:
        """Sends a signed request and returns any HTTP answer. Raises
        PeerCallFailed when the peer cannot be reached or may not be
        called."""
        try:
            return await self._client.send(
                PeerRequest(
                    base_url=peer.base_url,
                    method=method,
                    target=target,
                    protocol_version=peer.protocol_version,
                    body=body,
                    signing=PeerSigning(
                        sender_instance_id=await self._settings.instance_id(),
                        secret=peer.outbound_secret,
                    ),
                    headers=headers or {},
                    max_response_bytes=max_response_bytes,
                ),
                allow_private=await private_targets_allowed(self._settings),
            )
        except PeerUnreachableError as exc:
            raise PeerCallFailed(UNREACHABLE) from exc
        except InvalidPeerConfigurationError as exc:
            raise PeerCallFailed(INVALID_TARGET) from exc
