"""The peers visibility and "sync all from this peer" between two paired apps
(the `mirrors` fixture of test_peer_mirrors.py, "A" the source and "B" the
receiver): peers recipes reaching a peer that may receive, read as instance
and withdrawn while peering is off, refused while off and on capped
recipes, sent at once to a new pairing, the privacy statement version on
switching peering, and the automatic acceptance with its catalogue defaults,
held updates that never wait, rejections that stay and "accept everything
that waits"."""

from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select

from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.persistence.models.peer_channel_models import (
    PeerChannelEventModel,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.peer import Peer
from tests.integration.conftest import CSRF
from tests.integration.test_peer_mirrors import WEB
from tests.integration.test_peer_mirrors import Mirrors
from tests.integration.test_peer_mirrors import mirrors as mirrors_fixture  # noqa: F401


@pytest.fixture
def mirrors(mirrors_fixture: Mirrors) -> Mirrors:  # noqa: F811
    return mirrors_fixture


async def _switches(client: httpx.AsyncClient, peer: Peer, **values: Any) -> None:
    body = {
        "users_may_share": True,
        "accept_incoming": True,
        "mirror_visibility": "instance",
        "sync_all": False,
        **values,
    }
    changed = await client.put(
        f"{WEB}/admin/peers/{peer.public_id}/switches", headers=CSRF, json=body
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["sync_all"] is body["sync_all"]
    assert "send_all_public" not in changed.json()


async def _peering(client: httpx.AsyncClient, on: bool) -> None:
    current = (await client.get(f"{WEB}/settings/features")).json()
    saved = await client.put(
        f"{WEB}/settings/features", headers=CSRF, json={**current, "peering": on}
    )
    assert saved.status_code == 200, saved.text


async def _published(m: Mirrors, title: str, lines: list[tuple[str, float]], **extra: Any) -> str:
    body = await m.recipe_body(title, lines, **extra)
    created = await m.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert created.status_code == 201, created.text
    published = await m.a.post(f"{WEB}/recipes/{created.json()['id']}/publish", headers=CSRF)
    assert published.status_code == 200, published.text
    return str(created.json()["id"])


async def _last_event(item_id: str) -> str | None:
    async with SessionLocal() as db:
        found: str | None = await db.scalar(
            select(PeerChannelEventModel.type).where(PeerChannelEventModel.item_id == item_id)
        )
    return found


def _body_of(edit: dict[str, Any], **values: Any) -> dict[str, Any]:
    return {
        "original_locale": edit["original_locale"],
        "translations": edit["translations"],
        "base_servings": edit["base_servings"],
        "steps": [
            {
                "translations": s["translations"],
                "ingredients": [
                    {
                        "ingredient_id": i["ingredient_id"],
                        "sub_recipe_id": i["sub_recipe_id"],
                        "amount": i["amount"],
                        "unit_id": i["unit_id"],
                    }
                    for i in s["ingredients"]
                ],
            }
            for s in edit["steps"]
        ],
        **values,
    }


# ── The audience ─────────────────────────────────────────────────────


async def test_a_peers_recipe_goes_to_a_peer_only_while_it_may_receive(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id = await _published(mirrors, "Verbunden", [(kren, 20)], visibility="peers")
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    assert item["source_id"] == source_id
    detail = (await mirrors.a.get(f"{WEB}/recipes/{source_id}")).json()
    assert (detail["visibility"], detail["effective_visibility"]) == ("peers", "peers")

    await _switches(mirrors.a, mirrors.b_on_a, users_may_share=False)
    await mirrors.settle()
    assert await mirrors.incoming() == []

    await _switches(mirrors.a, mirrors.b_on_a, users_may_share=True)
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    await mirrors.accept_creating(item)
    assert await mirrors.mirror_of(source_id) is not None
    # Narrowed to instance: withdrawn.
    edit = (await mirrors.a.get(f"{WEB}/recipes/{source_id}/edit")).json()
    await mirrors.save_a(source_id, _body_of(edit, visibility="instance"))
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None


async def test_peers_reads_as_instance_while_peering_is_off(mirrors: Mirrors) -> None:
    draft = (await mirrors.a.get(f"{WEB}/admin/legal/privacy/draft")).json()["body"]
    assert '"Paired instances"' in draft
    first = await mirrors.a.post(
        f"{WEB}/admin/legal/privacy", headers=CSRF, json={"texts": {"en-GB": draft}}
    )
    assert first.status_code == 201, first.text
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id = await _published(mirrors, "Verbunden", [(kren, 20)], visibility="peers")
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    await mirrors.accept_creating(item)
    assert await _last_event(source_id) == "item.shared"

    await _peering(mirrors.a, False)
    detail = (await mirrors.a.get(f"{WEB}/recipes/{source_id}")).json()
    assert (detail["visibility"], detail["effective_visibility"]) == ("peers", "instance")
    # Withdrawn from the peer (sent once peering is on again).
    assert await _last_event(source_id) == "item.withdrawn"
    versions = (await mirrors.a.get(f"{WEB}/admin/legal/privacy/versions")).json()
    assert versions[0]["version"] == first.json()["version"] + 1
    assert versions[0]["peering_enabled"] is False
    # A stored peers is kept on save; a new one is refused.
    edit = (await mirrors.a.get(f"{WEB}/recipes/{source_id}/edit")).json()
    kept = await mirrors.save_a(source_id, _body_of(edit, visibility="peers"))
    assert kept["visibility"] == "peers"
    body = await mirrors.recipe_body("Neu", [(kren, 10)], visibility="peers")
    refused = await mirrors.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "PeerRecipesNotAllowedError"
    own = await mirrors.a.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "peers"}
    )
    assert own.status_code == 422
    assert own.json()["code"] == "PeerRecipesNotAllowedError"
    privacy = (await mirrors.a.get(f"{WEB}/settings/privacy")).json()
    default = await mirrors.a.put(
        f"{WEB}/settings/privacy",
        headers=CSRF,
        json={**privacy, "default_recipe_visibility": "peers"},
    )
    assert default.status_code == 422
    assert default.json()["code"] == "PeerRecipesNotAllowedError"

    await _peering(mirrors.a, True)
    detail = (await mirrors.a.get(f"{WEB}/recipes/{source_id}")).json()
    assert detail["effective_visibility"] == "peers"
    assert await _last_event(source_id) == "item.shared"
    versions = (await mirrors.a.get(f"{WEB}/admin/legal/privacy/versions")).json()
    assert versions[0]["version"] == first.json()["version"] + 2
    assert versions[0]["peering_enabled"] is True
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is not None
    # Now a peers default is accepted, and new recipes start there.
    own = await mirrors.a.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "peers"}
    )
    assert own.status_code == 200, own.text
    created = await mirrors.a.post(
        f"{WEB}/recipes", headers=CSRF, json=await mirrors.recipe_body("Standard", [(kren, 5)])
    )
    assert created.json()["visibility"] == "peers"


async def test_a_copy_of_a_mirror_can_never_go_to_peers(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    copy = await mirrors.b.post(f"{WEB}/recipes/{mirror_id}/copy", headers=CSRF)
    assert copy.status_code == 201, copy.text
    fork_id = copy.json()["id"]
    edit = (await mirrors.b.get(f"{WEB}/recipes/{fork_id}/edit")).json()
    assert edit["peer_capped"] is True
    for visibility in ("peers", "public"):
        refused = await mirrors.b.put(
            f"{WEB}/recipes/{fork_id}", headers=CSRF, json=_body_of(edit, visibility=visibility)
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["code"] == "PeerShareNotAllowedError"


async def test_a_new_pairing_receives_every_peers_and_public_recipe(mirrors: Mirrors) -> None:
    revoked = await mirrors.a.post(
        f"{WEB}/admin/peers/{mirrors.b_on_a.public_id}/revoke", headers=CSRF
    )
    assert revoked.status_code == 200, revoked.text
    privacy = (await mirrors.a.get(f"{WEB}/settings/privacy")).json()
    await mirrors.a.put(
        f"{WEB}/settings/privacy", headers=CSRF, json={**privacy, "allow_public_recipes": True}
    )
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    peers_id = await _published(mirrors, "Verbunden", [(kren, 20)], visibility="peers")
    public_id = await _published(mirrors, "Öffentlich", [(kren, 20)], visibility="public")
    await _published(mirrors, "Daheim", [(kren, 20)], visibility="instance")

    link = (await mirrors.a.post(f"{WEB}/admin/peers/invitations", headers=CSRF)).json()["link"]
    accepted = await mirrors.b.post(
        f"{WEB}/admin/peers/accept", headers=CSRF, json={"invitation_url": link}
    )
    assert accepted.status_code == 200, accepted.text
    async with SessionLocal() as db:
        (b_on_a,) = await Platform(db).peers.list_active()
    assert b_on_a.id == mirrors.b_on_a.id
    # Pairing again keeps the stored switches (the fixture turned sync all
    # off); only a first pairing starts with it on.
    assert b_on_a.sync_all is False
    await mirrors.settle()
    waiting = {i["source_id"] for i in await mirrors.incoming()}
    assert waiting == {peers_id, public_id}


# ── Sync all from this peer ──────────────────────────────────────────


async def _source_unit(m: Mirrors, code: str) -> str:
    created = await m.a.post(
        f"{WEB}/units",
        headers=CSRF,
        json={"code": code, "kind": "count", "translations": {"de-AT": {"name": code}}},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def test_sync_all_takes_recipes_in_at_once_with_automatic_decisions(
    mirrors: Mirrors,
) -> None:
    # B knows "Kren" by name and the unit "kuebel" by code; A's "Zirbe" and
    # its unit "zipfel" are unknown on B, and so is A's own tag.
    local_kren = await mirrors.ingredient(mirrors.b, "Kren")
    created = await mirrors.b.post(
        f"{WEB}/units",
        headers=CSRF,
        json={"code": "kuebel", "kind": "count", "translations": {"de-AT": {"name": "Kübel"}}},
    )
    assert created.status_code == 201, created.text
    local_bund = str(created.json()["id"])
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    category = next(
        c for c in (await mirrors.a.get(f"{WEB}/ingredient-categories")).json() if c["seeded"]
    )
    zirbe_created = await mirrors.a.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": "Zirbe", "plural_name": "Zirbe"}},
            "nutrition": {"kcal": 100},
            "category_id": category["id"],
        },
    )
    assert zirbe_created.status_code == 201, zirbe_created.text
    zirbe = str(zirbe_created.json()["id"])
    bund = await _source_unit(mirrors, "kuebel")
    prise = await _source_unit(mirrors, "zipfel")
    tag = await mirrors.a.post(
        f"{WEB}/tags",
        headers=CSRF,
        json={"kind": "meal", "translations": {"de-AT": {"name": "Hüttenjause"}}},
    )
    assert tag.status_code == 201, tag.text
    await _switches(mirrors.b, mirrors.a_on_b, sync_all=True)

    body = await mirrors.recipe_body(
        "Zirbenkren",
        [],
        visibility="shared",
        shared_peer_ids=[str(mirrors.b_on_a.public_id)],
        tag_ids=[tag.json()["id"]],
    )
    body["steps"][0]["ingredients"] = [
        {"ingredient_id": kren, "amount": 1, "unit_id": bund},
        {"ingredient_id": zirbe, "amount": 2, "unit_id": prise},
    ]
    created = await mirrors.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert created.status_code == 201, created.text
    source_id = created.json()["id"]
    await mirrors.a.post(f"{WEB}/recipes/{source_id}/publish", headers=CSRF)
    await mirrors.settle()

    assert await mirrors.incoming() == []
    mirror = await mirrors.mirror_of(source_id)
    assert mirror is not None
    assert mirror["tags"] == []
    lines = {line["name"]: line for line in mirror["steps"][0]["ingredients"]}
    assert lines["Kren"]["ingredient_id"] == local_kren
    assert lines["Kren"]["unit"]["id"] == local_bund
    assert lines["Zirbe"]["unit"] is None
    created_zirbe = (await mirrors.b.get(f"{WEB}/ingredients", params={"search": "Zirbe"})).json()
    (zirbe_here,) = created_zirbe["items"]
    assert zirbe_here["status"] == "draft"
    same = next(
        c
        for c in (await mirrors.b.get(f"{WEB}/ingredient-categories")).json()
        if c["name"] == category["name"]
    )
    detail = (await mirrors.b.get(f"{WEB}/ingredients/{zirbe_here['id']}")).json()
    assert detail["category"]["id"] == same["id"]
    mappings = (
        await mirrors.b.get(f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/mappings")
    ).json()
    decided = {(m["kind"], m["name"]): (m["action"], m["created_here"]) for m in mappings}
    assert decided[("ingredient", "Kren")] == ("map", False)
    assert decided[("ingredient", "Zirbe")] == ("map", True)
    assert decided[("unit", "kuebel")][0] == "map"
    assert decided[("unit", "zipfel")][0] == "none"
    assert decided[("tag", "Hüttenjause")][0] == "none"


async def test_sync_all_applies_updates_with_new_entries_and_keeps_saved_mappings(
    mirrors: Mirrors,
) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    # The administrator keeps Kren as plain text; that decision stays.
    (entry,) = item["entries"]
    accepted = await mirrors.accept(
        item["id"], [{"kind": "ingredient", "source_id": entry["source_id"], "action": "plain"}]
    )
    assert accepted.status_code == 200, accepted.text
    await _switches(mirrors.b, mirrors.a_on_b, sync_all=True)

    zirbe = await mirrors.ingredient(mirrors.a, "Zirbe")
    edit = (await mirrors.a.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    body = _body_of(edit, visibility="shared", shared_peer_ids=[str(mirrors.b_on_a.public_id)])
    unit = body["steps"][0]["ingredients"][0]["unit_id"]
    body["steps"][0]["ingredients"].append({"ingredient_id": zirbe, "amount": 5, "unit_id": unit})
    await mirrors.save_a(recipe["id"], body)
    await mirrors.settle()

    assert await mirrors.incoming() == []
    mirror = await mirrors.mirror_of(recipe["id"])
    assert mirror is not None
    assert [i["name"] for i in mirror["steps"][0]["ingredients"]] == ["Zirbe"]
    assert [p["name"] for p in mirror["mirror_details"]["plain_lines"]] == ["Kren"]


async def test_a_rejected_recipe_stays_rejected_under_sync_all(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    rejected = await mirrors.b.post(
        f"{WEB}/admin/incoming-recipes/{item['id']}/reject", headers=CSRF
    )
    assert rejected.status_code == 200, rejected.text
    await _switches(mirrors.b, mirrors.a_on_b, sync_all=True)

    edit = (await mirrors.a.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    body = _body_of(edit, visibility="shared", shared_peer_ids=[str(mirrors.b_on_a.public_id)])
    body["translations"]["de-AT"]["title"] = "Krenfleisch neu"
    await mirrors.save_a(recipe["id"], body)
    await mirrors.settle()
    assert await mirrors.mirror_of(recipe["id"]) is None
    (still,) = await mirrors.incoming("rejected")
    assert still["title"] == "Krenfleisch neu"
    accepted = await mirrors.b.post(
        f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/incoming-recipes/accept", headers=CSRF
    )
    assert accepted.json() == {"accepted": 0}
    assert await mirrors.mirror_of(recipe["id"]) is None


async def test_accepting_everything_that_waits(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    waiting = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    unwanted = await mirrors.shared_recipe("Krensuppe", [(kren, 10)])
    await mirrors.settle()
    items = {i["source_id"]: i for i in await mirrors.incoming()}
    rejected = await mirrors.b.post(
        f"{WEB}/admin/incoming-recipes/{items[unwanted['id']]['id']}/reject", headers=CSRF
    )
    assert rejected.status_code == 200, rejected.text
    # Switching sync all on accepts nothing by itself.
    await _switches(mirrors.b, mirrors.a_on_b, sync_all=True)
    assert len(await mirrors.incoming()) == 1

    url = f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/incoming-recipes/accept"
    accepted = await mirrors.b.post(url, headers=CSRF)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json() == {"accepted": 1}
    assert await mirrors.incoming() == []
    assert len(await mirrors.incoming("rejected")) == 1
    mirror = await mirrors.mirror_of(waiting["id"])
    assert mirror is not None
    assert [i["name"] for i in mirror["ingredients"]] == ["Kren"]
    assert await mirrors.mirror_of(unwanted["id"]) is None
    unknown = await mirrors.b.post(
        f"{WEB}/admin/peers/{UUID(int=1)}/incoming-recipes/accept", headers=CSRF
    )
    assert unknown.status_code == 404
