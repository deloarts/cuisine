"""/api/v1/web/shopping-lists: shared shopping lists, their items, and the
live stream that tells every open screen of a list to refetch."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from sse_starlette.sse import EventSourceResponse

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import get_live
from src.cookbook.adapters.inbound.api.deps import get_manage_shopping_lists
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import AddedResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import AddRecipeToListRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import RemovedResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingItemRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingItemUpdate
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListNoteResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListSummaryResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListUpdate
from src.cookbook.application.use_cases.planning.shopping_lists import ItemCommand
from src.cookbook.application.use_cases.planning.shopping_lists import ItemUpdate
from src.cookbook.application.use_cases.planning.shopping_lists import ManageShoppingLists
from src.cookbook.ports.outbound.live_publisher import ILiveSubscriber
from src.cookbook.ports.outbound.live_publisher import shopping_list_channel
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.domain.entities.user import User

router = APIRouter(prefix="/shopping-lists", tags=["shopping"])

_PING_SECONDS = 15
# A stream ends after this long and the browser reconnects, which checks the
# session and the list membership again.
_MAX_STREAM_SECONDS = 30 * 60


@router.get("", response_model=list[ShoppingListSummaryResponse])
async def list_shopping_lists(
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> list[ShoppingListSummaryResponse]:
    """The lists the viewer owns or was given."""
    lists, counts = await use_case.lists(user)
    return [await presenter.shopping_summary(s, counts.get(s.id, (0, 0))) for s in lists]


@router.post("", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def create_shopping_list(
    body: ShoppingListRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    created = await use_case.create(user, body.name, [str(m) for m in body.member_ids])
    return await presenter.shopping_list(await use_case.view(user, str(created.public_id)))


@router.get("/notes", response_model=list[ShoppingListNoteResponse])
async def list_shopping_list_notes(
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> list[ShoppingListNoteResponse]:
    """The viewer's notes about unused lists that deleted themselves, newest first."""
    return presenter.shopping_notes(await use_case.notes(user))


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_shopping_list_note(
    note_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> None:
    await use_case.dismiss_note(user, note_id)


@router.get("/{list_id}", response_model=ShoppingListResponse)
async def read_shopping_list(
    list_id: str,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    return await presenter.shopping_list(await use_case.view(user, list_id))


@router.put("/{list_id}", response_model=ShoppingListResponse)
async def update_shopping_list(
    list_id: str,
    body: ShoppingListUpdate,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    """Renames the list and switches its mode or keep flag; the owner also
    changes who it is shared with. Switching to continuous deletes the items
    ticked before the recently bought window."""
    await use_case.update(
        user,
        list_id,
        name=body.name,
        member_ids=[str(m) for m in body.member_ids] if body.member_ids is not None else None,
        mode=body.mode,
        keep=body.keep,
    )
    return await presenter.shopping_list(await use_case.view(user, list_id))


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_list(
    list_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> None:
    await use_case.delete(user, list_id)


@router.post("/{list_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_shopping_list(
    list_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> None:
    await use_case.leave(user, list_id)


@router.post("/{list_id}/items", response_model=ShoppingListResponse)
async def add_shopping_item(
    list_id: str,
    body: ShoppingItemRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    """Adds an item; an amount of an ingredient joins an open item of the
    same ingredient and unit. Answers with the whole list."""
    await use_case.add_item(
        user,
        list_id,
        ItemCommand(
            ingredient_id=str(body.ingredient_id) if body.ingredient_id else None,
            text=body.text,
            amount=body.amount,
            unit_id=str(body.unit_id) if body.unit_id else None,
        ),
    )
    return await presenter.shopping_list(await use_case.view(user, list_id))


@router.patch("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
async def update_shopping_item(
    list_id: str,
    item_id: str,
    body: ShoppingItemUpdate,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    sent = body.model_fields_set
    await use_case.update_item(
        user,
        list_id,
        item_id,
        ItemUpdate(
            checked=body.checked,
            text=body.text,
            amount=body.amount,
            amount_set="amount" in sent,
            unit_id=str(body.unit_id) if body.unit_id else None,
            unit_set="unit_id" in sent,
        ),
    )
    return await presenter.shopping_list(await use_case.view(user, list_id))


@router.delete("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
async def delete_shopping_item(
    list_id: str,
    item_id: str,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ShoppingListResponse:
    await use_case.delete_item(user, list_id, item_id)
    return await presenter.shopping_list(await use_case.view(user, list_id))


@router.post("/{list_id}/clear-checked", response_model=RemovedResponse)
async def clear_checked_items(
    list_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> RemovedResponse:
    return RemovedResponse(removed=await use_case.clear_checked(user, list_id))


@router.post("/{list_id}/recipes", response_model=AddedResponse)
async def add_recipe_to_list(
    list_id: str,
    body: AddRecipeToListRequest,
    user: User = Depends(get_current_user),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> AddedResponse:
    """Adds a recipe's ingredients for `servings` (its own by default)."""
    added = await use_case.add_recipe(
        user,
        list_id,
        str(body.recipe_id),
        body.servings,
        [str(s) for s in body.bought_sub_recipe_ids],
    )
    return AddedResponse(added=added)


@router.get("/{list_id}/events", response_class=EventSourceResponse)
async def shopping_list_events(
    list_id: str,
    user: User = Depends(get_current_user),
    p: Platform = Depends(get_platform),
    use_case: ManageShoppingLists = Depends(get_manage_shopping_lists),
    live: ILiveSubscriber = Depends(get_live),
) -> EventSourceResponse:
    """Server-sent events of one list: `ready` once connected, then
    `change` whenever someone changes the list. A client refetches the list
    on every change and after every reconnect."""
    shopping_list = await use_case.accessible(user, list_id)
    channel = shopping_list_channel(str(shopping_list.public_id))
    # The stream may stay open for many minutes; it must not hold one of
    # the pool's connections while it waits.
    await p.db.close()
    return EventSourceResponse(_frames(live, channel), ping=_PING_SECONDS, sep="\n")


async def _frames(live: ILiveSubscriber, channel: str) -> AsyncIterator[dict[str, Any]]:
    yield {"event": "ready", "data": "{}"}
    deadline = time.monotonic() + _MAX_STREAM_SECONDS
    events = live.subscribe(channel)
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                event = await asyncio.wait_for(anext(events), timeout=remaining)
            except (TimeoutError, StopAsyncIteration):
                return
            yield {"event": "change", "data": json.dumps(event)}
    finally:
        await events.aclose()  # type: ignore[attr-defined]
