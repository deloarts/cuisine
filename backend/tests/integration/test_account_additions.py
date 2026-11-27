"""The cookbook's side of the account additions: the health data consent
around food restrictions, the recipe revision retention, self-deletion,
"download my data" and the admin recipe archive."""

import io
import json
import zipfile
from datetime import timedelta
from typing import Any

import httpx
import pytest
from PIL import Image
from sqlalchemy import update

from src.bootstrap.nightly_jobs import run_nightly_once
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.persistence.models.user_models import UserModel
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id
from tests.integration.test_passkeys import FakeVerifier

# Written for user choice, the privacy mode in which owners pick each
# recipe's visibility; a fresh instance runs in instance mode.
pytestmark = pytest.mark.usefixtures("user_choice_privacy")

NUTS = {"kind": "allergy", "allergen": "nuts"}


async def _nut_cake(cook: httpx.AsyncClient) -> dict[str, Any]:
    nuts = await make_ingredient(cook, "Walnüsse", allergens=["nuts"])
    line = {"ingredient_id": nuts["id"], "amount": 100, "unit_id": await unit_id(cook, "g")}
    return await make_recipe(cook, "Nusskuchen", [("Backen", [line])])


# ── Health data consent ───────────────────────────────────────────────


async def test_restrictions_need_the_health_data_consent(cook: httpx.AsyncClient) -> None:
    refused = await cook.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=NUTS)
    assert refused.status_code == 403
    assert refused.json()["code"] == "ConsentRequiredError"
    await grant_health_data(cook)
    added = await cook.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=NUTS)
    assert added.status_code == 201


async def test_withdrawing_the_consent_deletes_the_restrictions(cook: httpx.AsyncClient) -> None:
    recipe = await _nut_cake(cook)
    await grant_health_data(cook)
    await cook.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=NUTS)
    assert (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()["has_warning"] is True
    withdrawn = await cook.delete(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    assert withdrawn.status_code == 200, withdrawn.text
    assert (await cook.get(f"{WEB}/users/me/food-restrictions")).json() == []
    assert (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()["has_warning"] is False


async def test_guests_without_the_consent_count_as_having_no_restrictions(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _nut_cake(cook)
    guest = await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    await grant_health_data(client)
    await client.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=NUTS)
    await client.patch(
        f"{WEB}/users/me", headers=CSRF, json={"share_restrictions_with_hosts": True}
    )
    params = {"guests": guest["id"]}
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params=params)).json()
    assert detail["unsuitable_for_guests"] is True
    # Withdrawing deletes them anyway; the check must not depend on that, so
    # take the consent away behind the API's back as well.
    async with SessionLocal() as db:
        await db.execute(
            update(UserModel)
            .where(UserModel.email == "guest@example.com")
            .values(consent_health_data_at=None)
        )
        await db.commit()
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params=params)).json()
    assert detail["unsuitable_for_guests"] is False


# ── Recipe revision retention ─────────────────────────────────────────


async def test_nightly_purge_keeps_each_recipes_newest_revision(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    recipe = await make_recipe(cook, "Rührkuchen", [("Rühren.", [])], publish=False)
    for title in ("Rührkuchen 2", "Rührkuchen 3"):
        saved = await cook.put(
            f"{WEB}/recipes/{recipe['id']}",
            headers=CSRF,
            json=recipe_payload(title, [("Rühren.", [])]),
        )
        assert saved.status_code == 200, saved.text
    async with SessionLocal() as db:
        await db.execute(
            update(RecipeRevisionModel).values(created=now_utc() - timedelta(days=400))
        )
        await db.commit()
    await admin.put(
        f"{WEB}/settings/retention",
        headers=CSRF,
        json={
            "security_log_days": 0,
            "agent_calls_days": 0,
            "webhook_deliveries_days": 0,
            "recipe_revisions_days": 365,
        },
    )
    await run_nightly_once(force=True)
    history = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions")).json()
    assert [r["number"] for r in history["items"]] == [3]


# ── Self-deletion ─────────────────────────────────────────────────────


async def _leaver(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> dict[str, Any]:
    """`leaver` with one recipe per fate, in a household with cook, and a
    shopping list shared with cook; signed in on `client`."""
    leaver = await make_user("leaver", permissions=["write:recipes", "write:ingredients"])
    await login(client, "leaver@example.com", "cook-password-1")
    founded = await client.post(f"{WEB}/households", headers=CSRF, json={"name": "WG"})
    assert founded.status_code in (200, 201), founded.text
    cook_id = (await cook.get(f"{WEB}/users/me")).json()["id"]
    invited = await client.post(
        f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": cook_id}
    )
    assert invited.status_code in (200, 201), invited.text
    invitation = (await cook.get(f"{WEB}/households/invitations")).json()[0]
    accepted = await cook.post(
        f"{WEB}/households/invitations/{invitation['id']}/accept", headers=CSRF
    )
    assert accepted.status_code == 200, accepted.text
    recipes = {
        visibility: await make_recipe(
            client, f"Rezept {visibility}", [("Kochen.", [])], visibility=visibility
        )
        for visibility in ("instance", "household", "private")
    }
    recipes["draft"] = await make_recipe(client, "Entwurf", [("Kochen.", [])], publish=False)
    await make_ingredient(client, "Bärlauch")
    await client.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Allein"})
    return {"user": leaver, "recipes": recipes}


async def test_self_deletion_follows_the_rules(
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    cook: httpx.AsyncClient,
    other_client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    # `admin` is signed in on the first client; the leaver takes it over.
    client = admin
    setup = await _leaver(make_user, client, cook)
    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert impact == {
        "recipes_kept_online": 1,
        "recipes_to_household": 1,
        "recipes_deleted": 1,
        "drafts_deleted": 1,
        "recipes_handed_over": [],
        "sub_recipes_kept_online": 0,
        "if_public_deleted": {
            "recipes_deleted": 2,
            "drafts_deleted": 1,
            "recipes_handed_over": [],
            "sub_recipes_kept_online": 0,
        },
        "can_delete_public_recipes": True,
        "ingredients_kept": 1,
        "lists_handed_over": 0,
        "lists_deleted": 1,
        "in_household": True,
        "refused_reason": None,
        "backup_keep_days": impact["backup_keep_days"],
        "backups_clear_by": impact["backups_clear_by"],
    }
    assert impact["backup_keep_days"] == 14

    wrong_name = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": "someone@example.com", "password": "cook-password-1"},
    )
    assert wrong_name.status_code == 422
    wrong_password = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": "leaver@example.com", "password": "x"},
    )
    assert wrong_password.status_code == 403
    nothing = await client.request(
        "DELETE", f"{WEB}/users/me", headers=CSRF, json={"email": "leaver@example.com"}
    )
    assert nothing.status_code == 422

    deleted = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": "leaver@example.com", "password": "cook-password-1"},
    )
    assert deleted.status_code == 204, deleted.text
    assert (await client.get(f"{WEB}/users/me")).status_code == 401

    recipes = setup["recipes"]
    online = await cook.get(f"{WEB}/recipes/{recipes['instance']['id']}")
    assert online.status_code == 200
    assert online.json()["owner"] is None
    inherited = (await cook.get(f"{WEB}/recipes/{recipes['household']['id']}")).json()
    assert inherited["owner"]["display_name"] == "Cook"
    assert inherited["can_edit"] is True
    household = (await cook.get(f"{WEB}/households/mine")).json()["household"]
    assert [m["display_name"] for m in household["members"]] == ["Cook"]
    assert "Allein" not in str((await cook.get(f"{WEB}/shopping-lists")).json())

    await login_system(client)
    for gone in (recipes["private"], recipes["draft"]):
        assert (await client.get(f"{WEB}/recipes/{gone['id']}")).status_code == 404
    assert "leaver" not in str((await client.get(f"{WEB}/users")).json())
    events = (await client.get(f"{WEB}/security-events")).json()["items"]
    assert "leaver" not in str(events)
    remaining = [e for e in events if e["event_type"] == "user_deleted"]
    assert len(remaining) == 1
    assert remaining[0]["actor_id"] is None and remaining[0]["target_user_id"] is None
    assert remaining[0]["client_ip"] is None


async def test_self_deletion_may_take_the_public_recipes_along(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    setup = await _leaver(make_user, client, cook)
    deleted = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={
            "email": "leaver@example.com",
            "password": "cook-password-1",
            "delete_public_recipes": True,
        },
    )
    assert deleted.status_code == 204, deleted.text
    gone = await cook.get(f"{WEB}/recipes/{setup['recipes']['instance']['id']}")
    assert gone.status_code == 404


async def _delete_self(client: httpx.AsyncClient, email: str) -> None:
    deleted = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": email, "password": "cook-password-1"},
    )
    assert deleted.status_code == 204, deleted.text


def _uses(*sub_ids: str) -> list[tuple[str, list[dict[str, Any]]]]:
    return [("Dazugeben.", [{"sub_recipe_id": i, "amount": 1} for i in sub_ids])]


async def _found_household(
    founder: httpx.AsyncClient, member: httpx.AsyncClient, member_id: str
) -> None:
    founded = await founder.post(f"{WEB}/households", headers=CSRF, json={"name": "Daheim"})
    assert founded.status_code in (200, 201), founded.text
    invited = await founder.post(
        f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": member_id}
    )
    assert invited.status_code in (200, 201), invited.text
    invitation = (await member.get(f"{WEB}/households/invitations")).json()[0]
    accepted = await member.post(
        f"{WEB}/households/invitations/{invitation['id']}/accept", headers=CSRF
    )
    assert accepted.status_code == 200, accepted.text


async def test_self_deletion_hands_a_used_recipe_to_the_using_recipes_owner(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    await make_user("leaver", permissions=["write:recipes"])
    guest = await make_user("guest")
    await make_user("stranger")
    cook_id = (await cook.get(f"{WEB}/users/me")).json()["id"]
    await login(client, "leaver@example.com", "cook-password-1")
    shared: dict[str, Any] = {"visibility": "shared", "shared_user_ids": [cook_id]}
    pesto = await make_recipe(client, "Pesto", [("Mixen.", [])], **shared)
    crumbs = await make_recipe(client, "Brösel", [("Reiben.", [])], **shared)
    lone = await make_recipe(client, "Allein", [("Kochen.", [])], visibility="private")
    pasta = await make_recipe(
        cook,
        "Nudeln",
        _uses(pesto["id"], crumbs["id"]),
        visibility="shared",
        shared_user_ids=[guest["id"]],
    )
    # A recipe unpublished after another recipe linked it is a draft in use.
    unpublished = await client.post(f"{WEB}/recipes/{crumbs['id']}/unpublish", headers=CSRF)
    assert unpublished.status_code == 200, unpublished.text

    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert sorted(impact["recipes_handed_over"], key=lambda r: r["title"]) == [
        {"id": crumbs["id"], "title": "Brösel", "new_owner_name": "Cook"},
        {"id": pesto["id"], "title": "Pesto", "new_owner_name": "Cook"},
    ]
    assert impact["recipes_deleted"] == 1
    assert impact["drafts_deleted"] == 0
    await _delete_self(client, "leaver@example.com")

    owned = (await cook.get(f"{WEB}/recipes/{pesto['id']}/edit")).json()
    assert owned["owner"]["display_name"] == "Cook"
    assert owned["visibility"] == "shared"
    assert owned["shared_user_ids"] == [guest["id"]]
    draft = (await cook.get(f"{WEB}/recipes/{crumbs['id']}/edit")).json()
    assert draft["owner"]["display_name"] == "Cook" and draft["status"] == "draft"
    # Nothing in the using recipe changes.
    using = (await cook.get(f"{WEB}/recipes/{pasta['id']}/edit")).json()
    assert [i["sub_recipe_id"] for i in using["steps"][0]["ingredients"]] == [
        pesto["id"],
        crumbs["id"],
    ]
    assert (await cook.get(f"{WEB}/recipes/{lone['id']}")).status_code == 404

    await login(client, "guest@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{pesto['id']}")).status_code == 200
    detail = (await client.get(f"{WEB}/recipes/{pasta['id']}")).json()
    assert [n["sub_recipe"]["accessible"] for n in detail["needs"]] == [True, False]
    await login(client, "stranger@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{pesto['id']}")).status_code == 404


async def test_self_deletion_hands_over_to_the_longest_standing_owner(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await make_user("leaver", permissions=["write:recipes"])
    anna = await make_user("anna", permissions=["write:recipes"])
    ben = await make_user("ben", permissions=["write:recipes"])
    async with SessionLocal() as db:
        await db.execute(
            update(UserModel)
            .where(UserModel.email == "ben@example.com")
            .values(created=now_utc() - timedelta(days=365))
        )
        await db.commit()
    await login(client, "leaver@example.com", "cook-password-1")
    pesto = await make_recipe(
        client,
        "Pesto",
        [("Mixen.", [])],
        visibility="shared",
        shared_user_ids=[anna["id"], ben["id"]],
    )
    for name, title in (("anna", "Nudeln"), ("ben", "Gnocchi")):
        await login(client, f"{name}@example.com", "cook-password-1")
        await make_recipe(client, title, _uses(pesto["id"]), visibility="private")
    await login(client, "leaver@example.com", "cook-password-1")
    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert impact["recipes_handed_over"] == [
        {"id": pesto["id"], "title": "Pesto", "new_owner_name": "Ben"}
    ]
    await _delete_self(client, "leaver@example.com")

    await login(client, "ben@example.com", "cook-password-1")
    owned = (await client.get(f"{WEB}/recipes/{pesto['id']}/edit")).json()
    assert owned["owner"]["display_name"] == "Ben"
    # Anna's private recipe has one reader, Anna, who keeps the sub-recipe.
    assert owned["visibility"] == "shared"
    assert owned["shared_user_ids"] == [anna["id"]]
    await login(client, "anna@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{pesto['id']}")).status_code == 200


async def test_self_deletion_hands_over_down_the_tree_to_the_household(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    await make_user("leaver", permissions=["write:recipes"])
    anna = await make_user("anna")
    await make_user("stranger")
    cook_id = (await cook.get(f"{WEB}/users/me")).json()["id"]
    await login(client, "anna@example.com", "cook-password-1")
    await _found_household(cook, client, anna["id"])
    await login(client, "leaver@example.com", "cook-password-1")
    # The basil paste is the leaver's alone; cook only ever saw the pesto.
    basil = await make_recipe(client, "Basilikumpaste", [("Mörsern.", [])], visibility="private")
    pesto = await make_recipe(
        client,
        "Pesto",
        _uses(basil["id"]),
        visibility="shared",
        shared_user_ids=[cook_id],
    )
    pasta = await make_recipe(cook, "Nudeln", _uses(pesto["id"]), visibility="household")
    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert sorted(r["title"] for r in impact["recipes_handed_over"]) == ["Basilikumpaste", "Pesto"]
    assert impact["recipes_deleted"] == 0
    await _delete_self(client, "leaver@example.com")

    for recipe in (pesto, basil):
        owned = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
        assert owned["owner"]["display_name"] == "Cook"
        # The household of the using recipe is all it needs, nothing wider.
        assert owned["visibility"] == "household"
        assert owned["shared_user_ids"] == []
    using = (await cook.get(f"{WEB}/recipes/{pesto['id']}/edit")).json()
    assert using["steps"][0]["ingredients"][0]["sub_recipe_id"] == basil["id"]

    await login(client, "anna@example.com", "cook-password-1")
    detail = (await client.get(f"{WEB}/recipes/{pasta['id']}")).json()
    assert [n["sub_recipe"]["accessible"] for n in detail["needs"]] == [True]
    assert (await client.get(f"{WEB}/recipes/{basil['id']}")).status_code == 200
    await login(client, "stranger@example.com", "cook-password-1")
    for recipe in (pesto, basil):
        assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 404


async def test_self_deletion_lists_the_public_recipes_handed_over_when_deleting_them(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    await make_user("leaver", permissions=["write:recipes"])
    await login(client, "leaver@example.com", "cook-password-1")
    pesto = await make_recipe(client, "Pesto", [("Mixen.", [])], visibility="instance")
    pasta = await make_recipe(cook, "Nudeln", _uses(pesto["id"]), visibility="private")
    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert impact["recipes_kept_online"] == 1
    assert impact["recipes_handed_over"] == []
    assert impact["if_public_deleted"] == {
        "recipes_deleted": 0,
        "drafts_deleted": 0,
        "recipes_handed_over": [{"id": pesto["id"], "title": "Pesto", "new_owner_name": "Cook"}],
        "sub_recipes_kept_online": 0,
    }
    deleted = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={
            "email": "leaver@example.com",
            "password": "cook-password-1",
            "delete_public_recipes": True,
        },
    )
    assert deleted.status_code == 204, deleted.text

    owned = (await cook.get(f"{WEB}/recipes/{pesto['id']}/edit")).json()
    assert owned["owner"]["display_name"] == "Cook"
    # It keeps the readers it had: everyone.
    assert owned["visibility"] == "instance"
    using = (await cook.get(f"{WEB}/recipes/{pasta['id']}/edit")).json()
    assert using["steps"][0]["ingredients"][0]["sub_recipe_id"] == pesto["id"]


async def test_a_sub_recipe_only_ownerless_recipes_use_stays_without_an_owner(
    make_user: MakeUser, client: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    await make_user("leaver", permissions=["write:recipes"])
    await login(client, "leaver@example.com", "cook-password-1")
    crumbs = await make_recipe(client, "Brösel", [("Reiben.", [])], visibility="private")
    pesto = await make_recipe(client, "Pesto", _uses(crumbs["id"]), visibility="private")
    pasta = await make_recipe(client, "Nudeln", _uses(pesto["id"]), visibility="instance")
    unpublished = await client.post(f"{WEB}/recipes/{crumbs['id']}/unpublish", headers=CSRF)
    assert unpublished.status_code == 200, unpublished.text
    impact = (await client.get(f"{WEB}/users/me/deletion-impact")).json()
    assert impact["recipes_kept_online"] == 1
    assert impact["sub_recipes_kept_online"] == 2
    assert impact["recipes_deleted"] == 0 and impact["drafts_deleted"] == 0
    assert impact["if_public_deleted"] == {
        "recipes_deleted": 2,
        "drafts_deleted": 1,
        "recipes_handed_over": [],
        "sub_recipes_kept_online": 0,
    }
    await _delete_self(client, "leaver@example.com")

    kept = (await cook.get(f"{WEB}/recipes/{pesto['id']}")).json()
    assert kept["owner"] is None
    # The ownerless recipe using it is visible to everyone, so it is too.
    assert kept["visibility"] == "instance"
    # The draft below it stays a draft nobody reads, still counted in the tree.
    assert [n["sub_recipe"]["accessible"] for n in kept["needs"]] == [False]
    assert (await cook.get(f"{WEB}/recipes/{crumbs['id']}")).status_code == 404
    detail = (await cook.get(f"{WEB}/recipes/{pasta['id']}")).json()
    assert [n["sub_recipe"]["accessible"] for n in detail["needs"]] == [True]


async def test_the_system_user_cannot_delete_itself(admin: httpx.AsyncClient) -> None:
    impact = (await admin.get(f"{WEB}/users/me/deletion-impact")).json()
    assert impact["refused_reason"] == "system_user"
    refused = await admin.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": "admin@example.com", "password": "admin-password-1"},
    )
    assert refused.status_code == 403


async def test_self_deletion_confirms_with_a_passkey(
    make_user: MakeUser, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = FakeVerifier()
    monkeypatch.setattr(deps, "passkey_verifier", lambda: verifier)
    await make_user("leaver")
    await login(client, "leaver@example.com", "cook-password-1")
    options = (await client.post(f"{WEB}/users/me/passkeys/options", headers=CSRF)).json()
    registered = await client.post(
        f"{WEB}/users/me/passkeys",
        headers=CSRF,
        json={
            "challenge_token": options["challenge_token"],
            "credential": {"rawId": "cred-1", "challenge": options["options"]["challenge"]},
            "name": "Laptop",
        },
    )
    assert registered.status_code == 201, registered.text

    async def confirm(**credential: Any) -> httpx.Response:
        prompt = (await client.post("/api/v1/auth/login/passkey/options")).json()
        return await client.request(
            "DELETE",
            f"{WEB}/users/me",
            headers=CSRF,
            json={
                "email": "leaver@example.com",
                "passkey": {
                    "challenge_token": prompt["challenge_token"],
                    "credential": {
                        "rawId": "cred-1",
                        "challenge": prompt["options"]["challenge"],
                        **credential,
                    },
                },
            },
        )

    assert (await confirm(bad=True)).status_code == 403
    deleted = await confirm()
    assert deleted.status_code == 204, deleted.text


# ── Download my data ──────────────────────────────────────────────────


async def test_download_my_data_holds_every_own_record(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _nut_cake(cook)
    rid = recipe["id"]
    await grant_health_data(cook)
    await cook.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=NUTS)
    await cook.put(f"{WEB}/recipes/{rid}/favourite", headers=CSRF, json={"favourite": True})
    await cook.put(f"{WEB}/recipes/{rid}/rating", headers=CSRF, json={"stars": 5})
    await cook.put(f"{WEB}/recipes/{rid}/note", headers=CSRF, json={"text": "mehr Zimt"})
    today = now_utc().date().isoformat()
    await cook.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": rid, "cooked_on": today, "servings": 2},
    )
    await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": today, "slot": "dinner", "recipe_id": rid, "servings": 2},
    )
    shopping = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Wocheneinkauf"})
    ).json()
    await cook.post(
        f"{WEB}/shopping-lists/{shopping['id']}/items", headers=CSRF, json={"text": "Milch"}
    )
    assert (
        await cook.post(f"{WEB}/kitchen/setup", headers=CSRF, json={"equipment_ids": []})
    ).status_code in (200, 201)

    response = await cook.get(f"{WEB}/users/me/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["format"] == "cuisine-personal-data"
    assert data["profile"]["email"] == "cook@example.com"
    assert data["consents"][0]["kind"] == "health_data"
    assert data["consents"][0]["granted_at"] is not None
    assert [r["title"] for r in data["recipes"]] == ["Nusskuchen"]
    assert data["recipes"][0]["content"]["translations"]["de-AT"]["title"] == "Nusskuchen"
    assert [i["names"]["de-AT"] for i in data["ingredients"]] == ["Walnüsse"]
    assert data["favourites"] == [{"id": rid, "title": "Nusskuchen", "accessible": True}]
    assert data["ratings"][0]["stars"] == 5
    assert data["notes"][0]["text"] == "mehr Zimt"
    assert data["cook_events"][0]["cooked_on"] == today
    assert data["meal_plan"][0]["recipe"]["title"] == "Nusskuchen"
    assert data["shopping_lists"][0]["items"][0]["name"] == "Milch"
    assert data["food_restrictions"][0]["allergen"] == "nuts"
    assert data["household"] is None
    assert data["kitchen"] == {
        "household": False,
        "set_up_at": data["kitchen"]["set_up_at"],
        "equipment": [],
    }

    # Nobody else's data: another user's export knows nothing of this.
    await make_user("other")
    await login(client, "other@example.com", "cook-password-1")
    other = (await client.get(f"{WEB}/users/me/export")).json()
    assert other["recipes"] == [] and other["food_restrictions"] == []
    assert "Zimt" not in str(other)


# ── Privacy statement acknowledgements ────────────────────────────────


async def test_privacy_acknowledgement_overview(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    empty = (await admin.get(f"{WEB}/admin/legal/privacy/acknowledgements")).json()
    assert empty == {"current_version": None, "acknowledged": [], "pending": []}
    await make_user("reader")
    published = await admin.post(
        f"{WEB}/admin/legal/privacy", headers=CSRF, json={"texts": {"en-GB": "We keep little."}}
    )
    assert published.status_code == 201, published.text
    overview = (await admin.get(f"{WEB}/admin/legal/privacy/acknowledgements")).json()
    assert overview["current_version"] == 1
    assert [e["user"]["display_name"] for e in overview["acknowledged"]] == ["Test Admin"]
    assert overview["acknowledged"][0]["version"] == 1
    assert [(e["user"]["display_name"], e["version"]) for e in overview["pending"]] == [
        ("Reader", None)
    ]

    await login(other_client, "reader@example.com", "cook-password-1")
    acknowledged = await other_client.post(
        f"{WEB}/users/me/privacy/acknowledge", headers=CSRF, json={"version": 1}
    )
    assert acknowledged.status_code == 204
    refused = await other_client.get(f"{WEB}/admin/legal/privacy/acknowledgements")
    assert refused.status_code == 403
    overview = (await admin.get(f"{WEB}/admin/legal/privacy/acknowledgements")).json()
    assert overview["pending"] == []
    assert len(overview["acknowledged"]) == 2


# ── Admin recipe archive ──────────────────────────────────────────────


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 32), (200, 40, 40)).save(out, format="PNG")
    return out.getvalue()


def _rewrite_manifest(data: bytes, change: Any) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            content = source.read(info)
            if info.filename == "recipes.json":
                manifest = json.loads(content)
                change(manifest)
                content = json.dumps(manifest).encode()
            target.writestr(info.filename, content)
    return out.getvalue()


async def test_recipe_archive_round_trip(admin: httpx.AsyncClient, cook: httpx.AsyncClient) -> None:
    g = await unit_id(cook, "g")
    flour = await make_ingredient(cook, "Mehl", kcal=350)
    exotic = await make_ingredient(cook, "Drachenfrucht")
    uploaded = await cook.post(
        f"{WEB}/files", headers=CSRF, files={"file": ("cover.png", _png(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    sheets = await make_recipe(
        cook,
        "Teigblätter",
        [("Kneten.", [{"ingredient_id": flour["id"], "amount": 250, "unit_id": g}])],
        yield_amount=500,
        yield_unit_id=g,
    )
    pie = await make_recipe(
        cook,
        "Obstkuchen",
        [
            (
                f"@[Teigblätter](recipe:{sheets['id']}) mit "
                f"@[Drachenfrucht](ingredient:{exotic['id']}) belegen.",
                [
                    {"sub_recipe_id": sheets["id"], "amount": 250, "unit_id": g},
                    {"ingredient_id": exotic["id"], "amount": 2},
                ],
            )
        ],
        cover_image_id=uploaded.json()["id"],
    )

    refused = await cook.get(f"{WEB}/admin/recipes/export")
    assert refused.status_code == 403
    exported = await admin.get(f"{WEB}/admin/recipes/export", params={"recipe_id": pie["id"]})
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/vnd.cuisine.recipe+zip"
    names = zipfile.ZipFile(io.BytesIO(exported.content)).namelist()
    assert "recipes.json" in names and any(n.startswith("files/") for n in names)

    def unknown_fruit(manifest: dict[str, Any]) -> None:
        # The importing instance has no such fruit and no such unit.
        entry = manifest["catalogue"]["ingredients"][exotic["id"]]
        entry["names"] = {"de-AT": {"name": "Pitahaya", "plural_name": "Pitahayas"}}
        entry["seed_key"] = None
        manifest["catalogue"]["units"][g]["code"] = "gramm"
        manifest["catalogue"]["units"][g]["seed_key"] = "no-such-unit"

    archive = _rewrite_manifest(exported.content, unknown_fruit)
    imported = await admin.post(
        f"{WEB}/recipes/import",
        headers=CSRF,
        files={"file": ("recipes.zip", archive, "application/zip")},
    )
    assert imported.status_code == 200, imported.text
    report = imported.json()
    assert [r["title"] for r in report["recipes"]] == ["Teigblätter", "Obstkuchen"]
    assert report["created_ingredients"] == ["Pitahaya"]
    assert report["matched_ingredients"] == 1
    kinds = {(c["kind"], c["name"]) for c in report["conflicts"]}
    assert ("unit", "gramm") in kinds
    assert ("title", "Obstkuchen") in kinds and ("title", "Teigblätter") in kinds

    new_pie = report["recipes"][1]["id"]
    edit = (await admin.get(f"{WEB}/recipes/{new_pie}/edit")).json()
    assert edit["status"] == "draft"
    assert edit["cover_image_id"] not in (None, uploaded.json()["id"])
    step = edit["steps"][0]
    new_sheets = report["recipes"][0]["id"]
    assert step["ingredients"][0]["sub_recipe_id"] == new_sheets
    assert step["ingredients"][0]["unit_id"] is None
    pitahaya = step["ingredients"][1]["ingredient_id"]
    assert f"recipe:{new_sheets}" in step["translations"]["de-AT"]["text"]
    assert f"ingredient:{pitahaya}" in step["translations"]["de-AT"]["text"]
    created = (await admin.get(f"{WEB}/ingredients/{pitahaya}")).json()
    assert created["status"] == "draft" and created["name"] == "Pitahaya"
    owner = (await admin.get(f"{WEB}/recipes/{new_pie}")).json()["owner"]
    assert owner["display_name"] == (await admin.get(f"{WEB}/users/me")).json()["display_name"]

    broken = await admin.post(
        f"{WEB}/recipes/import",
        headers=CSRF,
        files={"file": ("recipes.zip", b"not a zip", "application/zip")},
    )
    assert broken.status_code == 422
