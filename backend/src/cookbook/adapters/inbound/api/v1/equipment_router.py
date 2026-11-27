"""/api/v1/web: the equipment catalogue (everyone reads it, write:resources
changes it) and the viewer's kitchen, the equipment they or their household
own."""

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_locale
from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_equipment
from src.cookbook.adapters.inbound.api.deps import get_manage_kitchen
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.presenters import equipment_ref
from src.cookbook.adapters.inbound.api.presenters import equipment_response
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import MergeRequest
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import EquipmentDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import EquipmentDuplicate
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import EquipmentRequest
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import EquipmentResponse
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import KitchenRequest
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import KitchenResponse
from src.cookbook.adapters.inbound.api.schemas.equipment_schema import KitchenSetupRequest
from src.cookbook.application.use_cases.equipment.kitchen import ManageKitchen
from src.cookbook.application.use_cases.equipment.manage_equipment import EquipmentCommand
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.domain.entities.equipment import Kitchen
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import EquipmentStatus
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["equipment"])

_write = require_permission(Permission.WRITE_RESOURCES)


def _command(body: EquipmentRequest) -> EquipmentCommand:
    return EquipmentCommand(
        kind=body.kind,
        translations={k.value: NameText(v.name) for k, v in body.translations.items()},
        aliases={k.value: list(v) for k, v in body.aliases.items()},
        icon=body.icon,
        basic=body.basic,
    )


@router.get("/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    search: str | None = Query(None, max_length=128),
    kind: EquipmentKind | None = Query(None),
    status_filter: EquipmentStatus | None = Query(None, alias="status"),
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> list[EquipmentResponse]:
    """The whole catalogue (it stays small), sorted by name in the viewer's
    language. `search` matches names and aliases in any language."""
    found = await use_case.find(EquipmentQuery(search=search, kind=kind, status=status_filter))
    responses = [equipment_response(e, locale) for e in found]
    return sorted(responses, key=lambda r: r.name.casefold())


@router.get("/equipment/duplicates", response_model=list[EquipmentDuplicate])
async def equipment_duplicates(
    name: str = Query(min_length=1, max_length=128),
    locale: ContentLocale | None = Query(None),
    _user: User = Depends(get_current_user),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> list[EquipmentDuplicate]:
    """Equipment that probably means the same as `name`, by the rules of
    GET /ingredients/duplicates."""
    found = await use_case.near_duplicates(name, locale.value if locale else None)
    return [
        EquipmentDuplicate(
            id=UUID(entry.public_id), name=entry.main_name, matched=entry.name, exact=exact
        )
        for entry, exact in found
    ]


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def read_equipment(
    equipment_id: str,
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentResponse:
    return equipment_response(await use_case.get(equipment_id), locale)


@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    body: EquipmentRequest,
    actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentResponse:
    return equipment_response(await use_case.create(actor, _command(body)), locale)


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: str,
    body: EquipmentRequest,
    actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentResponse:
    return equipment_response(await use_case.update(actor, equipment_id, _command(body)), locale)


@router.post("/equipment/{equipment_id}/activate", response_model=EquipmentResponse)
async def activate_equipment(
    equipment_id: str,
    actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentResponse:
    """Marks a draft an agent created as reviewed."""
    return equipment_response(await use_case.activate(actor, equipment_id), locale)


@router.get("/equipment/{equipment_id}/deletion-impact", response_model=EquipmentDeletionImpact)
async def equipment_deletion_impact(
    equipment_id: str,
    _actor: User = Depends(_write),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentDeletionImpact:
    item = await use_case.get(equipment_id)
    recipe_ids = await use_case.recipe_ids_using(item)
    recipes = [
        r for r in await c.recipes.get_many(recipe_ids) if can_view_recipe(presenter.viewer, r)
    ]
    refs = await presenter.recipe_refs(recipes)
    return EquipmentDeletionImpact(
        seeded=item.seed_key is not None,
        recipe_count=len(recipe_ids),
        recipes=[refs[r.id] for r in recipes if r.id in refs],
        can_merge=item.seed_key is None,
    )


@router.post("/equipment/{equipment_id}/merge", response_model=EquipmentResponse)
async def merge_equipment(
    equipment_id: str,
    body: MergeRequest,
    actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> EquipmentResponse:
    """Moves recipe steps and kitchens to the target, keeps this item's
    names as the target's aliases and deletes it. Answers with the target."""
    return equipment_response(await use_case.merge(actor, equipment_id, str(body.into_id)), locale)


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: str,
    actor: User = Depends(_write),
    use_case: ManageEquipment = Depends(get_manage_equipment),
) -> None:
    """409 for seeded items and for items a recipe step names."""
    await use_case.delete(actor, equipment_id)


# ── My kitchen ───────────────────────────────────────────────────────


async def _kitchen(
    kitchen: Kitchen | None, household: bool, c: Cookbook, locale: str
) -> KitchenResponse:
    if kitchen is None:
        return KitchenResponse(set_up=False, household=household, equipment=[], changed=None)
    items = await c.equipment.get_many(kitchen.equipment_ids)
    refs = sorted((equipment_ref(e, locale) for e in items), key=lambda r: r.name.casefold())
    return KitchenResponse(
        set_up=True, household=household, equipment=refs, changed=kitchen.changed
    )


@router.get("/kitchen", response_model=KitchenResponse, tags=["kitchen"])
async def read_kitchen(
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    locale: str = Depends(get_locale),
    use_case: ManageKitchen = Depends(get_manage_kitchen),
) -> KitchenResponse:
    """The viewer's kitchen: the household's when they are in one."""
    kitchen, household = await use_case.of(user)
    return await _kitchen(kitchen, household, c, locale)


@router.post("/kitchen/setup", response_model=KitchenResponse, tags=["kitchen"])
async def set_up_kitchen(
    body: KitchenSetupRequest,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    locale: str = Depends(get_locale),
    use_case: ManageKitchen = Depends(get_manage_kitchen),
) -> KitchenResponse:
    """Sets the kitchen up (or starts it over) with the given items, or
    with the catalogue's basic items when `equipment_ids` is null. From
    then on recipes carry `missing_equipment` and `kitchen_ready`."""
    ids = [str(i) for i in body.equipment_ids] if body.equipment_ids is not None else None
    kitchen, household = await use_case.set_up(user, ids)
    return await _kitchen(kitchen, household, c, locale)


@router.put("/kitchen", response_model=KitchenResponse, tags=["kitchen"])
async def update_kitchen(
    body: KitchenRequest,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    locale: str = Depends(get_locale),
    use_case: ManageKitchen = Depends(get_manage_kitchen),
) -> KitchenResponse:
    """Replaces the kitchen's equipment; 422 before set-up."""
    kitchen, household = await use_case.update(user, [str(i) for i in body.equipment_ids])
    return await _kitchen(kitchen, household, c, locale)


@router.delete("/kitchen", status_code=status.HTTP_204_NO_CONTENT, tags=["kitchen"])
async def reset_kitchen(
    user: User = Depends(get_current_user),
    use_case: ManageKitchen = Depends(get_manage_kitchen),
) -> None:
    """Forgets the kitchen; nothing is flagged until it is set up again."""
    await use_case.reset(user)
