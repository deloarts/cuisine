"""
Builds the cookbook's response schemas. The API exposes public ids only and
text in the viewer's language, so every internal id is translated here and
every translatable text is resolved with the language fallback.

One `Presenter` serves one request; it looks up the people and files it
needs in one query per kind.
"""

from collections.abc import Iterable
from collections.abc import Mapping
from urllib.parse import quote
from uuid import UUID

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.schemas.common_schema import CategoryRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import EquipmentRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import FamilyRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import NutritionSchema
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import SubRecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import TagRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import UnitRef
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import CookEventResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import FoodFactResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import FoodRestrictionResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import MealPlanEntryResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingItemResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListNoteResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import ShoppingListSummaryResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import VariationRef
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import EquipmentResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import ConversionResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import FoodMatchResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientDetailResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientListItem
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientTextSchema
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import BasedOnRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import EquipmentNeed
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import ExtendedNutrientAmount
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import IngredientAmount
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import MirrorPlainEquipment
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import MirrorPlainLine
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import MirrorSourceRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import MirrorUnlinkedSubRecipe
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import MirrorView
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import NoteTextSchema
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import NutritionView
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import OwnRating
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import PeerRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeDetailResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeEditResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeSummaryResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeTextSchema
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepEdit
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepEquipmentEdit
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepEquipmentView
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepImageResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepIngredientEdit
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepTextSchema
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepView
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import SubRecipeNeed
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import WarningView
from src.cookbook.adapters.inbound.api.schemas.resource_schema import CategoryResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import FamilyResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import NameTextSchema
from src.cookbook.adapters.inbound.api.schemas.resource_schema import TagResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import UnitResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import UnitTextSchema
from src.cookbook.application.dto.views import Lookups
from src.cookbook.application.dto.views import RecipeSummary
from src.cookbook.application.dto.views import RecipeView
from src.cookbook.application.dto.views import ShoppingListView
from src.cookbook.application.dto.views import StepImage
from src.cookbook.application.services.mirror_facts import MirrorInfo
from src.cookbook.application.use_cases.cooking.food_facts import DailyFoodFact
from src.cookbook.domain.entities.cooking import CookEvent
from src.cookbook.domain.entities.cooking import MealPlanEntry
from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.cooking import ShoppingListNote
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.diet_rules import unconfirmed
from src.cookbook.domain.services.equipment_rules import needed_equipment
from src.cookbook.domain.services.markdown import plain_text
from src.cookbook.domain.services.recipe_rules import VisibilitySwitches
from src.cookbook.domain.services.recipe_rules import can_delete_recipe
from src.cookbook.domain.services.recipe_rules import can_edit_ingredient
from src.cookbook.domain.services.recipe_rules import can_manage_co_editors
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.shopping_modes import deletes_on
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import MealPlanScope
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import BY_KEY as EXTENDED_BY_KEY
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.nutrition_lookup import FoodMatch
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository

# The fallback when a record has no translations, which only bad data can
# cause; the original locale is always required.
_UNNAMED = "?"


def nutrition(value: Nutrition) -> NutritionSchema:
    return NutritionSchema(
        kcal=value.kcal,
        protein=value.protein,
        fat=value.fat,
        saturated_fat=value.saturated_fat,
        carbohydrates=value.carbohydrates,
        sugar=value.sugar,
        fibre=value.fibre,
        salt=value.salt,
    )


def _name(translations: dict[str, NameText], locale: str) -> str:
    if not translations:
        return _UNNAMED
    return resolve(translations, locale, next(iter(sorted(translations))))[1].name


def unit_ref(unit: Unit, locale: str) -> UnitRef:
    if unit.translations:
        _, text = resolve(unit.translations, locale, next(iter(sorted(unit.translations))))
        name, plural, abbreviation = text.name, text.plural_name, text.abbreviation
    else:
        name = plural = abbreviation = unit.code
    return UnitRef(
        id=unit.public_id,
        code=unit.code,
        kind=unit.kind.value,
        name=name,
        plural_name=plural or name,
        abbreviation=abbreviation or unit.code,
    )


def unit_response(unit: Unit, locale: str) -> UnitResponse:
    ref = unit_ref(unit, locale)
    return UnitResponse(
        id=unit.public_id,
        seeded=unit.seed_key is not None,
        code=unit.code,
        kind=unit.kind.value,
        to_base=unit.to_base,
        sort_order=unit.sort_order,
        name=ref.name,
        plural_name=ref.plural_name,
        abbreviation=ref.abbreviation,
        translations={
            k: UnitTextSchema(name=v.name, plural_name=v.plural_name, abbreviation=v.abbreviation)
            for k, v in unit.translations.items()
        },
    )


def tag_ref(tag: Tag, locale: str) -> TagRef:
    return TagRef(
        id=tag.public_id, kind=tag.kind.value, name=_name(tag.translations, locale), color=tag.color
    )


def tag_response(tag: Tag, locale: str) -> TagResponse:
    return TagResponse(
        id=tag.public_id,
        seeded=tag.seed_key is not None,
        kind=tag.kind.value,
        color=tag.color,
        name=_name(tag.translations, locale),
        translations={k: NameTextSchema(name=v.name) for k, v in tag.translations.items()},
    )


def category_ref(category: IngredientCategory, locale: str) -> CategoryRef:
    return CategoryRef(
        id=category.public_id,
        name=_name(category.translations, locale),
        sort_order=category.sort_order,
    )


def equipment_ref(item: Equipment, locale: str) -> EquipmentRef:
    return EquipmentRef(
        id=item.public_id,
        name=_name(item.translations, locale),
        kind=item.kind.value,
        icon=item.icon,
    )


def equipment_response(item: Equipment, locale: str) -> EquipmentResponse:
    served = (
        resolve(item.translations, locale, next(iter(sorted(item.translations))))[0]
        if item.translations
        else locale
    )
    return EquipmentResponse(
        id=item.public_id,
        name=_name(item.translations, locale),
        locale=served,
        available_locales=sorted(item.translations),
        kind=item.kind.value,
        icon=item.icon,
        basic=item.basic,
        status=item.status.value,
        seeded=item.seed_key is not None,
        aliases={k: list(v) for k, v in item.aliases.items()},
        translations={k: NameTextSchema(name=v.name) for k, v in item.translations.items()},
        changed=item.changed,
    )


def family_ref(family: IngredientFamily, locale: str) -> FamilyRef:
    return FamilyRef(id=family.public_id, name=_name(family.translations, locale))


def family_response(family: IngredientFamily, locale: str) -> FamilyResponse:
    return FamilyResponse(
        id=family.public_id,
        seeded=family.seed_key is not None,
        name=_name(family.translations, locale),
        translations={k: NameTextSchema(name=v.name) for k, v in family.translations.items()},
    )


def category_response(category: IngredientCategory, locale: str) -> CategoryResponse:
    return CategoryResponse(
        id=category.public_id,
        seeded=category.seed_key is not None,
        sort_order=category.sort_order,
        name=_name(category.translations, locale),
        translations={k: NameTextSchema(name=v.name) for k, v in category.translations.items()},
    )


def name_amount(amount: float | None, unit: Unit | None) -> float | None:
    """The amount an ingredient's name agrees with on one line. A bare count
    and a count of pieces take the plural ("2 onions", "6 Stk. Karotten"), a
    weight or volume takes it too ("450 g carrots", "450 g Karotten"), and
    other units keep the ingredient singular ("2 cloves garlic"). Uncountable
    ingredients carry the same plural as singular, so "150 g Butter" stays."""
    if amount is None or unit is None or unit.code == "piece":
        return amount
    if unit.kind in (UnitKind.MASS, UnitKind.VOLUME):
        return 2
    return 1


def ingredient_name(ingredient: Ingredient | None, locale: str, amount: float | None = 1) -> str:
    if ingredient is None or not ingredient.translations:
        return _UNNAMED
    _, text = resolve(ingredient.translations, locale, ingredient.original_locale)
    plural = amount is not None and amount != 1 and amount > 1
    return (text.plural_name or text.name) if plural else text.name


def wikipedia_url(locale: str, title: str) -> str:
    """The article's address in the Wikipedia edition of a content locale."""
    edition = locale.split("-", 1)[0]
    return f"https://{edition}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='')}"


def food_fact(daily: DailyFoodFact, locale: str) -> FoodFactResponse:
    fact = daily.fact
    served, text = resolve(fact.texts, locale, fact.source.locale)
    return FoodFactResponse(
        key=fact.key,
        text=text,
        locale=served,
        ingredient_id=daily.ingredient.public_id,
        ingredient_name=ingredient_name(daily.ingredient, locale),
        source_title=fact.source.title,
        source_url=wikipedia_url(fact.source.locale, fact.source.title),
    )


def food_match(match: FoodMatch) -> FoodMatchResponse:
    return FoodMatchResponse(
        fdc_id=match.fdc_id,
        description=match.description,
        data_type=match.data_type,
        brand=match.brand,
        nutrition=nutrition(match.nutrition),
        extended_nutrition=dict(match.extended_nutrition),
    )


def _uuid_or_none(value: str | None) -> UUID | None:
    return UUID(value) if value else None


async def person_ref(files: IStoredFileRepository, user: User | None) -> PersonRef | None:
    """The name and avatar of a signed-in user's fellow member."""
    if user is None:
        return None
    avatar = None
    if user.avatar_file_id is not None:
        avatar = (await files.public_ids([user.avatar_file_id])).get(user.avatar_file_id)
    return PersonRef(id=user.public_id, display_name=user.display_name, avatar_id=avatar)


class Presenter:
    def __init__(self, c: Cookbook, viewer: Viewer, locale: str) -> None:
        self._c = c
        self.viewer = viewer
        self.locale = locale
        self._people: dict[int, PersonRef | None] = {}
        self._files: dict[int, UUID] = {}
        self._shopping: ShoppingSettings | None = None
        self._switches: VisibilitySwitches | None = None

    @property
    def cookbook(self) -> Cookbook:
        """The request's repositories, for presenters built on this one."""
        return self._c

    # ── Lookups ───────────────────────────────────────────────────────

    async def people(self, ids: Iterable[int | None]) -> dict[int, PersonRef | None]:
        for user_id in {i for i in ids if i is not None} - set(self._people):
            user = await self._c.platform.users.get(user_id)
            self._people[user_id] = await person_ref(self._c.platform.files, user)
        return self._people

    async def person(self, user_id: int | None) -> PersonRef | None:
        if user_id is None:
            return None
        return (await self.people([user_id])).get(user_id)

    async def files(self, ids: Iterable[int | None]) -> dict[int, UUID]:
        wanted = [i for i in ids if i is not None and i not in self._files]
        if wanted:
            self._files.update(await self._c.platform.files.public_ids(wanted))
        return self._files

    def _file(self, file_id: int | None) -> UUID | None:
        return self._files.get(file_id) if file_id is not None else None

    # ── Ingredients ───────────────────────────────────────────────────

    async def ingredients(
        self, items: list[Ingredient], lookups: Lookups
    ) -> list[IngredientResponse]:
        people = await self.people(i.owner_id for i in items)
        return [self._ingredient(i, lookups, people) for i in items]

    async def ingredient_list(
        self, items: list[Ingredient], lookups: Lookups, usage: Mapping[int, int]
    ) -> list[IngredientListItem]:
        """The rows of the ingredient list, each with its usage count."""
        people = await self.people(i.owner_id for i in items)
        rows = []
        for i in items:
            row = self._ingredient(
                i, lookups, people, IngredientListItem, usage_count=usage.get(i.id, 0)
            )
            assert isinstance(row, IngredientListItem)
            rows.append(row)
        return rows

    def _ingredient(
        self,
        ingredient: Ingredient,
        lookups: Lookups,
        people: dict[int, PersonRef | None],
        cls: type[IngredientResponse] = IngredientResponse,
        **extra: object,
    ) -> IngredientResponse:
        locale, text = (
            resolve(ingredient.translations, self.locale, ingredient.original_locale)
            if ingredient.translations
            else (ingredient.original_locale, None)
        )
        category = lookups.categories.get(ingredient.category_id or 0)
        family = lookups.families.get(ingredient.family_id or 0)
        conversions = []
        for c in ingredient.conversions:
            unit = lookups.units.get(c.unit_id)
            if unit is not None:
                ref = unit_ref(unit, self.locale)
                conversions.append(
                    ConversionResponse(
                        unit_id=unit.public_id,
                        unit_code=unit.code,
                        unit_name=ref.name,
                        grams=c.grams,
                    )
                )
        return cls(
            id=ingredient.public_id,
            name=text.name if text else _UNNAMED,
            plural_name=(text.plural_name or text.name) if text else _UNNAMED,
            locale=locale,
            original_locale=ingredient.original_locale,
            available_locales=sorted(ingredient.translations),
            category=category_ref(category, self.locale) if category else None,
            family=family_ref(family, self.locale) if family else None,
            aliases={k: list(v) for k, v in ingredient.aliases.items()},
            nutrition=nutrition(ingredient.nutrition),
            extended_nutrition=dict(ingredient.extended_nutrition),
            season_months=list(ingredient.season_months),
            density_g_per_ml=ingredient.density_g_per_ml,
            conversions=conversions,
            allergens=[a.value for a in ingredient.allergens],
            diet_markers=[m.value for m in ingredient.diet_markers],
            status=ingredient.status.value,
            nutrition_source=ingredient.nutrition_source.value,
            usda_fdc_id=ingredient.usda_fdc_id,
            owner=people.get(ingredient.owner_id) if ingredient.owner_id else None,
            can_edit=can_edit_ingredient(self.viewer.user, ingredient),
            changed=ingredient.changed,
            **extra,
        )

    async def ingredient_detail(
        self, ingredient: Ingredient, lookups: Lookups, recipe_count: int
    ) -> IngredientDetailResponse:
        people = await self.people([ingredient.owner_id])
        response = self._ingredient(
            ingredient,
            lookups,
            people,
            IngredientDetailResponse,
            translations={
                k: IngredientTextSchema(name=v.name, plural_name=v.plural_name)
                for k, v in ingredient.translations.items()
            },
            recipe_count=recipe_count,
        )
        assert isinstance(response, IngredientDetailResponse)
        return response

    # ── Recipes ───────────────────────────────────────────────────────

    def recipe_ref(self, recipe: Recipe) -> RecipeRef:
        _, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        return RecipeRef(
            id=recipe.public_id,
            title=text.title,
            cover_image_id=self._file(recipe.cover_file_id),
            status=recipe.status.value,
        )

    async def recipe_refs(self, recipes: Iterable[Recipe]) -> dict[int, RecipeRef]:
        """References to the recipes the viewer may see; a hidden recipe
        gets none, so a plan entry or a shopping item loses its link."""
        found = [r for r in recipes if can_view_recipe(self.viewer, r)]
        await self.files(r.cover_file_id for r in found)
        return {r.id: self.recipe_ref(r) for r in found}

    async def step_images(self, images: list[StepImage]) -> list[StepImageResponse]:
        await self.files([*(i.file_id for i in images), *(i.recipe.cover_file_id for i in images)])
        out: list[StepImageResponse] = []
        for image in images:
            recipe = image.recipe
            step = recipe.steps[image.step_index]
            text = (
                resolve(step.translations, self.locale, recipe.original_locale)[1].text
                if step.translations
                else ""
            )
            file = self._file(image.file_id)
            if file is None:
                continue
            out.append(
                StepImageResponse(
                    image_id=file,
                    recipe=self.recipe_ref(recipe),
                    step_number=image.step_index + 1,
                    step_text=plain_text(text),
                    matches=image.matches,
                )
            )
        return out

    async def switches(self) -> VisibilitySwitches:
        """Whether the instance allows public recipes and whether peering is
        on, read once per request."""
        if self._switches is None:
            settings = self._c.platform.settings
            self._switches = VisibilitySwitches(
                public_allowed=(await settings.get_privacy()).allow_public_recipes,
                peering=(await settings.get_features()).peering,
            )
        return self._switches

    def _summary_fields(
        self,
        summary: RecipeSummary,
        lookups: Lookups,
        people: dict[int, PersonRef | None],
        switches: VisibilitySwitches,
    ) -> dict[str, object]:
        recipe = summary.recipe
        locale, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        return {
            "id": recipe.public_id,
            "title": text.title,
            "description": text.description,
            "description_text": plain_text(text.description),
            "locale": locale,
            "original_locale": recipe.original_locale,
            "available_locales": sorted(recipe.translations),
            "status": recipe.status.value,
            "visibility": recipe.visibility.value,
            "effective_visibility": switches.effective(recipe.visibility).value,
            "cover_image_id": self._file(recipe.cover_file_id),
            "base_servings": recipe.base_servings,
            "prep_minutes": recipe.prep_minutes,
            "cook_minutes": recipe.cook_minutes,
            "rest_minutes": recipe.rest_minutes,
            "total_minutes": recipe.total_minutes,
            "difficulty": recipe.difficulty.value,
            "tags": [
                tag_ref(lookups.tags[t], self.locale) for t in recipe.tag_ids if t in lookups.tags
            ],
            "allergens": [a.value for a in summary.allergens],
            "diets": [d.value for d in summary.diets],
            "unsuitable_for_guests": summary.unsuitable_for_guests,
            "season_months": list(summary.season_months),
            "in_season": summary.in_season,
            "missing_equipment": (
                [
                    equipment_ref(lookups.equipment[e], self.locale)
                    for e in summary.missing_equipment_ids
                    if e in lookups.equipment
                ]
                if summary.missing_equipment_ids is not None
                else None
            ),
            "kitchen_ready": (
                not summary.missing_equipment_ids
                if summary.missing_equipment_ids is not None
                else None
            ),
            "variation_count": summary.variation_count,
            "variation_fits_guests": summary.variation_fits_guests,
            "variation_fits_diets": summary.variation_fits_diets,
            "rating_average": summary.rating_average,
            "rating_count": summary.rating_count,
            "is_favourite": summary.is_favourite,
            "has_warning": summary.has_warning,
            "can_edit": summary.can_edit,
            "owner": people.get(recipe.owner_id) if recipe.owner_id else None,
            "created_via": recipe.created_via.value,
            "last_cooked": summary.last_cooked,
            "created": recipe.created,
            "changed": recipe.changed,
            "mirror": (
                MirrorSourceRef(
                    instance_name=summary.mirror_instance,
                    author_name=summary.mirror_author,
                    author_avatar_id=_uuid_or_none(summary.mirror_author_avatar),
                )
                if summary.mirror_instance is not None
                else None
            ),
            "peer_capped": recipe.peer_capped or recipe.is_mirror,
        }

    async def summaries(
        self, summaries: list[RecipeSummary], lookups: Lookups
    ) -> list[RecipeSummaryResponse]:
        people = await self.people(s.recipe.owner_id for s in summaries)
        await self.files(s.recipe.cover_file_id for s in summaries)
        switches = await self.switches()
        return [
            RecipeSummaryResponse(**self._summary_fields(s, lookups, people, switches))
            for s in summaries
        ]

    def sub_ref(self, recipe: Recipe | None) -> SubRecipeRef:
        """A sub-recipe as the viewer may see it: with link and title, or as
        an anonymous placeholder."""
        if recipe is None or not can_view_recipe(self.viewer, recipe):
            return SubRecipeRef(
                id=None, title=None, accessible=False, total_minutes=None, cover_image_id=None
            )
        _, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        return SubRecipeRef(
            id=recipe.public_id,
            title=text.title,
            accessible=True,
            total_minutes=recipe.total_minutes,
            cover_image_id=self._file(recipe.cover_file_id),
        )

    async def based_on(self, recipe: Recipe) -> BasedOnRef | None:
        """The original a copy was made from, as the viewer may see it."""
        if recipe.based_on_recipe_id is None:
            return None
        original = await self._c.recipes.get(recipe.based_on_recipe_id)
        if original is None:
            return None
        await self.files([original.cover_file_id])
        ref = self.sub_ref(original)
        return BasedOnRef(
            recipe=ref, owner=await self.person(original.owner_id) if ref.accessible else None
        )

    def _sub_amount(
        self,
        sub_recipe_id: int,
        amount: float | None,
        unit_id: int | None,
        lookups: Lookups,
        note: str = "",
        *,
        line_id: UUID | None = None,
    ) -> IngredientAmount:
        ref = self.sub_ref(lookups.recipes.get(sub_recipe_id))
        unit = lookups.units.get(unit_id) if unit_id is not None else None
        return IngredientAmount(
            ingredient_id=None,
            sub_recipe=ref,
            name=ref.title or "",
            amount=round(amount, 3) if amount is not None else None,
            unit=unit_ref(unit, self.locale) if unit else None,
            note=note,
            line_id=line_id,
        )

    def _amount(
        self,
        ingredient_id: int,
        amount: float | None,
        unit_id: int | None,
        lookups: Lookups,
        note: str = "",
        *,
        line_id: UUID | None = None,
    ) -> IngredientAmount:
        ingredient = lookups.ingredients.get(ingredient_id)
        unit = lookups.units.get(unit_id) if unit_id is not None else None
        category = (
            lookups.categories.get(ingredient.category_id)
            if ingredient and ingredient.category_id
            else None
        )
        return IngredientAmount(
            ingredient_id=ingredient.public_id if ingredient else UUID(int=0),
            name=ingredient_name(ingredient, self.locale, name_amount(amount, unit)),
            amount=round(amount, 3) if amount is not None else None,
            unit=unit_ref(unit, self.locale) if unit else None,
            note=note,
            category_id=category.public_id if category else None,
            line_id=line_id,
        )

    def _note(self, si: StepIngredient, original: str) -> str:
        if not si.translations:
            return ""
        return resolve(si.translations, self.locale, original)[1].note

    async def detail(self, view: RecipeView) -> RecipeDetailResponse:
        recipe, derived, lookups = view.recipe, view.derived, view.lookups
        people = await self.people([recipe.owner_id])
        await self.files(
            [
                recipe.cover_file_id,
                *(s.image_file_id for s in recipe.steps),
                *(r.cover_file_id for r in lookups.recipes.values()),
            ]
        )
        summary = RecipeSummary(
            recipe=recipe,
            allergens=derived.allergens,
            rating_average=view.rating_average,
            rating_count=view.rating_count,
            is_favourite=view.is_favourite,
            has_warning=bool(view.warnings),
            can_edit=view.can_edit,
            last_cooked=view.last_cooked,
            diets=derived.diets,
            unsuitable_for_guests=view.unsuitable_for_guests,
            season_months=view.season_months,
            in_season=view.in_season,
            missing_equipment_ids=view.missing_equipment_ids,
            variation_count=view.variation_count,
            mirror_instance=view.mirror.instance_name if view.mirror else None,
            mirror_author=view.mirror.author_name if view.mirror else None,
            mirror_author_avatar=view.mirror.author_avatar if view.mirror else None,
        )
        missing = (
            set(view.missing_equipment_ids) if view.missing_equipment_ids is not None else None
        )
        _, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        steps = []
        for position, step in enumerate(recipe.steps, start=1):
            step_text = (
                resolve(step.translations, self.locale, recipe.original_locale)[1].text
                if step.translations
                else ""
            )
            steps.append(
                StepView(
                    id=step.public_id,
                    position=position,
                    text=step_text,
                    duration_minutes=step.duration_minutes,
                    image_id=self._file(step.image_file_id),
                    ingredients=[
                        self._sub_amount(
                            si.sub_recipe_id,
                            si.amount * derived.factor if si.amount is not None else None,
                            si.unit_id,
                            lookups,
                            self._note(si, recipe.original_locale),
                            line_id=si.public_id,
                        )
                        if si.sub_recipe_id is not None
                        else self._amount(
                            si.ingredient_id or 0,
                            si.amount * derived.factor if si.amount is not None else None,
                            si.unit_id,
                            lookups,
                            self._note(si, recipe.original_locale),
                            line_id=si.public_id,
                        )
                        for si in step.ingredients
                    ],
                    equipment=[
                        StepEquipmentView(
                            id=se.public_id,
                            equipment=equipment_ref(
                                lookups.equipment[se.equipment_id], self.locale
                            ),
                            count=se.count,
                            note=(
                                resolve(se.translations, self.locale, recipe.original_locale)[
                                    1
                                ].note
                                if se.translations
                                else ""
                            ),
                        )
                        for se in step.equipment
                        if se.equipment_id in lookups.equipment
                    ],
                )
            )
        return RecipeDetailResponse(
            **self._summary_fields(summary, lookups, people, await self.switches()),
            tips=text.tips,
            yield_amount=recipe.yield_amount,
            yield_unit=(
                unit_ref(lookups.units[recipe.yield_unit_id], self.locale)
                if recipe.yield_unit_id in lookups.units
                else None
            ),
            needs=[
                SubRecipeNeed(
                    sub_recipe=self.sub_ref(lookups.recipes.get(need.recipe_id)),
                    amount=round(need.amount, 3) if need.amount is not None else None,
                    unit=(
                        unit_ref(lookups.units[need.unit_id], self.locale)
                        if need.unit_id is not None and need.unit_id in lookups.units
                        else None
                    ),
                    batches=round(need.batches, 3),
                )
                for need in derived.needs
            ],
            equipment=[
                EquipmentNeed(
                    equipment=equipment_ref(lookups.equipment[n.equipment_id], self.locale),
                    count=n.count,
                    sub_recipe=(
                        self.sub_ref(lookups.recipes.get(n.sub_recipe_id))
                        if n.sub_recipe_id is not None
                        else None
                    ),
                    missing=(n.equipment_id in missing) if missing is not None else None,
                )
                for n in needed_equipment(recipe, lookups.recipes)
                if n.equipment_id in lookups.equipment
            ],
            source_url=recipe.source_url,
            source_name=recipe.source_name,
            servings=derived.servings,
            ingredients=[
                self._amount(
                    line.ingredient_id,
                    line.amount,
                    line.unit_id,
                    lookups,
                    resolve(line.notes, self.locale, recipe.original_locale)[1].note
                    if line.notes
                    else "",
                )
                for line in derived.lines
            ],
            steps=steps,
            nutrition=NutritionView(
                total=nutrition(derived.nutrition_total),
                per_serving=nutrition(derived.nutrition_per_serving),
                complete=derived.nutrition_complete,
                missing_ingredient_ids=[
                    lookups.ingredients[i].public_id
                    for i in derived.missing_nutrition_ingredient_ids
                    if i in lookups.ingredients
                ],
                extended=[
                    ExtendedNutrientAmount(
                        key=e.key,
                        unit=EXTENDED_BY_KEY[e.key].unit,
                        total=e.total,
                        per_serving=e.per_serving,
                        complete=e.complete,
                    )
                    for e in derived.extended
                ],
            ),
            warnings=[
                WarningView(
                    restriction_id=await self._restriction_public_id(w.restriction_id),
                    kind=w.kind.value,
                    allergen=w.allergen.value if w.allergen else None,
                    diet=w.diet.value if w.diet else None,
                    family_id=(
                        lookups.families[w.family_id].public_id
                        if w.family_id in lookups.families
                        else None
                    ),
                    ingredient_id=(
                        lookups.ingredients[w.ingredient_id].public_id
                        if w.ingredient_id in lookups.ingredients
                        else None
                    ),
                    ingredient_names=[
                        ingredient_name(lookups.ingredients.get(i), self.locale)
                        for i in w.matching_ingredient_ids
                    ],
                )
                for w in view.warnings
            ],
            own_rating=(
                OwnRating(stars=view.own_rating.stars, comment=view.own_rating.comment)
                if view.own_rating
                else None
            ),
            own_note=view.own_note.text if view.own_note else None,
            last_cooked_by_me=view.last_cooked_by_me,
            can_delete=can_delete_recipe(self.viewer, recipe),
            based_on=await self.based_on(recipe),
            based_on_count=view.based_on_count,
            rating_overall_average=view.rating_overall_average,
            rating_overall_count=view.rating_overall_count,
            mirror_details=self._mirror(view.mirror, lookups, derived.factor),
            source_allergens_added=[a.value for a in view.source_allergens_added],
            unknown_allergens=list(view.unknown_allergens),
            unknown_diet_markers=list(view.unknown_diet_markers),
            unconfirmed_ingredient_ids=sorted(
                (i.public_id for i in lookups.ingredients.values() if unconfirmed(i)), key=str
            ),
        )

    def _unit_by_public_id(self, public_id: str | None, lookups: Lookups) -> UnitRef | None:
        if not public_id:
            return None
        unit = next((u for u in lookups.units.values() if str(u.public_id) == public_id), None)
        return unit_ref(unit, self.locale) if unit is not None else None

    def _mirror(
        self, info: MirrorInfo | None, lookups: Lookups, factor: float
    ) -> MirrorView | None:
        if info is None:
            return None

        def text(values: dict[str, str]) -> str:
            if not values:
                return ""
            return values.get(self.locale) or next(iter(values.values()))

        def scaled(amount: float | None) -> float | None:
            return round(amount * factor, 3) if amount is not None else None

        return MirrorView(
            peer=PeerRef(id=UUID(info.peer_id), name=info.instance_name),
            instance_name=info.instance_name,
            author_name=info.author_name,
            author_avatar_id=_uuid_or_none(info.author_avatar),
            source_url=info.source_url,
            source_revision=info.source_revision,
            accepted_at=info.accepted_at,
            updated_at=info.updated_at,
            plain_lines=[
                MirrorPlainLine(
                    step=line.step,
                    position=line.position,
                    name=text(line.names),
                    amount=scaled(line.amount),
                    unit=self._unit_by_public_id(line.unit_id, lookups),
                    note=text(line.notes),
                    allergens=list(line.allergens),
                    diet_markers=list(line.diet_markers),
                )
                for line in info.plain_lines
            ],
            plain_equipment=[
                MirrorPlainEquipment(
                    step=item.step, name=text(item.names), count=item.count, note=text(item.notes)
                )
                for item in info.plain_equipment
            ],
            unlinked_sub_recipes=[
                MirrorUnlinkedSubRecipe(
                    step=item.step,
                    position=item.position,
                    title=text(item.titles) or None,
                    amount=scaled(item.amount),
                    unit=self._unit_by_public_id(item.unit_id, lookups),
                )
                for item in info.unlinked_sub_recipes
            ],
        )

    async def _restriction_public_id(self, restriction_id: int) -> UUID:
        for restriction in await self._c.restrictions.list_for_user(self.viewer.id):
            if restriction.id == restriction_id:
                return restriction.public_id
        return UUID(int=0)

    def _edit_lines(
        self, lines: list[StepIngredient], lookups: Lookups
    ) -> list[StepIngredientEdit]:
        """Step lines or declared lines as the editor works on them; a line
        whose record the lookups lack is left out."""
        return [
            StepIngredientEdit(
                id=si.public_id,
                ingredient_id=(
                    lookups.ingredients[si.ingredient_id].public_id
                    if si.ingredient_id is not None
                    else None
                ),
                sub_recipe_id=(
                    lookups.recipes[si.sub_recipe_id].public_id
                    if si.sub_recipe_id is not None
                    else None
                ),
                ingredient_name=(
                    ingredient_name(lookups.ingredients[si.ingredient_id], self.locale)
                    if si.ingredient_id is not None
                    else self.sub_ref(lookups.recipes.get(si.sub_recipe_id or 0)).title or ""
                ),
                amount=si.amount,
                unit_id=(
                    lookups.units[si.unit_id].public_id
                    if si.unit_id is not None and si.unit_id in lookups.units
                    else None
                ),
                notes={k: NoteTextSchema(note=v.note) for k, v in si.translations.items()},
            )
            for si in lines
            if si.ingredient_id in lookups.ingredients or si.sub_recipe_id in lookups.recipes
        ]

    async def edit(
        self,
        recipe: Recipe,
        lookups: Lookups,
        can_edit: bool,
        less_visible: list[Recipe] | None = None,
        peer_hidden: list[Recipe] | None = None,
    ) -> RecipeEditResponse:
        await self.files([recipe.cover_file_id, *(s.image_file_id for s in recipe.steps)])
        tags = {t.id: t.public_id for t in lookups.tags.values()}
        people = await self.people(recipe.shared_user_ids)
        groups = await self._c.platform.groups.get_many(recipe.shared_group_ids)
        privacy = await self._c.platform.settings.get_privacy()
        peers = [
            p for p in [await self._c.platform.peers.get(i) for i in recipe.shared_peer_ids] if p
        ]
        return RecipeEditResponse(
            id=recipe.public_id,
            status=recipe.status.value,
            original_locale=recipe.original_locale,
            translations={
                k: RecipeTextSchema(title=v.title, description=v.description, tips=v.tips)
                for k, v in recipe.translations.items()
            },
            base_servings=recipe.base_servings,
            prep_minutes=recipe.prep_minutes,
            cook_minutes=recipe.cook_minutes,
            rest_minutes=recipe.rest_minutes,
            difficulty=recipe.difficulty.value,
            cover_image_id=self._file(recipe.cover_file_id),
            source_url=recipe.source_url,
            source_name=recipe.source_name,
            tag_ids=[tags[t] for t in recipe.tag_ids if t in tags],
            steps=[
                StepEdit(
                    id=s.public_id,
                    translations={
                        k: StepTextSchema(text=v.text) for k, v in s.translations.items()
                    },
                    duration_minutes=s.duration_minutes,
                    image_id=self._file(s.image_file_id),
                    ingredients=self._edit_lines(s.ingredients, lookups),
                    equipment=[
                        StepEquipmentEdit(
                            id=se.public_id,
                            equipment_id=lookups.equipment[se.equipment_id].public_id,
                            equipment_name=_name(
                                lookups.equipment[se.equipment_id].translations, self.locale
                            ),
                            count=se.count,
                            notes={
                                k: NoteTextSchema(note=v.note) for k, v in se.translations.items()
                            },
                        )
                        for se in s.equipment
                        if se.equipment_id in lookups.equipment
                    ],
                )
                for s in recipe.steps
            ],
            ingredients=self._edit_lines(recipe.ingredients, lookups),
            yield_amount=recipe.yield_amount,
            yield_unit_id=(
                lookups.units[recipe.yield_unit_id].public_id
                if recipe.yield_unit_id in lookups.units
                else None
            ),
            less_visible_sub_recipe_ids=[r.public_id for r in less_visible or []],
            visibility=recipe.visibility.value,
            effective_visibility=(await self.switches()).effective(recipe.visibility).value,
            shared_user_ids=[p.id for u in recipe.shared_user_ids if (p := people.get(u))],
            shared_group_ids=[g.public_id for g in groups],
            shared_peers=[PeerRef(id=p.public_id, name=p.name) for p in peers],
            peer_capped=recipe.peer_capped,
            peer_hidden_sub_recipe_ids=[r.public_id for r in peer_hidden or []],
            can_change_visibility=privacy.users_may_change_visibility
            and recipe.owner_id == self.viewer.id,
            created_via=recipe.created_via.value,
            owner=await self.person(recipe.owner_id),
            can_edit=can_edit,
            can_delete=can_delete_recipe(self.viewer, recipe),
            co_editors=[p for u in recipe.co_editor_ids if (p := (await self.people([u])).get(u))],
            can_manage_co_editors=can_manage_co_editors(self.viewer, recipe),
            based_on=await self.based_on(recipe),
            created=recipe.created,
            changed=recipe.changed,
            published_at=recipe.published_at,
        )

    # ── Cooking ───────────────────────────────────────────────────────

    async def cook_events(self, events: list[CookEvent]) -> list[CookEventResponse]:
        people = await self.people(e.user_id for e in events)
        found = await self._c.recipes.get_many(sorted({e.recipe_id for e in events}))
        recipes = await self.recipe_refs(found)
        variations = await self.variation_refs(
            {r.id: r for r in found}, [e.variation_id for e in events]
        )
        return [
            CookEventResponse(
                id=e.public_id,
                cooked_on=e.cooked_on,
                servings=e.servings,
                note=e.note,
                user=people.get(e.user_id),
                recipe=recipes.get(e.recipe_id),
                variation=variations.get(e.variation_id) if e.variation_id else None,
                is_own=e.user_id == self.viewer.id,
                created=e.created,
            )
            for e in events
        ]

    async def variation_refs(
        self, recipes: dict[int, Recipe], ids: Iterable[int | None]
    ) -> dict[int, VariationRef]:
        """References to the variations the viewer may see."""
        found = await self._c.variations.get_many(sorted({i for i in ids if i is not None}))
        return {
            v.id: VariationRef(id=v.public_id, name=v.name)
            for v in found
            if v.recipe_id in recipes and can_view_variation(self.viewer, recipes[v.recipe_id], v)
        }

    async def meal_plan(self, entries: list[MealPlanEntry]) -> list[MealPlanEntryResponse]:
        recipes = await self.recipe_refs(
            await self._c.recipes.get_many(sorted({e.recipe_id for e in entries if e.recipe_id}))
        )
        return [
            MealPlanEntryResponse(
                id=e.public_id,
                plan_date=e.plan_date,
                slot=e.slot.value,
                servings=e.servings,
                title=e.title,
                recipe=recipes.get(e.recipe_id) if e.recipe_id else None,
                scope=MealPlanScope.PERSONAL if e.household_id is None else MealPlanScope.HOUSEHOLD,
            )
            for e in entries
        ]

    async def shopping_summary(
        self, shopping_list: ShoppingList, counts: tuple[int, int]
    ) -> ShoppingListSummaryResponse:
        people = await self.people([shopping_list.owner_id, *shopping_list.member_ids])
        settings = await self.shopping_settings()
        return ShoppingListSummaryResponse(
            id=shopping_list.public_id,
            name=shopping_list.name,
            owner=people.get(shopping_list.owner_id),
            members=[p for m in shopping_list.member_ids if (p := people.get(m)) is not None],
            is_owner=shopping_list.owner_id == self.viewer.id,
            open_count=counts[0],
            checked_count=counts[1],
            changed=shopping_list.changed,
            mode=shopping_list.mode,
            keep=shopping_list.keep,
            last_activity_at=shopping_list.last_activity_at,
            deletes_on=deletes_on(shopping_list, settings.idle_list_days),
        )

    async def shopping_settings(self) -> ShoppingSettings:
        if self._shopping is None:
            self._shopping = await self._c.platform.settings.get_shopping()
        return self._shopping

    def shopping_notes(self, notes: list[ShoppingListNote]) -> list[ShoppingListNoteResponse]:
        return [
            ShoppingListNoteResponse(
                id=n.public_id, list_name=n.list_name, idle_days=n.idle_days, created=n.created
            )
            for n in notes
        ]

    async def shopping_list(self, view: ShoppingListView) -> ShoppingListResponse:
        items, lookups = view.items, view.lookups
        open_count = sum(1 for i in items if not i.checked)
        summary = await self.shopping_summary(
            view.shopping_list, (open_count, len(items) - open_count)
        )
        people = await self.people(i.checked_by_id for i in items)
        source_recipes = {
            r.id: r
            for r in await self._c.recipes.get_many(
                sorted({r for i in items for r in i.recipe_ids()})
            )
        }
        recipes = await self.recipe_refs(source_recipes.values())
        path_recipes = {
            r.id: r
            for r in await self._c.recipes.get_many(
                sorted({p for i in items for p in i.sub_recipe_path})
            )
        }
        await self.files(r.cover_file_id for r in path_recipes.values())
        responses = []
        for item in items:
            path = [self.sub_ref(path_recipes.get(p)) for p in item.sub_recipe_path]
            ingredient = lookups.ingredients.get(item.ingredient_id or 0)
            unit = lookups.units.get(item.unit_id) if item.unit_id is not None else None
            category = lookups.categories.get(item.category_id) if item.category_id else None
            name = (
                ingredient_name(ingredient, self.locale, item.amount if unit is None else 1)
                if ingredient
                else item.text or (path[-1].title or "" if path else "")
            )
            responses.append(
                ShoppingItemResponse(
                    id=item.public_id,
                    ingredient_id=ingredient.public_id if ingredient else None,
                    name=name,
                    text=item.text,
                    amount=item.amount,
                    unit=unit_ref(unit, self.locale) if unit else None,
                    category=category_ref(category, self.locale) if category else None,
                    family_id=(
                        lookups.families[ingredient.family_id].public_id
                        if ingredient and ingredient.family_id in lookups.families
                        else None
                    ),
                    checked=item.checked,
                    checked_by=people.get(item.checked_by_id) if item.checked_by_id else None,
                    checked_at=item.checked_at,
                    recipe=recipes.get(item.recipe_id) if item.recipe_id else None,
                    recipes=[
                        self.sub_ref(source_recipes[r])
                        for r in item.recipe_ids()
                        if r in source_recipes
                    ],
                    sub_recipe_path=path,
                    has_warning=item.id in view.warning_item_ids,
                )
            )
        settings = await self.shopping_settings()
        return ShoppingListResponse(
            **summary.model_dump(),
            bought_window_hours=settings.bought_window_hours,
            items=responses,
        )

    async def restrictions(
        self, restrictions: list[FoodRestriction]
    ) -> list[FoodRestrictionResponse]:
        ingredients = {
            i.id: i
            for i in await self._c.ingredients.get_many(
                [r.ingredient_id for r in restrictions if r.ingredient_id]
            )
        }
        families = {f.id: f for f in await self._c.families.list_all()}
        return [
            FoodRestrictionResponse(
                id=r.public_id,
                kind=r.kind.value,
                allergen=r.allergen.value if r.allergen else None,
                diet=r.diet.value if r.diet else None,
                family_id=families[r.family_id].public_id if r.family_id in families else None,
                family_name=(
                    _name(families[r.family_id].translations, self.locale)
                    if r.family_id in families
                    else None
                ),
                ingredient_id=(
                    ingredients[r.ingredient_id].public_id
                    if r.ingredient_id in ingredients
                    else None
                ),
                ingredient_name=(
                    ingredient_name(ingredients[r.ingredient_id], self.locale)
                    if r.ingredient_id in ingredients
                    else None
                ),
                note=r.note,
                created=r.created,
            )
            for r in restrictions
        ]
