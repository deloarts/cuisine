"""
The shopping list purge the background job runs every 15 minutes. On every
continuous list it deletes the items ticked before the recently bought
window. It deletes every normal list nobody used for the configured idle
days, unless a member chose to keep it or it is a household's default list,
and leaves each former member an in-app note. Open screens learn of both
through the lists' live channels after the commit. Running it twice in a
row changes nothing the second time.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.cooking import ShoppingListNote
from src.cookbook.domain.services.shopping_modes import bought_cutoff
from src.cookbook.domain.services.shopping_modes import idle_cutoff
from src.cookbook.ports.outbound.live_publisher import ILivePublisher
from src.cookbook.ports.outbound.live_publisher import shopping_list_channel
from src.cookbook.ports.outbound.repositories.cooking_repositories import (
    IShoppingListNoteRepository,
)
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork


@dataclass(frozen=True)
class PurgeResult:
    bought_removed: int
    lists_deleted: int


class PurgeShoppingLists:
    def __init__(
        self,
        *,
        list_repo: IShoppingListRepository,
        note_repo: IShoppingListNoteRepository,
        settings_repo: ISettingsRepository,
        live: ILivePublisher,
        uow: IUnitOfWork,
    ) -> None:
        self._lists = list_repo
        self._notes = note_repo
        self._settings = settings_repo
        self._live = live
        self._uow = uow

    async def run(self, now: datetime) -> PurgeResult:
        settings = await self._settings.get_shopping()
        cutoff = bought_cutoff(now, settings.bought_window_hours)
        trimmed: list[ShoppingList] = []
        removed = 0
        for shopping_list in await self._lists.continuous_with_checked_before(cutoff):
            count = await self._lists.delete_checked_before(shopping_list.id, cutoff)
            if count:
                removed += count
                trimmed.append(shopping_list)
        deleted: list[ShoppingList] = []
        if settings.idle_list_days > 0:
            for shopping_list in await self._lists.idle_since(
                idle_cutoff(now, settings.idle_list_days)
            ):
                for user_id in sorted({shopping_list.owner_id, *shopping_list.member_ids}):
                    await self._notes.add(
                        ShoppingListNote(
                            user_id=user_id,
                            list_name=shopping_list.name,
                            idle_days=settings.idle_list_days,
                            created=now,
                        )
                    )
                await self._lists.delete(shopping_list)
                deleted.append(shopping_list)
        await self._uow.commit()
        for shopping_list in trimmed:
            await self._publish(shopping_list, "items_changed")
        for shopping_list in deleted:
            await self._publish(shopping_list, "list_deleted")
        return PurgeResult(bought_removed=removed, lists_deleted=len(deleted))

    async def _publish(self, shopping_list: ShoppingList, event: str) -> None:
        # Nobody made this change, so `by` is empty.
        payload: dict[str, Any] = {
            "type": event,
            "list_id": str(shopping_list.public_id),
            "by": None,
        }
        await self._live.publish(shopping_list_channel(str(shopping_list.public_id)), payload)
