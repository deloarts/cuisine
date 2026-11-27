"""Sharing recipes with a paired instance and mirroring them: share targets,
public recipes going to every peer, the accept queue with catalogue decisions, the
per-peer mapping and its correction, held updates, the allergen and marker
union, withdrawals, revoke, read-only mirrors, variations, forks and
sub-recipes.

Every test runs two complete apps paired through their admin endpoints, as
in test_peer_channels.py: "A" on the test database is the source, signed in
as the system user, and "B" on a second SQLite file receives, its requests
made as B's system user unless a test switches the user. Both carry the
reference units, tags and categories, so units match by seed key, while
every ingredient is created by the test. The channel worker runs by hand
(`settle`)."""

import io
import json
import tempfile
import uuid
import zipfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bootstrap import cookbook_seed
from src.bootstrap import seed
from src.bootstrap.models import Base
from src.bootstrap.peer_channel_worker import run_peer_channels_once
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerCatalogueMappingModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import RecipeMirrorModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.platform.adapters.inbound.api import auth_deps
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerChannelModel
from src.platform.adapters.outbound.persistence.models.peer_models import PeerModel
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.session import build_engine
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.services.privacy_draft import PrivacyFacts
from src.platform.domain.services.privacy_draft import privacy_draft
from src.platform.infrastructure.config.settings import DatabaseSettings
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import login
from tests.integration.conftest import system_user
from tests.integration.test_mcp import _token as mcp_token
from tests.integration.test_mcp import call as mcp_call
from tests.integration.test_peer_channels import Link
from tests.integration.test_peering import A_URL
from tests.integration.test_peering import B_URL
from tests.integration.test_peering import GUARD
from tests.integration.test_peering import build_app

WEB = "/api/v1/web"


async def _privacy(sessions: async_sessionmaker[AsyncSession], **values: Any) -> None:
    async with sessions() as db:
        await SqlAlchemySettingsRepository(db).save_privacy(
            PrivacySettings(
                default_recipe_visibility="instance", users_may_change_visibility=True, **values
            )
        )
        await db.commit()


@dataclass
class Mirrors:
    a: httpx.AsyncClient
    b: httpx.AsyncClient
    app_a: Any
    app_b: Any
    sessions_b: async_sessionmaker[AsyncSession]
    to_a: Link
    to_b: Link
    b_on_a: Peer
    a_on_b: Peer
    admin_b: User

    async def settle(self) -> None:
        for _ in range(4):
            for side in ("a", "b"):
                await run_peer_channels_once(
                    sessions=SessionLocal if side == "a" else self.sessions_b,
                    client=(self.to_b if side == "a" else self.to_a).client(),
                    base_url=A_URL if side == "a" else B_URL,
                    guard=GUARD,
                )

    async def catch_up(self) -> None:
        """Makes B's catch-up due, as the timer would."""
        async with self.sessions_b() as db:
            await db.execute(
                update(PeerChannelModel)
                .where(PeerChannelModel.peer_id == self.a_on_b.id)
                .values(catch_up_due_at=now_utc())
            )
            await db.commit()

    def as_user_b(self, user: User) -> None:
        self.app_b.dependency_overrides[auth_deps.get_current_user] = lambda: user

    async def b_user(self, name: str) -> User:
        created = await self.b.post(
            f"{WEB}/users",
            headers=CSRF,
            json={
                "full_name": name.title(),
                "email": f"{name}@example.com",
                "password": "cook-password-1",
                "permissions": ["write:recipes"],
            },
        )
        assert created.status_code == 201, created.text
        async with self.sessions_b() as db:
            found = await SqlAlchemyUserRepository(db).get_by_email(f"{name}@example.com")
        assert found is not None
        return found

    # ── Source side ──────────────────────────────────────────────────

    async def unit(self, client: httpx.AsyncClient, code: str = "g") -> str:
        units = (await client.get(f"{WEB}/units")).json()
        return str(next(u["id"] for u in units if u["code"] == code))

    async def ingredient(
        self,
        client: httpx.AsyncClient,
        name: str,
        *,
        allergens: list[str] | None = None,
        markers: list[str] | None = None,
    ) -> str:
        created = await client.post(
            f"{WEB}/ingredients",
            headers=CSRF,
            json={
                "original_locale": "de-AT",
                "translations": {"de-AT": {"name": name, "plural_name": name}},
                "nutrition": {"kcal": 100},
                "allergens": allergens or [],
                "diet_markers": markers or [],
            },
        )
        assert created.status_code == 201, created.text
        return str(created.json()["id"])

    async def recipe_body(
        self, title: str, lines: list[tuple[str, float]], **extra: Any
    ) -> dict[str, Any]:
        unit = await self.unit(self.a)
        return {
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": title, "description": "Gut."}},
            "base_servings": 2,
            "steps": [
                {
                    "translations": {"de-AT": {"text": "Alles mischen."}},
                    "ingredients": [
                        {"ingredient_id": i, "amount": amount, "unit_id": unit}
                        for i, amount in lines
                    ],
                }
            ],
            **extra,
        }

    async def shared_recipe(
        self, title: str, lines: list[tuple[str, float]], *, publish: bool = True, **extra: Any
    ) -> dict[str, Any]:
        body = await self.recipe_body(
            title,
            lines,
            visibility="shared",
            shared_peer_ids=[str(self.b_on_a.public_id)],
            **extra,
        )
        created = await self.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
        assert created.status_code == 201, created.text
        recipe: dict[str, Any] = created.json()
        if publish:
            published = await self.a.post(f"{WEB}/recipes/{recipe['id']}/publish", headers=CSRF)
            assert published.status_code == 200, published.text
            recipe = published.json()
        return recipe

    async def save_a(self, recipe_id: str, body: dict[str, Any]) -> dict[str, Any]:
        saved = await self.a.put(f"{WEB}/recipes/{recipe_id}", headers=CSRF, json=body)
        assert saved.status_code == 200, saved.text
        result: dict[str, Any] = saved.json()
        return result

    # ── Receiving side ───────────────────────────────────────────────

    async def incoming(self, status: str = "pending") -> list[dict[str, Any]]:
        listed = await self.b.get(f"{WEB}/admin/incoming-recipes", params={"status": status})
        assert listed.status_code == 200, listed.text
        result: list[dict[str, Any]] = listed.json()
        return result

    async def accept(
        self, item_id: str, decisions: list[dict[str, Any]] | None = None
    ) -> httpx.Response:
        return await self.b.post(
            f"{WEB}/admin/incoming-recipes/{item_id}/accept",
            headers=CSRF,
            json={"decisions": decisions or []},
        )

    async def accept_creating(self, item: dict[str, Any]) -> str:
        """Accepts with "create" for every entry; answers the mirror's id."""
        accepted = await self.accept(
            item["id"],
            [
                {"kind": e["kind"], "source_id": e["source_id"], "action": "create"}
                for e in item["entries"]
            ],
        )
        assert accepted.status_code == 200, accepted.text
        return str(accepted.json()["id"])

    async def mirror_of(self, source_id: str) -> dict[str, Any] | None:
        async with self.sessions_b() as db:
            row = await db.scalar(
                select(RecipeModel)
                .join(RecipeMirrorModel, RecipeMirrorModel.recipe_id == RecipeModel.id)
                .where(RecipeMirrorModel.origin_public_id == _uuid(source_id))
            )
        if row is None:
            return None
        detail = await self.b.get(f"{WEB}/recipes/{row.public_id}")
        assert detail.status_code == 200, detail.text
        result: dict[str, Any] = detail.json()
        return result

    async def share_and_accept(self, title: str, lines: list[tuple[str, float]]) -> tuple[str, str]:
        """Shares a recipe from A and accepts it on B, creating every
        entry; answers the source id and the mirror id."""
        recipe = await self.shared_recipe(title, lines)
        await self.settle()
        (item,) = [i for i in await self.incoming() if i["source_id"] == recipe["id"]]
        return recipe["id"], await self.accept_creating(item)


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


@pytest.fixture
async def mirrors(
    login_system: LoginSystem, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Mirrors]:
    with tempfile.TemporaryDirectory(prefix="cuisine-mirror-b-") as folder:
        engine_b = build_engine(DatabaseSettings(url=f"sqlite:///{Path(folder) / 'b.db'}"))
        sessions_b = async_sessionmaker(autoflush=False, expire_on_commit=False, bind=engine_b)
        async with engine_b.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            to_a, to_b = Link(), Link()
            app_a = build_app(base_url=A_URL, peer_client=to_b.client())
            app_b = build_app(base_url=B_URL, peer_client=to_a.client())
            to_a.app, to_b.app = app_a, app_b

            async def db_b() -> AsyncIterator[AsyncSession]:
                async with sessions_b() as session:
                    yield session

            app_b.dependency_overrides[deps.get_db] = db_b
            await cookbook_seed.ensure_reference_data(ingredients=False)
            monkeypatch.setattr(seed, "SessionLocal", sessions_b)
            monkeypatch.setattr(cookbook_seed, "SessionLocal", sessions_b)
            await seed.ensure_system_user()
            await cookbook_seed.ensure_reference_data(ingredients=False)
            monkeypatch.undo()
            async with sessions_b() as db:
                admin_b = await system_user(SqlAlchemyUserRepository(db))
            assert admin_b is not None
            app_b.dependency_overrides[auth_deps.get_current_user] = lambda: admin_b
            for sessions in (SessionLocal, sessions_b):
                async with sessions() as db:
                    await SqlAlchemySettingsRepository(db).save_features(
                        FeatureSettings(peering=True)
                    )
                    await db.commit()
                await _privacy(sessions)
            async with (
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app_a), base_url="https://testserver"
                ) as a,
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app_b), base_url="https://testserver"
                ) as b,
            ):
                await login_system(a)
                link = (await a.post(f"{WEB}/admin/peers/invitations", headers=CSRF)).json()["link"]
                accepted = await b.post(
                    f"{WEB}/admin/peers/accept", headers=CSRF, json={"invitation_url": link}
                )
                assert accepted.status_code == 200, accepted.text
                # A new pairing takes the peer's recipes in at once ("sync
                # all"); these tests drive the administrator's accept queue,
                # so both sides switch it off as an administrator would.
                for sessions in (SessionLocal, sessions_b):
                    async with sessions() as db:
                        await db.execute(update(PeerModel).values(sync_all=False))
                        await db.commit()
                async with SessionLocal() as db:
                    (b_on_a,) = await Platform(db).peers.list_active()
                async with sessions_b() as db:
                    (a_on_b,) = await Platform(db).peers.list_active()
                pair = Mirrors(
                    a=a,
                    b=b,
                    app_a=app_a,
                    app_b=app_b,
                    sessions_b=sessions_b,
                    to_a=to_a,
                    to_b=to_b,
                    b_on_a=b_on_a,
                    a_on_b=a_on_b,
                    admin_b=admin_b,
                )
                await pair.settle()
                yield pair
        finally:
            await engine_b.dispose()


# ── Sharing, the queue and acceptance ────────────────────────────────


async def test_a_shared_recipe_waits_for_acceptance_and_then_mirrors(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren", allergens=["mustard"])
    targets = (await mirrors.a.get(f"{WEB}/peers/share-targets")).json()
    assert [t["id"] for t in targets] == [str(mirrors.b_on_a.public_id)]
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    edit = (await mirrors.a.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    assert [p["id"] for p in edit["shared_peers"]] == [str(mirrors.b_on_a.public_id)]
    await mirrors.settle()

    # Nothing is visible before an administrator accepts it.
    assert (await mirrors.b.get(f"{WEB}/recipes")).json()["total"] == 0
    (item,) = await mirrors.incoming()
    assert item["title"] == "Krenfleisch"
    assert item["kind"] == "new"
    assert item["author_name"] == "Test Admin"
    assert item["peer"]["id"] == str(mirrors.a_on_b.public_id)
    # The unit matched by its seed key; the ingredient needs a decision.
    assert [(e["kind"], e["name"], e["allergens"]) for e in item["entries"]] == [
        ("ingredient", "Kren", ["mustard"])
    ]
    refused = await mirrors.accept(item["id"])
    assert refused.status_code == 422
    assert refused.json()["code"] == "PeerMappingError"
    assert refused.json()["missing"] == [f"ingredient:{item['entries'][0]['source_id']}"]

    mirror_id = await mirrors.accept_creating(item)
    assert await mirrors.incoming() == []
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert detail["title"] == "Krenfleisch"
    assert detail["can_edit"] is False
    assert detail["can_delete"] is False
    assert detail["peer_capped"] is True
    assert detail["owner"] is None
    assert detail["mirror"]["author_name"] == "Test Admin"
    assert detail["mirror"]["instance_name"] == mirrors.a_on_b.name
    details = detail["mirror_details"]
    assert details["source_url"] == f"{A_URL}/r/{recipe['id']}"
    assert details["peer"]["id"] == str(mirrors.a_on_b.public_id)
    assert [i["name"] for i in detail["ingredients"]] == ["Kren"]
    assert detail["allergens"] == ["mustard"]
    # The created ingredient is a draft of the review queue, without owner.
    created = (await mirrors.b.get(f"{WEB}/ingredients", params={"search": "Kren"})).json()
    assert [i["status"] for i in created["items"]] == ["draft"]
    # Listed with its attribution.
    listed = (await mirrors.b.get(f"{WEB}/recipes")).json()["items"]
    assert listed[0]["mirror"]["author_name"] == "Test Admin"


async def test_mirror_visibility_follows_the_incoming_switch(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    outsider = await mirrors.b_user("outsider")
    member = await mirrors.b_user("member")
    group = await mirrors.b.post(
        f"{WEB}/groups",
        headers=CSRF,
        json={"name": "Family", "member_ids": [str(member.public_id)]},
    )
    assert group.status_code == 201, group.text
    mirrors.as_user_b(outsider)
    assert (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).status_code == 200

    mirrors.as_user_b(mirrors.admin_b)
    switched = await mirrors.b.put(
        f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/switches",
        headers=CSRF,
        json={
            "users_may_share": True,
            "sync_all": False,
            "accept_incoming": True,
            "mirror_visibility": "group",
            "mirror_group": group.json()["id"],
        },
    )
    assert switched.status_code == 200, switched.text
    mirrors.as_user_b(outsider)
    assert (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).status_code == 404
    assert (await mirrors.b.get(f"{WEB}/recipes")).json()["total"] == 0
    mirrors.as_user_b(await _reload(mirrors, member))
    assert (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).status_code == 200


async def _reload(mirrors: Mirrors, user: User) -> User:
    async with mirrors.sessions_b() as db:
        found = await SqlAlchemyUserRepository(db).get(user.id)
    assert found is not None
    return found


# ── Updates and the mapping ──────────────────────────────────────────


async def test_updates_apply_or_wait_for_new_entries(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    before = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    line_id = before["steps"][0]["ingredients"][0]["line_id"]

    # All entries mapped: the update applies at once, ids stay.
    body = await mirrors.recipe_body(
        "Krenfleisch neu",
        [(kren, 30)],
        visibility="shared",
        shared_peer_ids=[str(mirrors.b_on_a.public_id)],
    )
    body["steps"][0]["id"] = (await mirrors.a.get(f"{WEB}/recipes/{source_id}/edit")).json()[
        "steps"
    ][0]["id"]
    body["steps"][0]["ingredients"][0]["id"] = (
        await mirrors.a.get(f"{WEB}/recipes/{source_id}/edit")
    ).json()["steps"][0]["ingredients"][0]["id"]
    await mirrors.save_a(source_id, body)
    await mirrors.settle()
    after = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert after["title"] == "Krenfleisch neu"
    assert after["steps"][0]["ingredients"][0]["line_id"] == line_id
    assert after["mirror_details"]["source_revision"] != before["mirror_details"]["source_revision"]

    # A new ingredient without a mapping: the update waits.
    ingwer = await mirrors.ingredient(mirrors.a, "Ingwer")
    body["translations"]["de-AT"]["title"] = "Krenfleisch mit Ingwer"
    body["steps"][0]["ingredients"].append(
        {"ingredient_id": ingwer, "amount": 5, "unit_id": await mirrors.unit(mirrors.a)}
    )
    await mirrors.save_a(source_id, body)
    await mirrors.settle()
    held = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert held["title"] == "Krenfleisch neu"
    (item,) = await mirrors.incoming()
    assert item["kind"] == "update"
    assert item["mirror_id"] == mirror_id
    assert [e["name"] for e in item["entries"]] == ["Ingwer"]

    local = await mirrors.ingredient(mirrors.b, "Ingwer lokal")
    accepted = await mirrors.accept(
        item["id"],
        [
            {
                "kind": "ingredient",
                "source_id": item["entries"][0]["source_id"],
                "action": "map",
                "target_id": local,
            }
        ],
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["id"] == mirror_id
    resolved = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert resolved["title"] == "Krenfleisch mit Ingwer"
    assert sorted(i["name"] for i in resolved["ingredients"]) == ["Ingwer lokal", "Kren"]


async def test_a_mapping_is_reused_and_corrections_apply_to_every_mirror(
    mirrors: Mirrors,
) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren", allergens=["mustard"])
    _, first = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    recipe = await mirrors.shared_recipe("Krensuppe", [(kren, 40)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    # Kren was decided for the first recipe already.
    assert item["entries"] == []
    accepted = await mirrors.accept(item["id"])
    assert accepted.status_code == 200, accepted.text
    second = accepted.json()["id"]

    mappings = (
        await mirrors.b.get(f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/mappings")
    ).json()
    kren_mapping = next(m for m in mappings if m["name"] == "Kren")
    assert kren_mapping["action"] == "map"
    assert kren_mapping["created_here"] is True
    assert kren_mapping["used_by"] == 2
    assert next(m for m in mappings if m["kind"] == "unit")["matched_by"] == "seed_key"

    corrected = await mirrors.b.put(
        f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/mappings/ingredient/"
        f"{kren_mapping['source_id']}",
        headers=CSRF,
        json={"action": "plain"},
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["action"] == "plain"
    for mirror_id in (first, second):
        detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
        assert detail["ingredients"] == []
        (plain,) = detail["mirror_details"]["plain_lines"]
        assert plain["name"] == "Kren"
        assert plain["allergens"] == ["mustard"]
        # A plain-text line keeps the source's allergens.
        assert detail["allergens"] == ["mustard"]
    assert recipe["translations"]["de-AT"]["title"] == "Krensuppe"


async def test_allergens_are_the_union_of_local_and_source_data(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren", allergens=["mustard"])
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    local = await mirrors.ingredient(mirrors.b, "Meerrettich", allergens=["celery"])
    accepted = await mirrors.accept(
        item["id"],
        [
            {
                "kind": "ingredient",
                "source_id": item["entries"][0]["source_id"],
                "action": "map",
                "target_id": local,
            }
        ],
    )
    assert accepted.status_code == 200, accepted.text
    detail = (await mirrors.b.get(f"{WEB}/recipes/{accepted.json()['id']}")).json()
    assert detail["allergens"] == ["celery", "mustard"]
    assert detail["source_allergens_added"] == ["mustard"]
    listed = (await mirrors.b.get(f"{WEB}/recipes")).json()["items"]
    assert listed[0]["allergens"] == ["celery", "mustard"]
    assert recipe["id"]


async def test_an_unknown_diet_marker_is_kept_and_might_not_fit(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    # The ingredient created from the source's data waits for review as a
    # draft, so the mirror claims no diet until someone activates it.
    assert detail["diets"] == []
    (draft_id,) = detail["unconfirmed_ingredient_ids"]
    async with mirrors.sessions_b() as db:
        await db.execute(
            update(IngredientModel)
            .where(IngredientModel.public_id == uuid.UUID(draft_id))
            .values(status="active")
        )
        await db.commit()
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert "vegan" in detail["diets"]
    # A newer source marks the ingredient with a marker this release lacks.
    async with mirrors.sessions_b() as db:
        row = await db.scalar(
            select(PeerCatalogueMappingModel).where(PeerCatalogueMappingModel.kind == "ingredient")
        )
        assert row is not None
        row.remote_data = {**row.remote_data, "diet_markers": ["insects"]}
        await db.commit()
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert detail["unknown_diet_markers"] == ["insects"]
    assert detail["diets"] == []

    # The dinner guest check treats it as "might not fit".
    async with mirrors.sessions_b() as db:
        settings = SqlAlchemySettingsRepository(db)
        await settings.save_features(FeatureSettings(peering=True, dinner_guests=True))
        await db.commit()
    guest = await mirrors.b_user("guest")
    mirrors.as_user_b(guest)
    assert (
        await mirrors.b.put(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    ).status_code == 200
    restriction = await mirrors.b.post(
        f"{WEB}/users/me/food-restrictions", headers=CSRF, json={"kind": "diet", "diet": "vegan"}
    )
    assert restriction.status_code == 201, restriction.text
    patched = await mirrors.b.patch(
        f"{WEB}/users/me", headers=CSRF, json={"share_restrictions_with_hosts": True}
    )
    assert patched.status_code == 200, patched.text
    mirrors.as_user_b(mirrors.admin_b)
    checked = (
        await mirrors.b.get(f"{WEB}/recipes/{mirror_id}", params={"guests": str(guest.public_id)})
    ).json()
    assert checked["unsuitable_for_guests"] is True


# ── What is sent and withdrawn ───────────────────────────────────────


async def test_drafts_are_never_sent(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    await mirrors.shared_recipe("Entwurf", [(kren, 20)], publish=False)
    await mirrors.settle()
    assert await mirrors.incoming() == []
    assert "GET /items" not in " ".join(mirrors.to_a.requests)


async def test_withdrawals_remove_the_mirror_and_reshares_queue_again(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    # A local variation and a favourite on the mirror.
    variation = await mirrors.b.post(
        f"{WEB}/recipes/{mirror_id}/variations",
        headers=CSRF,
        json={"name": "Scharf", "locale": "de-AT", "changes": []},
    )
    assert variation.status_code == 201, variation.text
    assert (
        await mirrors.b.put(
            f"{WEB}/recipes/{mirror_id}/favourite", headers=CSRF, json={"favourite": True}
        )
    ).status_code == 204

    # Unpublishing withdraws it.
    assert (
        await mirrors.a.post(f"{WEB}/recipes/{source_id}/unpublish", headers=CSRF)
    ).status_code == 200
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None
    assert (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).status_code == 404

    # Published again, it waits for a decision again (the mapping holds).
    assert (
        await mirrors.a.post(f"{WEB}/recipes/{source_id}/publish", headers=CSRF)
    ).status_code == 200
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    assert item["entries"] == []
    accepted = await mirrors.accept(item["id"])
    assert accepted.status_code == 200

    # Narrowing it withdraws it.
    body = await mirrors.recipe_body("Krenfleisch", [(kren, 20)], visibility="instance")
    await mirrors.save_a(source_id, body)
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None

    # Sharing again and then removing the peer withdraws it too.
    body = await mirrors.recipe_body(
        "Krenfleisch",
        [(kren, 20)],
        visibility="shared",
        shared_peer_ids=[str(mirrors.b_on_a.public_id)],
    )
    await mirrors.save_a(source_id, body)
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    await mirrors.save_a(source_id, {**body, "shared_peer_ids": []})
    await mirrors.settle()
    assert await mirrors.incoming() == []

    # Deleting it withdraws it.
    await mirrors.save_a(source_id, body)
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    assert (await mirrors.accept(item["id"])).status_code == 200
    assert (await mirrors.a.delete(f"{WEB}/recipes/{source_id}", headers=CSRF)).status_code == 204
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None


async def test_deleting_the_owner_withdraws_the_recipe(mirrors: Mirrors) -> None:
    created = await mirrors.a.post(
        f"{WEB}/users",
        headers=CSRF,
        json={
            "full_name": "Anna",
            "email": "anna@example.com",
            "password": "cook-password-1",
            "permissions": ["write:recipes", "write:ingredients"],
        },
    )
    assert created.status_code == 201, created.text
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mirrors.app_a), base_url="https://testserver"
    ) as anna:
        await login(anna, "anna@example.com", "cook-password-1")
        kren = await mirrors.ingredient(anna, "Kren")
        unit = await mirrors.unit(anna)
        made = await anna.post(
            f"{WEB}/recipes",
            headers=CSRF,
            json={
                "original_locale": "de-AT",
                "translations": {"de-AT": {"title": "Annas Kren"}},
                "steps": [
                    {
                        "translations": {"de-AT": {"text": "Reiben."}},
                        "ingredients": [{"ingredient_id": kren, "amount": 5, "unit_id": unit}],
                    }
                ],
                "visibility": "shared",
                "shared_peer_ids": [str(mirrors.b_on_a.public_id)],
            },
        )
        assert made.status_code == 201, made.text
        source_id = made.json()["id"]
        assert (
            await anna.post(f"{WEB}/recipes/{source_id}/publish", headers=CSRF)
        ).status_code == 200
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    await mirrors.accept_creating(item)
    assert await mirrors.mirror_of(source_id) is not None

    deleted = await mirrors.a.request(
        "DELETE",
        f"{WEB}/users/{created.json()['id']}",
        headers=CSRF,
        json={"ownerless_visibility": "instance"},
    )
    assert deleted.status_code in (200, 204), deleted.text
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None


async def test_public_recipes_go_to_every_peer_users_may_share_with(mirrors: Mirrors) -> None:
    await _privacy(SessionLocal, allow_public_recipes=True)
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    body = await mirrors.recipe_body("Öffentlich", [(kren, 20)], visibility="public")
    created = await mirrors.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    source_id = created.json()["id"]
    await mirrors.a.post(f"{WEB}/recipes/{source_id}/publish", headers=CSRF)
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    assert item["source_id"] == source_id

    async def users_may_share(on: bool) -> None:
        changed = await mirrors.a.put(
            f"{WEB}/admin/peers/{mirrors.b_on_a.public_id}/switches",
            headers=CSRF,
            json={
                "users_may_share": on,
                "accept_incoming": True,
                "mirror_visibility": "instance",
                "sync_all": False,
            },
        )
        assert changed.status_code == 200, changed.text

    await users_may_share(False)
    await mirrors.settle()
    assert await mirrors.incoming() == []

    await users_may_share(True)
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    await mirrors.accept_creating(item)
    assert await mirrors.mirror_of(source_id) is not None
    # Public recipes no longer allowed: the recipe reads as instance and
    # leaves the peer.
    privacy = (await mirrors.a.get(f"{WEB}/settings/privacy")).json()
    saved = await mirrors.a.put(
        f"{WEB}/settings/privacy", headers=CSRF, json={**privacy, "allow_public_recipes": False}
    )
    assert saved.status_code == 200, saved.text
    await mirrors.settle()
    assert await mirrors.mirror_of(source_id) is None


async def test_revoking_removes_mirrors_waiting_recipes_and_mappings(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    copy = await mirrors.b.post(f"{WEB}/recipes/{mirror_id}/copy", headers=CSRF)
    assert copy.status_code == 201, copy.text
    await mirrors.shared_recipe("Wartet", [(kren, 10)])
    await mirrors.settle()
    assert len(await mirrors.incoming()) == 1

    revoked = await mirrors.a.post(
        f"{WEB}/admin/peers/{mirrors.b_on_a.public_id}/revoke", headers=CSRF
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["peer_notified"] is True
    assert await mirrors.mirror_of(source_id) is None
    async with mirrors.sessions_b() as db:
        assert (await db.scalars(select(PeerCatalogueMappingModel))).all() == []
    assert await mirrors.incoming() == []
    # The fork stays.
    assert (await mirrors.b.get(f"{WEB}/recipes/{copy.json()['id']}")).status_code == 200


# ── Read only, variations, forks, sub-recipes ────────────────────────


async def test_a_mirror_is_read_only(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    body = await mirrors.recipe_body("Geändert", [])
    for method, path, payload in (
        ("PUT", f"/recipes/{mirror_id}", body),
        ("GET", f"/recipes/{mirror_id}/edit", None),
        ("POST", f"/recipes/{mirror_id}/publish", None),
        ("POST", f"/recipes/{mirror_id}/unpublish", None),
        ("DELETE", f"/recipes/{mirror_id}", None),
        ("PUT", f"/recipes/{mirror_id}/co-editors", {"user_ids": []}),
        ("GET", f"/recipes/{mirror_id}/revisions", None),
        ("POST", f"/recipes/{mirror_id}/revisions/1/restore", None),
        (
            "PUT",
            f"/recipes/{mirror_id}/translation",
            {"locale": "en-GB", "text": {"title": "Changed"}, "steps": []},
        ),
    ):
        answer = await mirrors.b.request(method, f"{WEB}{path}", headers=CSRF, json=payload)
        assert answer.status_code == 409, (method, path, answer.text)
        assert answer.json()["code"] == "MirrorReadOnlyError"
    # The personal layer works as on local recipes.
    assert (
        await mirrors.b.put(f"{WEB}/recipes/{mirror_id}/note", headers=CSRF, json={"text": "Gut"})
    ).status_code == 200


async def test_source_variations_are_mirrored_read_only(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    made = await mirrors.a.post(
        f"{WEB}/recipes/{recipe['id']}/variations",
        headers=CSRF,
        json={"name": "Mehr Kren", "locale": "de-AT", "note": "Für Mutige", "changes": []},
    )
    assert made.status_code == 201, made.text
    private = await mirrors.a.post(
        f"{WEB}/recipes/{recipe['id']}/variations",
        headers=CSRF,
        json={"name": "Geheim", "locale": "de-AT", "private": True, "changes": []},
    )
    assert private.status_code == 201, private.text
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    mirror_id = await mirrors.accept_creating(item)
    variations = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}/variations")).json()
    assert [(v["name"], v["mirrored"], v["source_author_name"]) for v in variations] == [
        ("Mehr Kren", True, "Test Admin")
    ]
    changed = await mirrors.b.put(
        f"{WEB}/recipes/{mirror_id}/variations/{variations[0]['id']}",
        headers=CSRF,
        json={"name": "X", "locale": "de-AT", "changes": []},
    )
    assert changed.status_code == 409
    assert changed.json()["code"] == "MirrorReadOnlyError"


async def test_a_fork_is_capped_and_mirrors_go_nowhere(mirrors: Mirrors) -> None:
    await _privacy(mirrors.sessions_b, allow_public_recipes=True)
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    copy = await mirrors.b.post(f"{WEB}/recipes/{mirror_id}/copy", headers=CSRF)
    assert copy.status_code == 201, copy.text
    fork = copy.json()
    assert fork["peer_capped"] is True
    assert fork["based_on"]["recipe"]["id"] == mirror_id
    edit = (await mirrors.b.get(f"{WEB}/recipes/{fork['id']}/edit")).json()
    unit = await mirrors.unit(mirrors.b)
    body = {
        "original_locale": "de-AT",
        "translations": edit["translations"],
        "steps": [
            {
                "translations": s["translations"],
                "ingredients": [
                    {"ingredient_id": i["ingredient_id"], "amount": i["amount"], "unit_id": unit}
                    for i in s["ingredients"]
                ],
            }
            for s in edit["steps"]
        ],
    }
    public = await mirrors.b.put(
        f"{WEB}/recipes/{fork['id']}", headers=CSRF, json={**body, "visibility": "public"}
    )
    assert public.status_code == 422
    assert public.json()["code"] == "PeerShareNotAllowedError"
    shared = await mirrors.b.put(
        f"{WEB}/recipes/{fork['id']}",
        headers=CSRF,
        json={
            **body,
            "visibility": "shared",
            "shared_peer_ids": [str(mirrors.a_on_b.public_id)],
        },
    )
    assert shared.status_code == 422
    assert shared.json()["code"] == "PeerShareNotAllowedError"
    # A copy of the copy stays capped.
    again = await mirrors.b.post(f"{WEB}/recipes/{fork['id']}/copy", headers=CSRF)
    assert again.json()["peer_capped"] is True


async def test_sub_recipes_are_items_of_their_own(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    sub = await mirrors.shared_recipe("Krensauce", [(kren, 20)])
    body = await mirrors.recipe_body(
        "Tafelspitz",
        [],
        visibility="shared",
        shared_peer_ids=[str(mirrors.b_on_a.public_id)],
    )
    body["steps"][0]["ingredients"] = [{"sub_recipe_id": sub["id"], "amount": 1}]
    created = await mirrors.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    parent_id = created.json()["id"]
    await mirrors.a.post(f"{WEB}/recipes/{parent_id}/publish", headers=CSRF)
    await mirrors.settle()
    items = {i["title"]: i for i in await mirrors.incoming()}
    assert set(items) == {"Krensauce", "Tafelspitz"}
    assert items["Tafelspitz"]["sub_recipes"] == [
        {"source_id": sub["id"], "title": "Krensauce", "mirrored": False, "waiting": True}
    ]
    parent_mirror = await mirrors.accept_creating(items["Tafelspitz"])
    detail = (await mirrors.b.get(f"{WEB}/recipes/{parent_mirror}")).json()
    assert detail["needs"] == []
    assert [u["title"] for u in detail["mirror_details"]["unlinked_sub_recipes"]] == ["Krensauce"]

    sub_mirror = await mirrors.accept_creating(items["Krensauce"])
    detail = (await mirrors.b.get(f"{WEB}/recipes/{parent_mirror}")).json()
    assert [n["sub_recipe"]["id"] for n in detail["needs"]] == [sub_mirror]
    assert detail["mirror_details"]["unlinked_sub_recipes"] == []

    # The sub-recipe leaves: the parent mirror loses the link, not itself.
    body_sub = await mirrors.recipe_body("Krensauce", [(kren, 20)], visibility="instance")
    await mirrors.save_a(sub["id"], body_sub)
    await mirrors.settle()
    assert await mirrors.mirror_of(sub["id"]) is None
    detail = (await mirrors.b.get(f"{WEB}/recipes/{parent_mirror}")).json()
    assert detail["needs"] == []
    (unlinked,) = detail["mirror_details"]["unlinked_sub_recipes"]
    # Not shared with this instance any more: no title.
    assert unlinked["title"] is None


async def test_the_author_name_follows_the_author_setting(mirrors: Mirrors) -> None:
    patched = await mirrors.a.patch(
        f"{WEB}/users/me", headers=CSRF, json={"show_name_on_paired_instances": False}
    )
    assert patched.status_code == 200, patched.text
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert detail["mirror"]["author_name"] is None
    assert detail["mirror_details"]["author_name"] is None


async def test_mirrors_keep_their_catalogue_entries_in_use(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    local = await mirrors.ingredient(mirrors.b, "Meerrettich")
    await mirrors.accept(
        item["id"],
        [
            {
                "kind": "ingredient",
                "source_id": item["entries"][0]["source_id"],
                "action": "map",
                "target_id": local,
            }
        ],
    )
    impact = (await mirrors.b.get(f"{WEB}/ingredients/{local}/deletion-impact")).json()
    assert impact["recipe_count"] == 1
    assert (await mirrors.b.delete(f"{WEB}/ingredients/{local}", headers=CSRF)).status_code == 409
    assert recipe["id"]


async def test_a_rejected_recipe_stays_rejected_until_reopened(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    rejected = await mirrors.b.post(
        f"{WEB}/admin/incoming-recipes/{item['id']}/reject", headers=CSRF
    )
    assert rejected.json()["status"] == "rejected"
    body = await mirrors.recipe_body(
        "Krenfleisch neu",
        [(kren, 25)],
        visibility="shared",
        shared_peer_ids=[str(mirrors.b_on_a.public_id)],
    )
    await mirrors.save_a(recipe["id"], body)
    await mirrors.settle()
    assert await mirrors.incoming() == []
    (kept,) = await mirrors.incoming("rejected")
    assert kept["title"] == "Krenfleisch neu"
    reopened = await mirrors.b.post(
        f"{WEB}/admin/incoming-recipes/{item['id']}/reopen", headers=CSRF
    )
    assert reopened.json()["status"] == "pending"
    assert len(await mirrors.incoming()) == 1


async def test_a_gained_capability_refetches_the_mirrors(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    source_id, _ = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    async with mirrors.sessions_b() as db:
        await db.execute(
            update(PeerModel).where(PeerModel.id == mirrors.a_on_b.id).values(capabilities=[])
        )
        await db.commit()
    refreshed = await mirrors.b.post(
        f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/refresh", headers=CSRF
    )
    assert refreshed.status_code == 200, refreshed.text
    async with mirrors.sessions_b() as db:
        mirror = await db.scalar(select(RecipeMirrorModel))
        assert mirror is not None and mirror.etag == ""
    fetched = len([r for r in mirrors.to_a.requests if r.startswith("GET /items/recipe/")])
    await mirrors.settle()
    assert len([r for r in mirrors.to_a.requests if r.startswith("GET /items/recipe/")]) > fetched
    async with mirrors.sessions_b() as db:
        mirror = await db.scalar(select(RecipeMirrorModel))
        assert mirror is not None and mirror.etag != ""
    assert source_id


async def test_agents_read_mirrors_with_attribution_and_cannot_write_them(
    mirrors: Mirrors,
) -> None:
    # This time B is the source and A holds the mirror, since the agent
    # surface runs on A's database.
    kren = await mirrors.ingredient(mirrors.b, "Kren")
    unit = await mirrors.unit(mirrors.b)
    made = await mirrors.b.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": "Krenfleisch"}},
            "steps": [
                {
                    "translations": {"de-AT": {"text": "Reiben."}},
                    "ingredients": [{"ingredient_id": kren, "amount": 5, "unit_id": unit}],
                }
            ],
            "visibility": "shared",
            "shared_peer_ids": [str(mirrors.a_on_b.public_id)],
        },
    )
    assert made.status_code == 201, made.text
    assert (
        await mirrors.b.post(f"{WEB}/recipes/{made.json()['id']}/publish", headers=CSRF)
    ).status_code == 200
    await mirrors.settle()
    (item,) = (await mirrors.a.get(f"{WEB}/admin/incoming-recipes")).json()
    accepted = await mirrors.a.post(
        f"{WEB}/admin/incoming-recipes/{item['id']}/accept",
        headers=CSRF,
        json={
            "decisions": [
                {"kind": e["kind"], "source_id": e["source_id"], "action": "create"}
                for e in item["entries"]
            ]
        },
    )
    assert accepted.status_code == 200, accepted.text
    mirror_id = accepted.json()["id"]

    token = await mcp_token(mirrors.a, ["use:mcp", "write:recipes", "write:ingredients"])
    found = await mcp_call(mirrors.a, token, "search_recipes", {"query": "Kren"})
    assert found["isError"] is False, found
    (hit,) = found["structuredContent"]["recipes"]
    assert hit["from_instance"] == mirrors.b_on_a.name
    assert hit["source_author"] == "Test Admin"
    read = await mcp_call(mirrors.a, token, "get_recipe", {"recipe_id": mirror_id})
    assert read["structuredContent"]["mirror_details"]["source_url"].startswith(B_URL)
    refused = await mcp_call(
        mirrors.a,
        token,
        "add_recipe_translation",
        {"recipe_id": mirror_id, "locale": "en-GB", "title": "Horseradish", "steps": ["Grate."]},
    )
    assert refused["isError"] is True
    assert "read only" in str(refused["content"])


def test_the_privacy_draft_describes_peering_while_it_is_on() -> None:
    facts = PrivacyFacts(
        instance_name="Cuisine",
        storage_provider="local",
        backup_keep_days=14,
        backup_hour_utc=3,
        security_log_days=90,
        agent_calls_days=90,
        webhook_deliveries_days=30,
        recipe_revisions_days=0,
        agents_enabled=False,
        agent_token_max_days=30,
        webhooks_enabled=False,
        usda_enabled=False,
        mail_enabled=False,
        households_enabled=True,
        dinner_guests_enabled=True,
    )
    assert "## Paired instances" not in privacy_draft(facts, "en-GB")
    on = replace(facts, peering_enabled=True)
    english = privacy_draft(on, "en-GB")
    assert "## Paired instances" in english
    assert "none while public recipes are not allowed" in english
    assert "## Verbundene Instanzen" in privacy_draft(on, "de-AT")


async def test_a_mirror_is_never_exported(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    exported = await mirrors.b.get(f"{WEB}/recipes/{mirror_id}/export")
    assert exported.status_code == 409, exported.text
    assert exported.json()["code"] == "MirrorReadOnlyError"
    # The administrator's bulk export leaves mirrors out, chosen or not.
    for params in ({}, {"recipe_id": mirror_id}):
        bulk = await mirrors.b.get(f"{WEB}/admin/recipes/export", params=params)
        assert bulk.status_code == 200, bulk.text
        with zipfile.ZipFile(io.BytesIO(bulk.content)) as archive:
            document = json.loads(archive.read("recipes.json"))
        assert [r["id"] for r in document["recipes"]] == []


async def test_plain_lines_of_a_mirror_go_on_the_shopping_list(mirrors: Mirrors) -> None:
    kren = await mirrors.ingredient(mirrors.a, "Kren", allergens=["mustard"])
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    mappings = (
        await mirrors.b.get(f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/mappings")
    ).json()
    kren_mapping = next(m for m in mappings if m["name"] == "Kren")
    corrected = await mirrors.b.put(
        f"{WEB}/admin/peers/{mirrors.a_on_b.public_id}/mappings/ingredient/"
        f"{kren_mapping['source_id']}",
        headers=CSRF,
        json={"action": "plain"},
    )
    assert corrected.status_code == 200, corrected.text
    created = await mirrors.b.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]
    for _ in range(2):
        added = await mirrors.b.post(
            f"{WEB}/shopping-lists/{list_id}/recipes",
            headers=CSRF,
            json={"recipe_id": mirror_id, "servings": 4},
        )
        assert added.status_code == 200, added.text
        assert added.json()["added"] == 1
    items = (await mirrors.b.get(f"{WEB}/shopping-lists/{list_id}")).json()["items"]
    # Scaled from 2 to 4 servings, and the second add joins the first item.
    assert [(i["ingredient_id"], i["text"], i["amount"], i["unit"]["code"]) for i in items] == [
        (None, "Kren", 80.0, "g")
    ]


def _avatar_png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 120, 200)).save(out, format="PNG")
    return out.getvalue()


async def _set_avatar(client: httpx.AsyncClient) -> None:
    saved = await client.put(
        f"{WEB}/users/me/avatar",
        headers=CSRF,
        files={"file": ("me.png", _avatar_png(), "image/png")},
    )
    assert saved.status_code == 200, saved.text


async def test_the_author_avatar_travels_with_the_name(mirrors: Mirrors) -> None:
    await _set_avatar(mirrors.a)
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    recipe = await mirrors.shared_recipe("Krenfleisch", [(kren, 20)])
    made = await mirrors.a.post(
        f"{WEB}/recipes/{recipe['id']}/variations",
        headers=CSRF,
        json={"name": "Mehr Kren", "locale": "de-AT", "changes": []},
    )
    assert made.status_code == 201, made.text
    await mirrors.settle()
    (item,) = await mirrors.incoming()
    mirror_id = await mirrors.accept_creating(item)

    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    avatar = detail["mirror"]["author_avatar_id"]
    assert avatar is not None
    assert detail["mirror_details"]["author_avatar_id"] == avatar
    listed = (await mirrors.b.get(f"{WEB}/recipes")).json()["items"]
    assert listed[0]["mirror"]["author_avatar_id"] == avatar
    (variation,) = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}/variations")).json()
    assert variation["source_author_avatar_id"] == avatar
    served = await mirrors.b.get(f"{WEB}/files/{avatar}/content", params={"variant": "thumbnail"})
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"

    # Withdrawn, the mirror takes the avatar it came with along.
    assert (
        await mirrors.a.post(f"{WEB}/recipes/{recipe['id']}/unpublish", headers=CSRF)
    ).status_code == 200
    await mirrors.settle()
    assert (await mirrors.b.get(f"{WEB}/files/{avatar}")).status_code == 404


async def test_no_avatar_travels_without_the_name(mirrors: Mirrors) -> None:
    await _set_avatar(mirrors.a)
    patched = await mirrors.a.patch(
        f"{WEB}/users/me", headers=CSRF, json={"show_name_on_paired_instances": False}
    )
    assert patched.status_code == 200, patched.text
    kren = await mirrors.ingredient(mirrors.a, "Kren")
    _, mirror_id = await mirrors.share_and_accept("Krenfleisch", [(kren, 20)])
    detail = (await mirrors.b.get(f"{WEB}/recipes/{mirror_id}")).json()
    assert detail["mirror"]["author_avatar_id"] is None
    assert detail["mirror_details"]["author_avatar_id"] is None
