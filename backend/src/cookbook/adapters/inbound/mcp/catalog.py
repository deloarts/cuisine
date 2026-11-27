"""
What the cookbook offers AI agents through the MCP surface. Every tool runs
the use case of the matching web route with the caller as actor, so a tool
never checks less than the button in the web app.

The draft tools create recipes as drafts and ingredients as draft
ingredients; a person reviews and publishes them in the web app. A
translation or an image can only be added to a draft. Food restrictions are
never exposed to agents.
"""

import base64
import binascii
from collections.abc import Iterable
from typing import Annotated
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_equipment
from src.cookbook.adapters.inbound.api.deps import get_manage_ingredients
from src.cookbook.adapters.inbound.api.deps import get_manage_recipes
from src.cookbook.adapters.inbound.api.deps import get_manage_resources
from src.cookbook.adapters.inbound.api.deps import get_manage_variations
from src.cookbook.adapters.inbound.api.deps import get_read_recipes
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.presenters import category_response
from src.cookbook.adapters.inbound.api.presenters import tag_response
from src.cookbook.adapters.inbound.api.presenters import unit_response
from src.cookbook.adapters.inbound.api.variation_presenter import variation_response
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ConversionCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_recipes import RecipeCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepEquipmentCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepIngredientCommand
from src.cookbook.application.use_cases.recipes.manage_variations import ManageVariations
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import EquipmentNotFoundError
from src.cookbook.domain.exceptions import IngredientFamilyNotFoundError
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidIngredientError
from src.cookbook.domain.exceptions import InvalidRecipeError
from src.cookbook.domain.exceptions import TagNotFoundError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.mentions import MentionTarget
from src.cookbook.domain.services.mentions import UnresolvedMentionError
from src.cookbook.domain.services.mentions import mentions
from src.cookbook.domain.services.mentions import resolve_named_mentions
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IngredientQuery
from src.platform.adapters.inbound.api.deps import get_manage_files
from src.platform.adapters.inbound.mcp.tools import AgentCatalog
from src.platform.adapters.inbound.mcp.tools import AgentPrompt
from src.platform.adapters.inbound.mcp.tools import AgentTool
from src.platform.adapters.inbound.mcp.tools import AgentToolContext
from src.platform.adapters.inbound.mcp.tools import DraftToolInput
from src.platform.adapters.inbound.mcp.tools import PromptArgument
from src.platform.adapters.inbound.mcp.tools import ToolInput
from src.platform.adapters.inbound.mcp.tools import ToolKind
from src.platform.adapters.inbound.mcp.tools import ToolOutput
from src.platform.adapters.inbound.mcp.tools import ref
from src.platform.application.use_cases.files.manage_files import ManageFiles
from src.platform.domain.value_objects.permission import Permission

Locale = Literal["de-AT", "en-GB"]


def _locale(ctx: AgentToolContext, locale: str | None) -> str:
    """The language a tool answers in: the one asked for, else the token
    user's UI language, as on the web surface."""
    return locale or ui_locale(ctx.actor.language.value)


async def _presenter(ctx: AgentToolContext, locale: str | None) -> tuple[Cookbook, Presenter]:
    c = await ctx.use_case(get_cookbook)
    return c, Presenter(c, await c.viewers.of(ctx.actor), _locale(ctx, locale))


# ── Read tools ───────────────────────────────────────────────────────


class SearchRecipesInput(ToolInput):
    query: str | None = Field(default=None, max_length=128, description="Words to search for.")
    tag_ids: list[str] = Field(default_factory=list, description="Tag ids that must all match.")
    include_my_drafts: bool = Field(default=False)
    locale: Locale | None = None
    limit: int = Field(default=20, ge=1, le=50)


async def search_recipes(ctx: AgentToolContext, args: SearchRecipesInput) -> ToolOutput:
    c, presenter = await _presenter(ctx, args.locale)
    read: ReadRecipes = await ctx.use_case(get_read_recipes)
    tag_ids = []
    for public_id in args.tag_ids:
        tag = await c.tags.get_by_public_id(public_id)
        tag_ids.append(tag.id if tag else -1)
    summaries, total, lookups = await read.list(
        ctx.actor,
        await read.query_for(
            ctx.actor,
            status=None if args.include_my_drafts else "published",
            search=args.query,
            tag_ids=tag_ids,
            limit=args.limit,
        ),
    )
    items = await presenter.summaries(summaries, lookups)
    return ToolOutput(
        {
            "total": total,
            "recipes": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "status": r.status,
                    "total_minutes": r.total_minutes,
                    "tags": [t.name for t in r.tags],
                    # A read-only mirror of a recipe another instance shares.
                    "from_instance": r.mirror.instance_name if r.mirror else None,
                    "source_author": r.mirror.author_name if r.mirror else None,
                }
                for r in items
            ],
        }
    )


class GetRecipeInput(ToolInput):
    recipe_id: str
    locale: Locale | None = None
    include_variations: bool = Field(
        default=False,
        description="Also list the recipe's variations you may see, each with its changes "
        "(swaps, added or removed lines, other step text, extra steps; steps numbered from 1).",
    )


async def get_recipe(ctx: AgentToolContext, args: GetRecipeInput) -> ToolOutput:
    _, presenter = await _presenter(ctx, args.locale)
    read: ReadRecipes = await ctx.use_case(get_read_recipes)
    detail = await presenter.detail(await read.view(ctx.actor, args.recipe_id))
    # The viewer's own warnings are health data about a person; agents
    # never see them.
    data = detail.model_dump(
        mode="json",
        exclude={
            "warnings",
            "has_warning",
            "unsuitable_for_guests",
            "variation_fits_guests",
            "own_note",
        },
    )
    if args.include_variations:
        variations: ManageVariations = await ctx.use_case(get_manage_variations)
        recipe, found = await variations.for_recipe(ctx.actor, args.recipe_id)
        infos = await variations.infos(ctx.actor, recipe, found)
        data["variations"] = [
            {
                "id": str(v.id),
                "name": v.name,
                "note": v.note,
                "locale": v.locale,
                "author": (
                    v.author.display_name
                    if v.author
                    else v.source_author_name
                    if v.mirrored
                    else None
                ),
                "mirrored": v.mirrored,
                "is_stale": v.is_stale,
                "rating_average": v.rating_average,
                "rating_count": v.rating_count,
                "changes": [
                    c.model_dump(mode="json", exclude={"available", "applies"})
                    for c in v.changes
                    if c.applies
                ],
            }
            for v in [
                await variation_response(presenter, variations.resolver, recipe, i) for i in infos
            ]
        ]
    return ToolOutput(data)


class LocaleInput(ToolInput):
    locale: Locale | None = None


async def list_tags(ctx: AgentToolContext, args: LocaleInput) -> ToolOutput:
    resources: ManageResources = await ctx.use_case(get_manage_resources)
    locale = _locale(ctx, args.locale)
    return ToolOutput(
        [tag_response(t, locale).model_dump(mode="json") for t in await resources.tags()]
    )


async def list_units(ctx: AgentToolContext, args: LocaleInput) -> ToolOutput:
    resources: ManageResources = await ctx.use_case(get_manage_resources)
    locale = _locale(ctx, args.locale)
    return ToolOutput(
        [unit_response(u, locale).model_dump(mode="json") for u in await resources.units()]
    )


async def list_ingredient_categories(ctx: AgentToolContext, args: LocaleInput) -> ToolOutput:
    resources: ManageResources = await ctx.use_case(get_manage_resources)
    locale = _locale(ctx, args.locale)
    return ToolOutput(
        [category_response(c, locale).model_dump(mode="json") for c in await resources.categories()]
    )


class SearchIngredientsInput(ToolInput):
    query: str = Field(min_length=1, max_length=128)
    locale: Locale | None = None
    limit: int = Field(default=20, ge=1, le=50)


async def search_ingredients(ctx: AgentToolContext, args: SearchIngredientsInput) -> ToolOutput:
    c, presenter = await _presenter(ctx, args.locale)
    manage: ManageIngredients = await ctx.use_case(get_manage_ingredients)
    found, total = await manage.find(IngredientQuery(search=args.query), limit=args.limit, offset=0)
    items = await presenter.ingredients(found, await c.lookups().load())
    return ToolOutput(
        {
            "total": total,
            "ingredients": [
                {
                    "id": str(i.id),
                    "name": i.name,
                    "plural_name": i.plural_name,
                    "status": i.status,
                    "has_nutrition": any(v is not None for v in i.nutrition.model_dump().values()),
                    "allergens": i.allergens,
                    "diet_markers": i.diet_markers,
                    "aliases": i.aliases,
                    "family": i.family.name if i.family else None,
                }
                for i in items
            ],
        }
    )


async def list_my_drafts(ctx: AgentToolContext, args: LocaleInput) -> ToolOutput:
    _, presenter = await _presenter(ctx, args.locale)
    read: ReadRecipes = await ctx.use_case(get_read_recipes)
    summaries, total, lookups = await read.list(
        ctx.actor, await read.query_for(ctx.actor, status="drafts", owner_id=ctx.actor.id, limit=50)
    )
    items = await presenter.summaries(summaries, lookups)
    return ToolOutput(
        {"total": total, "drafts": [{"id": str(r.id), "title": r.title} for r in items]}
    )


# ── Draft tools ──────────────────────────────────────────────────────


class NutritionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kcal: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    saturated_fat: float | None = Field(default=None, ge=0)
    carbohydrates: float | None = Field(default=None, ge=0)
    sugar: float | None = Field(default=None, ge=0)
    fibre: float | None = Field(default=None, ge=0)
    salt: float | None = Field(default=None, ge=0)


class ConversionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str = Field(description="A unit code such as piece or clove, or a unit id.")
    grams: float = Field(gt=0)


class IngredientNameInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    plural_name: str = Field(default="", max_length=128)


class CreateIngredientInput(DraftToolInput):
    original_locale: Locale
    names: dict[Locale, IngredientNameInput] = Field(
        description="The name per language; the original language is required."
    )
    category_id: str | None = None
    family: str | None = Field(
        default=None, description="An ingredient family by id or name, such as Tomatoes."
    )
    aliases: dict[Locale, list[str]] = Field(
        default_factory=dict,
        description="Other names per language, such as regional names; each must be free.",
    )
    nutrition_per_100g: NutritionInput = Field(default_factory=NutritionInput)
    extended_nutrition_per_100g: dict[str, Annotated[float, Field(ge=0)]] = Field(
        default_factory=dict,
        description="Optional vitamins, minerals and fatty acids per 100 g; the key names the "
        "unit. Allowed keys: " + ", ".join(EXTENDED_KEYS) + ". Leave out what you do not know.",
    )
    season_months: list[Annotated[int, Field(ge=1, le=12)]] = Field(
        default_factory=list,
        description="Months 1 to 12 when the ingredient is in season in Austria; empty when it "
        "is not seasonal.",
    )
    density_g_per_ml: float | None = Field(default=None, gt=0)
    conversions: list[ConversionInput] = Field(default_factory=list)
    allergens: list[Allergen] = Field(default_factory=list)
    diet_markers: list[DietMarker] = Field(
        default_factory=list,
        description="What the ingredient is or contains for diets: meat, poultry, pork, beef, "
        "fish, seafood, gelatin, dairy, eggs, honey, alcohol.",
    )


async def _family_id(c: Cookbook, value: str | None) -> str | None:
    if not value:
        return None
    family = await c.families.get_by_public_id(value)
    if family is None:
        wanted = value.strip().casefold()
        family = next(
            (
                f
                for f in await c.families.list_all()
                if any(t.name.casefold() == wanted for t in f.translations.values())
            ),
            None,
        )
    if family is None:
        raise IngredientFamilyNotFoundError(f"Unknown ingredient family {value!r}.")
    return str(family.public_id)


async def _unit(c: Cookbook, value: str) -> Unit:
    unit = await c.units.get_by_code(value.strip()) or await c.units.get_by_public_id(value)
    if unit is None:
        raise UnitNotFoundError(f"Unknown unit {value!r}; call list_units for the codes.")
    return unit


async def create_ingredient(ctx: AgentToolContext, args: CreateIngredientInput) -> ToolOutput:
    c = await ctx.use_case(get_cookbook)
    manage: ManageIngredients = await ctx.use_case(get_manage_ingredients)
    conversions = [
        ConversionCommand(str((await _unit(c, conv.unit)).public_id), conv.grams)
        for conv in args.conversions
    ]
    ingredient = await manage.create(
        ctx.actor,
        IngredientCommand(
            original_locale=args.original_locale,
            translations={
                k: IngredientText(name=v.name, plural_name=v.plural_name)
                for k, v in args.names.items()
            },
            category_id=args.category_id,
            family_id=await _family_id(c, args.family),
            aliases={k: list(v) for k, v in args.aliases.items()},
            nutrition=Nutrition(**args.nutrition_per_100g.model_dump()),
            extended_nutrition=dict(args.extended_nutrition_per_100g),
            season_months=list(args.season_months),
            density_g_per_ml=args.density_g_per_ml,
            conversions=conversions,
            allergens=list(args.allergens),
            diet_markers=list(args.diet_markers),
        ),
        status=IngredientStatus.DRAFT,
    )
    return ToolOutput(
        {
            "id": str(ingredient.public_id),
            "status": ingredient.status.value,
            "hints": _ingredient_translation_hint(ingredient),
        },
        created_refs=[ref("ingredient", ingredient.public_id)],
    )


def _ingredient_translation_hint(ingredient: Ingredient) -> list[str]:
    """Asks for every content language the ingredient still lacks a name in,
    so recipes using it read whole in every language."""
    missing = _missing_locales(ingredient.translations)
    if not missing:
        return []
    return [
        f"The ingredient has no {', '.join(missing)} name yet. Add it with "
        f"add_ingredient_translation (ingredient_id {ingredient.public_id})."
    ]


class IngredientTranslationInput(DraftToolInput):
    ingredient_id: str = Field(description="A draft ingredient's id.")
    locale: Locale
    name: str = Field(min_length=1, max_length=128)
    plural_name: str = Field(default="", max_length=128)
    aliases: list[Annotated[str, Field(min_length=1, max_length=128)]] | None = Field(
        default=None,
        description="Other names in this language, such as regional names; they replace the "
        "language's aliases, and leaving them out keeps them.",
    )


async def add_ingredient_translation(
    ctx: AgentToolContext, args: IngredientTranslationInput
) -> ToolOutput:
    manage: ManageIngredients = await ctx.use_case(get_manage_ingredients)
    current = await manage.get(args.ingredient_id)
    if current.status is not IngredientStatus.DRAFT:
        raise InvalidIngredientError(
            "Agents only change draft ingredients; this one is in the catalogue."
        )
    ingredient = await manage.add_translation(
        ctx.actor,
        args.ingredient_id,
        args.locale,
        IngredientText(name=args.name, plural_name=args.plural_name),
        list(args.aliases) if args.aliases is not None else None,
    )
    return ToolOutput(
        {
            "id": str(ingredient.public_id),
            "locales": sorted(ingredient.translations),
            "hints": _ingredient_translation_hint(ingredient),
        },
        created_refs=[ref("ingredient", ingredient.public_id)],
    )


class StepIngredientInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_id: str | None = Field(default=None, description="An id from search_ingredients.")
    sub_recipe_id: str | None = Field(
        default=None,
        description="A recipe id from search_recipes to use as a sub-recipe, such as homemade "
        "pasta in a lasagna; its amount is in the sub-recipe's yield unit or in its servings.",
    )
    name: str | None = Field(
        default=None,
        max_length=128,
        description="The ingredient's name when no id fits; an unknown name becomes a draft "
        "ingredient in the recipe's original language.",
    )
    amount: float | None = Field(default=None, ge=0, description="Null for 'to taste'.")
    unit: str | None = Field(default=None, description="A unit code from list_units, or null.")
    note: str = Field(default="", max_length=255, description="Such as 'finely chopped'.")


class StepEquipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_id: str | None = Field(default=None, description="An equipment id, if known.")
    name: str | None = Field(
        default=None,
        max_length=128,
        description="The item's name or a common alias, such as 'Schneebesen' or 'whisk', when "
        "no id fits; an unknown name becomes a draft item in the recipe's original language.",
    )
    count: int | None = Field(default=None, ge=1, le=100, description="Such as 2 for two bowls.")
    note: str = Field(default="", max_length=255, description="Such as '26 cm' or '200 °C fan'.")


_MARKDOWN = (
    "Plain text or the Markdown subset Cuisine renders: **bold**, *italic*, bullet "
    "(- item) and numbered (1. item) lists, and line breaks. No other Markdown or HTML."
)


class StepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        min_length=1,
        max_length=10_000,
        description=_MARKDOWN + " Mention an ingredient or equipment item of this step where "
        "the text names it: @[Zwiebeln](ingredient) or @[Topf](equipment) matches one of this "
        "step's own lines or items by its name, plural or alias, including ingredients this "
        "call creates; @[Name](ingredient:<id>), @[Name](recipe:<id>) and "
        "@[Name](equipment:<id>) name it by id. Mention nothing that is not on this step.",
    )
    duration_minutes: int | None = Field(default=None, ge=0, le=10_000)
    ingredients: list[StepIngredientInput] = Field(default_factory=list)
    equipment: list[StepEquipmentInput] = Field(
        default_factory=list, description="The equipment this step needs."
    )


class CreateRecipeDraftInput(DraftToolInput):
    original_locale: Locale = Field(description="The language the texts below are written in.")
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000, description=_MARKDOWN)
    tips: str = Field(default="", max_length=10_000, description=_MARKDOWN)
    base_servings: int = Field(default=4, ge=1, le=100)
    prep_minutes: int | None = Field(default=None, ge=0, le=10_000)
    cook_minutes: int | None = Field(default=None, ge=0, le=10_000)
    rest_minutes: int | None = Field(default=None, ge=0, le=10_000)
    difficulty: Difficulty = Difficulty.EASY
    source_url: str | None = Field(default=None, max_length=2048)
    source_name: str | None = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list, description="Tag ids or tag names.")
    steps: list[StepInput] = Field(min_length=1)
    ingredients: list[StepIngredientInput] = Field(
        default_factory=list,
        max_length=200,
        description="Optional: the recipe's whole ingredient list as the source states it, in "
        "the same shape as a step's ingredients. The recipe's list takes the larger of it and "
        "what the steps use, so list here what no step names or needs more of; leave it empty "
        "when the steps already name every ingredient with its full amount.",
    )


async def _tag(c: Cookbook, value: str) -> Tag:
    tag = await c.tags.get_by_public_id(value)
    if tag is not None:
        return tag
    wanted = value.strip().lower()
    for candidate in await c.tags.list_all():
        if any(t.name.lower() == wanted for t in candidate.translations.values()):
            return candidate
    raise TagNotFoundError(f"Unknown tag {value!r}; call list_tags for the tags.")


async def _ingredient(
    ctx: AgentToolContext,
    c: Cookbook,
    manage: ManageIngredients,
    si: StepIngredientInput,
    locale: str,
    created: list[Ingredient],
) -> Ingredient:
    if si.ingredient_id:
        found = await c.ingredients.get_by_public_id(si.ingredient_id)
        if found is None:
            raise IngredientNotFoundError(f"Unknown ingredient id {si.ingredient_id!r}.")
        return found
    if not si.name or not si.name.strip():
        raise InvalidRecipeError("Every step ingredient needs an ingredient_id or a name.")
    for earlier in created:
        if any(t.name.lower() == si.name.strip().lower() for t in earlier.translations.values()):
            return earlier
    found = await c.ingredients.find_by_name(si.name)
    if found is not None:
        return found
    if not ctx.actor.has_permission(Permission.WRITE_INGREDIENTS):
        raise IngredientNotFoundError(
            f"No ingredient is called {si.name!r}, and this token may not create ingredients."
        )
    new = await manage.create(
        ctx.actor,
        IngredientCommand(
            original_locale=locale,
            translations={locale: IngredientText(name=si.name.strip(), plural_name="")},
        ),
        status=IngredientStatus.DRAFT,
        commit=False,
    )
    created.append(new)
    return new


async def _equipment(
    c: Cookbook,
    manage: ManageEquipment,
    se: StepEquipmentInput,
    locale: str,
    created: list[Equipment],
) -> Equipment:
    if se.equipment_id:
        found = await c.equipment.get_by_public_id(se.equipment_id)
        if found is None:
            raise EquipmentNotFoundError(f"Unknown equipment id {se.equipment_id!r}.")
        return found
    if not se.name or not se.name.strip():
        raise InvalidRecipeError("Every step equipment item needs an equipment_id or a name.")
    wanted = se.name.strip().lower()
    for earlier in created:
        if any(t.name.lower() == wanted for t in earlier.translations.values()):
            return earlier
    found = await c.equipment.find_by_name(se.name)
    if found is not None:
        return found
    new = await manage.create_draft(se.name.strip(), locale)
    created.append(new)
    return new


def _mention_target(
    kind: Literal["ingredient", "equipment"], entry: Ingredient | Equipment, given: str | None
) -> MentionTarget:
    """What a named mention of this line or item may say: every name and
    plural in every language, every alias and the name the agent gave."""
    names: list[str] = [given or ""]
    for text in entry.translations.values():
        names.append(text.name)
        names.append(getattr(text, "plural_name", ""))
    names.extend(a for aliases in entry.aliases.values() for a in aliases)
    return MentionTarget(kind, str(entry.public_id), tuple(n for n in names if n))


def _draft_hints(
    args: CreateRecipeDraftInput, steps: list[StepCommand], created: list[Ingredient]
) -> list[str]:
    """Advice for the next draft, from how this one was written: the draft is
    saved either way, and an agent cannot change it afterwards."""
    hints: list[str] = []
    if args.ingredients and not any(step.ingredients for step in steps):
        hints.append(
            "No step lists the ingredients it uses; the recipe only has its overall list. "
            "Put each ingredient on the step that uses it (split an amount over steps where "
            "the source does), so cook mode shows the amounts at each step."
        )
    unmentioned = [
        number
        for number, step in enumerate(steps, start=1)
        if step.ingredients and not any(mentions(text.text) for text in step.translations.values())
    ]
    if unmentioned:
        listed = ", ".join(str(n) for n in unmentioned)
        hints.append(
            f"The text of step {listed} mentions none of its ingredients. Where the text "
            "names one of them, write it as a mention, @[Zwiebeln](ingredient), so the reader "
            "sees its amount there."
        )
    if created:
        names = ", ".join(
            f"{resolve(i.translations, None, i.original_locale)[1].name} ({i.public_id})"
            for i in created
        )
        hints.append(
            f"{names} became draft ingredients named in {args.original_locale} only, without "
            "allergens or diet markers, so the recipe claims no diet until a person checks "
            "them. Give each its name in every other language with add_ingredient_translation. "
            "Next time create such an ingredient with create_ingredient first, with its names "
            "in every language and what you know of its allergens and markers."
        )
    hints.extend(_translation_hint([args.original_locale]))
    return hints


async def create_recipe_draft(ctx: AgentToolContext, args: CreateRecipeDraftInput) -> ToolOutput:
    c = await ctx.use_case(get_cookbook)
    manage_ingredients: ManageIngredients = await ctx.use_case(get_manage_ingredients)
    manage_equipment: ManageEquipment = await ctx.use_case(get_manage_equipment)
    manage: ManageRecipes = await ctx.use_case(get_manage_recipes)
    locale = args.original_locale
    created: list[Ingredient] = []
    created_equipment: list[Equipment] = []
    steps: list[StepCommand] = []

    async def line(
        si: StepIngredientInput, targets: list[MentionTarget] | None = None
    ) -> StepIngredientCommand:
        unit = await _unit(c, si.unit) if si.unit else None
        notes: dict[str, NoteText] = {locale: NoteText(si.note)} if si.note.strip() else {}
        if si.sub_recipe_id:
            return StepIngredientCommand(
                sub_recipe_id=si.sub_recipe_id,
                amount=si.amount,
                unit_id=str(unit.public_id) if unit else None,
                notes=notes,
            )
        ingredient = await _ingredient(ctx, c, manage_ingredients, si, locale, created)
        if targets is not None:
            targets.append(_mention_target("ingredient", ingredient, si.name))
        return StepIngredientCommand(
            ingredient_id=str(ingredient.public_id),
            amount=si.amount,
            unit_id=str(unit.public_id) if unit else None,
            notes=notes,
        )

    for number, step in enumerate(args.steps, start=1):
        targets: list[MentionTarget] = []
        ingredients = [await line(si, targets) for si in step.ingredients]
        equipment = []
        for se in step.equipment:
            item = await _equipment(c, manage_equipment, se, locale, created_equipment)
            targets.append(_mention_target("equipment", item, se.name))
            equipment.append(
                StepEquipmentCommand(
                    equipment_id=str(item.public_id),
                    count=se.count,
                    notes={locale: NoteText(se.note)} if se.note.strip() else {},
                )
            )
        try:
            text = resolve_named_mentions(step.text, targets, name_key)
        except UnresolvedMentionError as e:
            raise InvalidRecipeError(
                f"Step {number}: {e} Add the {e.kind} to the step's "
                f"{'ingredients' if e.kind == 'ingredient' else 'equipment'} "
                "or write its name without the mention."
            ) from e
        steps.append(
            StepCommand(
                translations={locale: StepText(text)},
                duration_minutes=step.duration_minutes,
                ingredients=ingredients,
                equipment=equipment,
            )
        )
    recipe = await manage.create(
        ctx.actor,
        RecipeCommand(
            original_locale=locale,
            translations={locale: RecipeText(args.title, args.description, args.tips)},
            base_servings=args.base_servings,
            prep_minutes=args.prep_minutes,
            cook_minutes=args.cook_minutes,
            rest_minutes=args.rest_minutes,
            difficulty=args.difficulty,
            source_url=args.source_url,
            source_name=args.source_name,
            tag_ids=[str((await _tag(c, t)).public_id) for t in args.tags],
            steps=steps,
            ingredients=[await line(si) for si in args.ingredients],
        ),
        created_via=CreatedVia.MCP,
    )
    return ToolOutput(
        {
            "id": str(recipe.public_id),
            "status": recipe.status.value,
            "created_ingredients": [
                {
                    "id": str(i.public_id),
                    "name": resolve(i.translations, None, i.original_locale)[1].name,
                }
                for i in created
            ],
            "created_equipment": [
                {
                    "id": str(e.public_id),
                    "name": next(iter(e.translations.values())).name if e.translations else "",
                }
                for e in created_equipment
            ],
            "hints": _draft_hints(args, steps, created),
            "next": "A person reviews and publishes the draft in the Cuisine web app.",
        },
        created_refs=[
            ref("recipe", recipe.public_id),
            *(ref("ingredient", i.public_id) for i in created),
            *(ref("equipment", e.public_id) for e in created_equipment),
        ],
    )


async def _own_draft(ctx: AgentToolContext, recipe_id: str) -> Recipe:
    manage: ManageRecipes = await ctx.use_case(get_manage_recipes)
    recipe = await manage.get_editable(ctx.actor, recipe_id)
    if recipe.status is not RecipeStatus.DRAFT:
        raise InvalidRecipeError("Agents only change drafts; this recipe is published.")
    return recipe


def _missing_locales(present: Iterable[str]) -> list[str]:
    return [locale for locale in LOCALES if locale not in set(present)]


def _translation_hint(present: Iterable[str]) -> list[str]:
    """Asks for every content language the draft still lacks: Cuisine keeps
    each recipe in all of them, so every reader gets it in their own."""
    missing = _missing_locales(present)
    if not missing:
        return []
    return [
        f"The draft has no {', '.join(missing)} text yet. Add it with add_recipe_translation "
        "(title, description, tips, every step and its notes), so every reader gets the "
        "recipe in their own language."
    ]


async def _translated_step_texts(c: Cookbook, recipe: Recipe, texts: list[str]) -> list[str]:
    """The translated step texts with their named mentions turned into
    mentions by id, matched against each step's stored lines and items."""
    ingredient_ids = {si.ingredient_id for st in recipe.steps for si in st.ingredients}
    equipment_ids = {se.equipment_id for st in recipe.steps for se in st.equipment}
    ingredients = {
        i.id: i for i in await c.ingredients.get_many([i for i in ingredient_ids if i is not None])
    }
    equipment = {e.id: e for e in await c.equipment.get_many(list(equipment_ids))}
    result: list[str] = []
    for number, text in enumerate(texts, start=1):
        step = recipe.steps[number - 1] if number <= len(recipe.steps) else None
        targets: list[MentionTarget] = []
        if step is not None:
            targets.extend(
                _mention_target("ingredient", ingredients[si.ingredient_id], None)
                for si in step.ingredients
                if si.ingredient_id in ingredients
            )
            targets.extend(
                _mention_target("equipment", equipment[se.equipment_id], None)
                for se in step.equipment
                if se.equipment_id in equipment
            )
        try:
            result.append(resolve_named_mentions(text, targets, name_key))
        except UnresolvedMentionError as e:
            raise InvalidRecipeError(
                f"Step {number}: {e} Mention only this step's own lines, by a name they carry "
                "in any language, or write the name without the mention."
            ) from e
    return result


class AttachImageInput(DraftToolInput):
    recipe_id: str
    image_base64: str = Field(description="A JPEG, PNG, WebP or GIF image, base64 encoded.")
    file_name: str = Field(default="image.jpg", max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"] = "image/jpeg"
    step_number: int | None = Field(
        default=None, ge=1, description="Attach to this step (1-based); omit for the cover."
    )


async def attach_recipe_image(ctx: AgentToolContext, args: AttachImageInput) -> ToolOutput:
    await _own_draft(ctx, args.recipe_id)
    try:
        data = base64.b64decode(args.image_base64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise InvalidRecipeError("The image is not valid base64.") from e
    files: ManageFiles = await ctx.use_case(get_manage_files)
    stored = await files.upload(
        ctx.actor, data=data, file_name=args.file_name, content_type=args.content_type
    )
    manage: ManageRecipes = await ctx.use_case(get_manage_recipes)
    await manage.set_image(
        ctx.actor,
        args.recipe_id,
        str(stored.public_id),
        args.step_number - 1 if args.step_number is not None else None,
        via=CreatedVia.MCP,
    )
    return ToolOutput(
        {"image_id": str(stored.public_id)}, created_refs=[ref("file", stored.public_id)]
    )


class TranslationInput(DraftToolInput):
    recipe_id: str
    locale: Locale
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)
    tips: str = Field(default="", max_length=10_000)
    steps: list[str] = Field(description="Each step's text in this language, in order.")
    notes: list[list[str]] | None = Field(
        default=None, description="Per step, each step ingredient's note in this language."
    )
    ingredient_notes: list[str] | None = Field(
        default=None,
        description="Each note of the recipe's own ingredient list in this language, in order.",
    )


async def add_recipe_translation(ctx: AgentToolContext, args: TranslationInput) -> ToolOutput:
    draft = await _own_draft(ctx, args.recipe_id)
    c = await ctx.use_case(get_cookbook)
    texts = await _translated_step_texts(c, draft, args.steps)
    manage: ManageRecipes = await ctx.use_case(get_manage_recipes)
    recipe = await manage.add_translation(
        ctx.actor,
        args.recipe_id,
        args.locale,
        RecipeText(args.title, args.description, args.tips),
        [StepText(s) for s in texts],
        [[NoteText(n) for n in step] for step in args.notes] if args.notes else None,
        [NoteText(n) for n in args.ingredient_notes] if args.ingredient_notes is not None else None,
        via=CreatedVia.MCP,
    )
    return ToolOutput(
        {
            "id": str(recipe.public_id),
            "locales": sorted(recipe.translations),
            "hints": _translation_hint(recipe.translations),
        },
        created_refs=[ref("recipe", recipe.public_id)],
    )


def _import_prompt(arguments: Any) -> str:
    source = arguments.get("source", "")
    return (
        f"Import this recipe into Cuisine as a draft: {source}\n\n"
        "Read the source yourself. Call list_tags and list_units, look up every ingredient "
        "with search_ingredients, then call create_recipe_draft once with all steps and the "
        "ingredients each step uses, in the source's language. Put each ingredient on the step "
        "that uses it, split an amount where the source splits it (half of the wine), and "
        "mention the ingredient in the step text where it is named, as @[Zwiebeln](ingredient). "
        "List an ingredient in the recipe's own ingredients only when no step uses it. If the "
        "source has a photo, attach it with attach_recipe_image. Then translate the draft into "
        "every other language Cuisine keeps (de-AT, en-GB) with add_recipe_translation: title, "
        "description, tips, every step and its notes. Name every ingredient the draft created in "
        "every language with add_ingredient_translation. Tell me the draft's id and any hints "
        "from the answers at the end."
    )


COOKBOOK_AGENT_CATALOG = AgentCatalog(
    tools=(
        AgentTool(
            name="search_recipes",
            title="Search recipes",
            description="Finds published recipes (and optionally your drafts) by words and tags.",
            input_model=SearchRecipesInput,
            handler=search_recipes,
        ),
        AgentTool(
            name="get_recipe",
            title="Read a recipe",
            description="One recipe with steps, the ingredients of each step, the ingredient "
            "list, nutrition and allergens, and optionally its variations.",
            input_model=GetRecipeInput,
            handler=get_recipe,
        ),
        AgentTool(
            name="list_tags",
            title="List tags",
            description="Every tag (meal, cuisine, occasion, other) with its id.",
            input_model=LocaleInput,
            handler=list_tags,
        ),
        AgentTool(
            name="list_units",
            title="List units",
            description="Every unit with its code (g, ml, tbsp, piece, ...) and id.",
            input_model=LocaleInput,
            handler=list_units,
        ),
        AgentTool(
            name="list_ingredient_categories",
            title="List ingredient categories",
            description="The supermarket aisles ingredients are grouped by.",
            input_model=LocaleInput,
            handler=list_ingredient_categories,
        ),
        AgentTool(
            name="search_ingredients",
            title="Search ingredients",
            description="Finds catalogue ingredients by name in any language.",
            input_model=SearchIngredientsInput,
            handler=search_ingredients,
        ),
        AgentTool(
            name="list_my_drafts",
            title="List my recipe drafts",
            description="Your recipe drafts that wait for review.",
            input_model=LocaleInput,
            handler=list_my_drafts,
            requires=(Permission.WRITE_RECIPES,),
        ),
        AgentTool(
            name="create_ingredient",
            title="Create an ingredient",
            description="Creates a draft ingredient with names, nutrition per 100 g, unit "
            "conversions and allergens. Give its name in every language (de-AT and en-GB).",
            input_model=CreateIngredientInput,
            handler=create_ingredient,
            kind=ToolKind.DRAFT,
            requires=(Permission.WRITE_INGREDIENTS,),
        ),
        AgentTool(
            name="add_ingredient_translation",
            title="Translate a draft ingredient",
            description="Adds or replaces the name, plural and optionally the aliases of a "
            "draft ingredient in one language, such as one create_recipe_draft created from a "
            "name. Call it for every language the ingredient lacks, so it is named in all of "
            "de-AT and en-GB. Catalogue ingredients are not changed by agents.",
            input_model=IngredientTranslationInput,
            handler=add_ingredient_translation,
            kind=ToolKind.DRAFT,
            requires=(Permission.WRITE_INGREDIENTS,),
        ),
        AgentTool(
            name="create_recipe_draft",
            title="Create a recipe draft",
            description="Creates a whole recipe as a draft: texts, tags, steps with the "
            "ingredients each step uses and optionally the recipe's own ingredient list. "
            "Put every ingredient on the step that uses it, splitting an amount over steps "
            "where the source does, and mention it where the step text names it: a step "
            '{"text": "@[Zwiebeln](ingredient) in @[Butter](ingredient) anschwitzen.", '
            '"ingredients": [{"name": "Zwiebel", "amount": 2, "unit": "piece"}, '
            '{"ingredient_id": "<id>", "amount": 20, "unit": "g"}]}. '
            "Unknown ingredient names become draft ingredients. Write it in the source's "
            "language, then add every other language Cuisine keeps (de-AT, en-GB) with "
            "add_recipe_translation. The answer's hints say what is still missing.",
            input_model=CreateRecipeDraftInput,
            handler=create_recipe_draft,
            kind=ToolKind.DRAFT,
            requires=(Permission.WRITE_RECIPES,),
        ),
        AgentTool(
            name="attach_recipe_image",
            title="Attach an image to a draft",
            description="Uploads an image as the cover or a step image of one of your drafts.",
            input_model=AttachImageInput,
            handler=attach_recipe_image,
            kind=ToolKind.DRAFT,
            requires=(Permission.WRITE_RECIPES,),
        ),
        AgentTool(
            name="add_recipe_translation",
            title="Translate a draft",
            description="Adds or replaces one language of one of your drafts: title, "
            "description, tips, every step's text in order and the notes. Call it for every "
            "language the draft lacks, so it exists in all of de-AT and en-GB; step texts may "
            "mention the step's lines by name in this language, as @[onions](ingredient).",
            input_model=TranslationInput,
            handler=add_recipe_translation,
            kind=ToolKind.DRAFT,
            requires=(Permission.WRITE_RECIPES,),
        ),
    ),
    prompts=(
        AgentPrompt(
            name="import_recipe",
            title="Import a recipe",
            description="Imports a recipe from a website or a PDF as a draft.",
            arguments=(PromptArgument("source", "The URL or file of the recipe."),),
            render=_import_prompt,
        ),
    ),
)
