"""Helpers the cookbook integration tests share: looking up seeded
resources and creating ingredients and recipes through the API."""

from typing import Any

import httpx

from tests.integration.conftest import CSRF

WEB = "/api/v1/web"


async def unit_id(client: httpx.AsyncClient, code: str) -> str:
    units = (await client.get(f"{WEB}/units")).json()
    return str(next(u["id"] for u in units if u["code"] == code))


async def tag_id(client: httpx.AsyncClient, english_name: str) -> str:
    tags = (await client.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    return str(next(t["id"] for t in tags if t["name"] == english_name))


async def make_ingredient(
    client: httpx.AsyncClient,
    name: str,
    *,
    kcal: float | None = None,
    allergens: list[str] | None = None,
    conversions: list[dict[str, Any]] | None = None,
    english: str | None = None,
    plural: str | None = None,
    english_plural: str | None = None,
) -> dict[str, Any]:
    """Creates an ingredient; the plurals default to the name plus "n" or
    "s", and an uncountable ingredient passes its name as its plural."""
    translations: dict[str, Any] = {"de-AT": {"name": name, "plural_name": plural or f"{name}n"}}
    if english:
        translations["en-GB"] = {
            "name": english,
            "plural_name": english_plural or f"{english}s",
        }
    response = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": translations,
            "nutrition": {"kcal": kcal},
            "allergens": allergens or [],
            "conversions": conversions or [],
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def recipe_payload(
    title: str,
    steps: list[tuple[str, list[dict[str, Any]]]],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "original_locale": "de-AT",
        "translations": {"de-AT": {"title": title, "description": f"{title} Beschreibung"}},
        "base_servings": 2,
        "prep_minutes": 10,
        "cook_minutes": 20,
        "steps": [
            {"translations": {"de-AT": {"text": text}}, "ingredients": ingredients}
            for text, ingredients in steps
        ],
        **extra,
    }


async def make_recipe(
    client: httpx.AsyncClient,
    title: str,
    steps: list[tuple[str, list[dict[str, Any]]]],
    *,
    publish: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    created = await client.post(
        f"{WEB}/recipes", headers=CSRF, json=recipe_payload(title, steps, **extra)
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    if publish:
        published = await client.post(f"{WEB}/recipes/{body['id']}/publish", headers=CSRF)
        assert published.status_code == 200, published.text
        body = published.json()
    return body


async def grant_health_data(client: httpx.AsyncClient) -> None:
    """Gives the signed-in user the health data consent, which entering
    food restrictions needs."""
    granted = await client.put(f"{WEB}/users/me/consents/health_data", headers=CSRF)
    assert granted.status_code == 200, granted.text
