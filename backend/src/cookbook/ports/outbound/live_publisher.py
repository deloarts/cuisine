"""Pushing a change to every open view of a shared record, such as a
shopping list on several phones."""

from collections.abc import AsyncIterator
from typing import Any
from typing import Protocol


class ILivePublisher(Protocol):
    async def publish(self, channel: str, event: dict[str, Any]) -> None: ...


class ILiveSubscriber(Protocol):
    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]: ...


class ILiveChannel(ILivePublisher, ILiveSubscriber, Protocol):
    """Both sides of the live channel, as one adapter provides them."""


def shopping_list_channel(list_public_id: str) -> str:
    return f"cuisine:shopping-list:{list_public_id}"
