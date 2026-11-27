"""Recipe revisions: recording on every content change, who may read them,
the snapshot's shape and names, and restoring."""

from io import BytesIO
from typing import Any

import httpx
from PIL import Image

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id


async def _create(cook: httpx.AsyncClient, title: str, steps: Any, **extra: Any) -> dict[str, Any]:
    created = await cook.post(
        f"{WEB}/recipes", headers=CSRF, json=recipe_payload(title, steps, **extra)
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def _revisions(cook: httpx.AsyncClient, recipe_id: str) -> dict[str, Any]:
    response = await cook.get(f"{WEB}/recipes/{recipe_id}/revisions")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_every_content_change_records_a_revision_but_publishing_does_not(
    cook: httpx.AsyncClient,
) -> None:
    flour = await make_ingredient(cook, "Mehl", english="flour")
    g = await unit_id(cook, "g")
    line = {"ingredient_id": flour["id"], "amount": 200, "unit_id": g}
    recipe = await _create(cook, "Kuchen", [("Rühren.", [line])])
    updated = await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json={**recipe_payload("Rührkuchen", [("Rühren.", [line])]), "revision_note": "Titel"},
    )
    assert updated.status_code == 200
    translated = await cook.put(
        f"{WEB}/recipes/{recipe['id']}/translation",
        headers=CSRF,
        json={"locale": "en-GB", "text": {"title": "Cake"}, "steps": [{"text": "Stir."}]},
    )
    assert translated.status_code == 200, translated.text
    assert (
        await cook.post(f"{WEB}/recipes/{recipe['id']}/publish", headers=CSRF)
    ).status_code == 200

    history = await _revisions(cook, recipe["id"])
    assert history["total"] == 3
    kinds = [(r["number"], r["kind"]) for r in history["items"]]
    assert kinds == [(3, "translated"), (2, "updated"), (1, "created")]
    second = history["items"][1]
    assert second["note"] == "Titel"
    assert second["created_via"] == "web"
    assert second["author"]["display_name"] == "Cook"
    assert second["restored_from"] is None

    first = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/1")).json()
    snapshot = first["snapshot"]
    assert snapshot["schema_version"] == 1
    assert snapshot["translations"]["de-AT"]["title"] == "Kuchen"
    assert "status" not in snapshot
    assert "visibility" not in snapshot
    step_line = snapshot["steps"][0]["ingredients"][0]
    assert step_line["ingredient_id"] == flour["id"]
    assert step_line["unit_id"] == g
    assert snapshot["names"]["ingredients"][flour["id"]] == {"de-AT": "Mehl", "en-GB": "flour"}
    assert set(snapshot["names"]["units"][g]) == {"de-AT", "en-GB"}


async def test_only_editors_see_the_history(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _create(cook, "Suppe", [("Kochen.", [])])
    await cook.post(f"{WEB}/recipes/{recipe['id']}/publish", headers=CSRF)
    await make_user("reader")
    await login(client, "reader@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 200
    assert (await client.get(f"{WEB}/recipes/{recipe['id']}/revisions")).status_code == 403
    missing = await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/9")
    assert missing.status_code == 404


async def test_restore_writes_old_content_as_a_new_revision_and_keeps_the_status(
    cook: httpx.AsyncClient,
) -> None:
    salt = await make_ingredient(cook, "Salz")
    pepper = await make_ingredient(cook, "Pfeffer")
    recipe = await _create(cook, "Eintopf", [("Kochen.", [{"ingredient_id": salt["id"]}])])
    await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json=recipe_payload("Eintopf scharf", [("Würzen.", [{"ingredient_id": pepper["id"]}])]),
    )
    await cook.post(f"{WEB}/recipes/{recipe['id']}/publish", headers=CSRF)

    restored = await cook.post(f"{WEB}/recipes/{recipe['id']}/revisions/1/restore", headers=CSRF)
    assert restored.status_code == 200, restored.text
    body = restored.json()
    assert body["translations"]["de-AT"]["title"] == "Eintopf"
    assert body["steps"][0]["ingredients"][0]["ingredient_id"] == salt["id"]
    assert body["status"] == "published"
    history = await _revisions(cook, recipe["id"])
    assert history["total"] == 3
    newest = history["items"][0]
    assert (newest["kind"], newest["restored_from"]) == ("restored", 1)
    # History is never rewritten.
    second = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/2")).json()
    assert second["snapshot"]["translations"]["de-AT"]["title"] == "Eintopf scharf"


async def test_restore_fails_naming_a_vanished_ingredient(cook: httpx.AsyncClient) -> None:
    gone = await make_ingredient(cook, "Liebstöckel")
    salt = await make_ingredient(cook, "Salz")
    recipe = await _create(cook, "Brühe", [("Kochen.", [{"ingredient_id": gone["id"]}])])
    await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json=recipe_payload("Brühe", [("Kochen.", [{"ingredient_id": salt["id"]}])]),
    )
    assert (await cook.delete(f"{WEB}/ingredients/{gone['id']}", headers=CSRF)).status_code == 204
    refused = await cook.post(f"{WEB}/recipes/{recipe['id']}/revisions/1/restore", headers=CSRF)
    assert refused.status_code == 409
    body = refused.json()
    assert body["code"] == "RevisionRestoreError"
    assert (body["missing_kind"], body["missing_name"]) == ("ingredient", "Liebstöckel")
    # The old revision still reads, with the name it recorded.
    old = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/1")).json()
    assert old["snapshot"]["names"]["ingredients"][gone["id"]]["de-AT"] == "Liebstöckel"


async def test_restore_drops_images_that_no_longer_exist(cook: httpx.AsyncClient) -> None:
    out = BytesIO()
    Image.new("RGB", (32, 32), (0, 0, 0)).save(out, format="PNG")
    uploaded = await cook.post(
        f"{WEB}/files", headers=CSRF, files={"file": ("c.png", out.getvalue(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    image_id = uploaded.json()["id"]
    recipe = await _create(cook, "Bild", [("Anrichten.", [])], cover_image_id=image_id)
    await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json=recipe_payload("Bild", [("Anrichten.", [])]),
    )
    first = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/1")).json()
    assert first["snapshot"]["cover_image_id"] == image_id
    assert (await cook.delete(f"{WEB}/files/{image_id}", headers=CSRF)).status_code == 204
    restored = await cook.post(f"{WEB}/recipes/{recipe['id']}/revisions/1/restore", headers=CSRF)
    assert restored.status_code == 200, restored.text
    assert restored.json()["cover_image_id"] is None
