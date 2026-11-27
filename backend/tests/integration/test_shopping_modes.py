"""Shopping list modes: the recently bought window of continuous lists, the
idle deletion of normal lists and its notes, keep, the household list, mode
switches, the purge's live events and the admin settings."""

from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import httpx
from sqlalchemy import update

from src.bootstrap.shopping_jobs import run_shopping_purge_once
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import shopping_purge
from src.cookbook.adapters.outbound.external.live_updates import InMemoryLivePublisher
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.application.use_cases.planning.shopping_purge import PurgeResult
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB

SETTINGS = f"{WEB}/settings/shopping"


async def _purge(live: InMemoryLivePublisher, at: datetime) -> PurgeResult:
    async with SessionLocal() as db:
        return await shopping_purge(Cookbook(Platform(db)), live).run(at)


async def _new_list(client: httpx.AsyncClient, name: str, **extra: Any) -> dict[str, Any]:
    response = await client.post(
        f"{WEB}/shopping-lists", headers=CSRF, json={"name": name, **extra}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _add(client: httpx.AsyncClient, list_id: str, text: str) -> dict[str, Any]:
    response = await client.post(
        f"{WEB}/shopping-lists/{list_id}/items", headers=CSRF, json={"text": text}
    )
    assert response.status_code == 200, response.text
    return next(i for i in response.json()["items"] if i["text"] == text)


async def _tick(client: httpx.AsyncClient, list_id: str, item_id: str) -> dict[str, Any]:
    response = await client.patch(
        f"{WEB}/shopping-lists/{list_id}/items/{item_id}", headers=CSRF, json={"checked": True}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _backdate_ticks(hours: float) -> None:
    async with SessionLocal() as db:
        await db.execute(
            update(ShoppingItemModel)
            .where(ShoppingItemModel.checked.is_(True))
            .values(checked_at=now_utc() - timedelta(hours=hours))
        )
        await db.commit()


async def test_new_lists_are_normal_and_the_household_list_continuous(
    cook: httpx.AsyncClient,
) -> None:
    created = await _new_list(cook, "Markt")
    assert created["mode"] == "normal"
    assert created["keep"] is False
    assert created["bought_window_hours"] == 12
    assert created["deletes_on"] == (now_utc() + timedelta(days=30)).date().isoformat()

    home = (await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Zuhause"})).json()
    household_list = (await cook.get(f"{WEB}/shopping-lists/{home['shopping_list_id']}")).json()
    assert household_list["mode"] == "continuous"
    assert household_list["deletes_on"] is None
    # Even switched to normal it never deletes itself.
    normal = await cook.put(
        f"{WEB}/shopping-lists/{home['shopping_list_id']}", headers=CSRF, json={"mode": "normal"}
    )
    assert normal.json()["mode"] == "normal"
    assert normal.json()["deletes_on"] is None


async def test_activity_moves_the_deletion_day(cook: httpx.AsyncClient) -> None:
    created = await _new_list(cook, "Markt")
    item = await _add(cook, created["id"], "Brot")
    ticked = await _tick(cook, created["id"], item["id"])
    assert ticked["last_activity_at"] > created["last_activity_at"]
    kept = await cook.put(
        f"{WEB}/shopping-lists/{created['id']}", headers=CSRF, json={"keep": True}
    )
    assert kept.json()["keep"] is True
    assert kept.json()["deletes_on"] is None
    summary = (await cook.get(f"{WEB}/shopping-lists")).json()[0]
    assert summary["mode"] == "normal" and summary["keep"] is True


async def test_purge_forgets_purchases_after_the_window_and_publishes(
    cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    created = await _new_list(cook, "Wocheneinkauf")
    list_id = created["id"]
    switched = await cook.put(
        f"{WEB}/shopping-lists/{list_id}", headers=CSRF, json={"mode": "continuous"}
    )
    assert switched.json()["mode"] == "continuous"
    assert switched.json()["deletes_on"] is None
    bread = await _add(cook, list_id, "Brot")
    await _add(cook, list_id, "Milch")
    ticked = await _tick(cook, list_id, bread["id"])
    recent = next(i for i in ticked["items"] if i["text"] == "Brot")
    assert recent["checked"] is True and recent["checked_at"] is not None

    live.published.clear()
    within = await _purge(live, now_utc() + timedelta(hours=11))
    assert within == PurgeResult(bought_removed=0, lists_deleted=0)
    assert live.published == []

    after = await _purge(live, now_utc() + timedelta(hours=13))
    assert after.bought_removed == 1
    left = (await cook.get(f"{WEB}/shopping-lists/{list_id}")).json()["items"]
    assert [i["text"] for i in left] == ["Milch"]
    assert live.published == [
        (
            f"cuisine:shopping-list:{list_id}",
            {"type": "items_changed", "list_id": list_id, "by": None},
        )
    ]


async def test_purge_leaves_purchases_on_normal_lists(
    cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    created = await _new_list(cook, "Markt")
    bread = await _add(cook, created["id"], "Brot")
    await _tick(cook, created["id"], bread["id"])
    assert (await _purge(live, now_utc() + timedelta(days=2))).bought_removed == 0


async def test_idle_normal_lists_delete_themselves_unless_kept(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    live: InMemoryLivePublisher,
) -> None:
    friend = await make_user("friend")
    idle = await _new_list(cook, "Grillfest", member_ids=[friend["id"]])
    kept = await _new_list(cook, "Vorrat")
    await cook.put(f"{WEB}/shopping-lists/{kept['id']}", headers=CSRF, json={"keep": True})
    continuous = await _new_list(cook, "Immer")
    await cook.put(
        f"{WEB}/shopping-lists/{continuous['id']}", headers=CSRF, json={"mode": "continuous"}
    )
    home = (await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Zuhause"})).json()

    assert (await _purge(live, now_utc() + timedelta(days=29))).lists_deleted == 0
    live.published.clear()
    result = await _purge(live, now_utc() + timedelta(days=31))
    assert result.lists_deleted == 1
    remaining = {s["id"] for s in (await cook.get(f"{WEB}/shopping-lists")).json()}
    assert remaining == {kept["id"], continuous["id"], home["shopping_list_id"]}
    assert live.published == [
        (
            f"cuisine:shopping-list:{idle['id']}",
            {"type": "list_deleted", "list_id": idle["id"], "by": None},
        )
    ]

    notes = (await cook.get(f"{WEB}/shopping-lists/notes")).json()
    assert [(n["list_name"], n["idle_days"]) for n in notes] == [("Grillfest", 30)]
    await login(client, "friend@example.com", "cook-password-1")
    friend_notes = (await client.get(f"{WEB}/shopping-lists/notes")).json()
    assert [n["list_name"] for n in friend_notes] == ["Grillfest"]
    # A note is the reader's own: another user cannot dismiss it.
    refused = await client.delete(f"{WEB}/shopping-lists/notes/{notes[0]['id']}", headers=CSRF)
    assert refused.status_code == 404
    dismissed = await cook.delete(f"{WEB}/shopping-lists/notes/{notes[0]['id']}", headers=CSRF)
    assert dismissed.status_code == 204
    assert (await cook.get(f"{WEB}/shopping-lists/notes")).json() == []


async def test_zero_idle_days_turns_self_deletion_off(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    saved = await admin.put(
        SETTINGS, headers=CSRF, json={"bought_window_hours": 12, "idle_list_days": 0}
    )
    assert saved.status_code == 200, saved.text
    created = await _new_list(cook, "Markt")
    assert created["deletes_on"] is None
    assert (await _purge(live, now_utc() + timedelta(days=400))).lists_deleted == 0


async def test_switching_to_continuous_drops_old_purchases(
    cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    created = await _new_list(cook, "Markt")
    list_id = created["id"]
    old = await _add(cook, list_id, "Brot")
    await _tick(cook, list_id, old["id"])
    await _backdate_ticks(13)
    fresh = await _add(cook, list_id, "Milch")
    await _tick(cook, list_id, fresh["id"])
    await _add(cook, list_id, "Käse")

    live.published.clear()
    switched = (
        await cook.put(f"{WEB}/shopping-lists/{list_id}", headers=CSRF, json={"mode": "continuous"})
    ).json()
    assert sorted(i["text"] for i in switched["items"]) == ["Käse", "Milch"]
    assert {e["type"] for _, e in live.published} == {"list_changed", "items_changed"}
    # Back to normal keeps every item.
    back = (
        await cook.put(f"{WEB}/shopping-lists/{list_id}", headers=CSRF, json={"mode": "normal"})
    ).json()
    assert len(back["items"]) == 2
    assert date.fromisoformat(back["deletes_on"]) == (now_utc() + timedelta(days=30)).date()


async def test_the_background_job_runs_once_per_interval(
    cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    created = await _new_list(cook, "Markt")
    await cook.put(
        f"{WEB}/shopping-lists/{created['id']}", headers=CSRF, json={"mode": "continuous"}
    )
    bread = await _add(cook, created["id"], "Brot")
    await _tick(cook, created["id"], bread["id"])
    await _backdate_ticks(13)
    assert await run_shopping_purge_once(force=True, live=live) is True
    assert await run_shopping_purge_once(live=live) is False
    assert (await cook.get(f"{WEB}/shopping-lists/{created['id']}")).json()["items"] == []


async def test_shopping_settings_validation(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    assert (await admin.get(SETTINGS)).json() == {"bought_window_hours": 12, "idle_list_days": 30}
    for body in (
        {"bought_window_hours": 0, "idle_list_days": 30},
        {"bought_window_hours": 721, "idle_list_days": 30},
        {"bought_window_hours": 12, "idle_list_days": -1},
        {"bought_window_hours": 12, "idle_list_days": 3651},
    ):
        assert (await admin.put(SETTINGS, headers=CSRF, json=body)).status_code == 422, body
    saved = await admin.put(
        SETTINGS, headers=CSRF, json={"bought_window_hours": 48, "idle_list_days": 14}
    )
    assert saved.json() == {"bought_window_hours": 48, "idle_list_days": 14}
    created = await _new_list(cook, "Markt")
    assert created["bought_window_hours"] == 48
    assert created["deletes_on"] == (now_utc() + timedelta(days=14)).date().isoformat()
    refused = await cook.put(
        SETTINGS, headers=CSRF, json={"bought_window_hours": 1, "idle_list_days": 1}
    )
    assert refused.status_code == 403


async def test_first_job_state_writes_race_safely() -> None:
    """The nightly jobs and the purge both create the job state row on a
    fresh database; the one that loses the insert updates the other's row."""
    async with SessionLocal() as loser, SessionLocal() as winner:
        repo = SqlAlchemySettingsRepository(loser)
        real_get = loser.get
        calls = 0

        async def stale_get(*args: Any, **kwargs: Any) -> Any:
            # The loser looked before the winner committed its insert.
            nonlocal calls
            calls += 1
            if calls == 1:
                await SqlAlchemySettingsRepository(winner).save_job_state({"nightly_at": "x"})
                await winner.commit()
                return None
            return await real_get(*args, **kwargs)

        with patch.object(loser, "get", stale_get):
            await repo.save_job_state({"shopping_purge_at": "y"})
        await loser.commit()
    async with SessionLocal() as db:
        assert await SqlAlchemySettingsRepository(db).get_job_state() == {"shopping_purge_at": "y"}
