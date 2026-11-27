"""The food fact of the day on the start page: one fact about a base
ingredient, in the viewer's language, with its Wikipedia source, giving way
to the next fact once its ingredient is no longer active."""

import httpx
from sqlalchemy import update

from src.bootstrap.cookbook_seed import ensure_reference_data
from src.bootstrap.reference_data import load_reference_data
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.domain.services.food_facts import daily_candidates
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.cookbook_helpers import WEB


async def test_home_has_no_food_fact_without_the_base_ingredients(
    admin: httpx.AsyncClient,
) -> None:
    home = (await admin.get(f"{WEB}/home")).json()
    assert home["food_fact"] is None


async def test_home_shows_the_fact_of_the_day_until_its_ingredient_is_archived(
    admin: httpx.AsyncClient,
) -> None:
    await ensure_reference_data()
    facts = sorted(load_reference_data().food_facts, key=lambda f: f.key)
    expected = facts[next(daily_candidates(now_utc().date(), len(facts)))]

    shown = (await admin.get(f"{WEB}/home")).json()["food_fact"]
    assert shown["key"] == expected.key
    assert shown["text"] == expected.texts[shown["locale"]]
    assert shown["source_title"] == expected.source.title
    assert shown["source_url"].startswith(
        f"https://{expected.source.locale.split('-')[0]}.wikipedia.org/wiki/"
    )
    ingredient = (await admin.get(f"{WEB}/ingredients/{shown['ingredient_id']}")).json()
    assert ingredient["name"] == shown["ingredient_name"]

    # Base ingredients cannot be deleted through the API; an archived one
    # (deleted while restrictions pointed at it) is the case that remains.
    async with SessionLocal() as db:
        await db.execute(
            update(IngredientModel)
            .where(IngredientModel.seed_key == expected.ingredient_key)
            .values(status=IngredientStatus.ARCHIVED.value)
        )
        await db.commit()
    after = (await admin.get(f"{WEB}/home")).json()["food_fact"]
    assert after is not None
    assert after["ingredient_id"] != shown["ingredient_id"]
