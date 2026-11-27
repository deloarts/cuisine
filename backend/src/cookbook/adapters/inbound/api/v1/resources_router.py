"""/api/v1/web: units, tags and ingredient categories. Everyone reads them;
write:resources changes them. `/resources/usage` counts how often each
resource is used, for the resources page alone, so the lists the pickers
load stay cheap."""

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_locale
from src.cookbook.adapters.inbound.api.deps import get_manage_resources
from src.cookbook.adapters.inbound.api.deps import get_read_resource_usage
from src.cookbook.adapters.inbound.api.presenters import category_response
from src.cookbook.adapters.inbound.api.presenters import family_response
from src.cookbook.adapters.inbound.api.presenters import tag_response
from src.cookbook.adapters.inbound.api.presenters import unit_response
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import MergeRequest
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import UnitDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.resource_schema import CategoryRequest
from src.cookbook.adapters.inbound.api.schemas.resource_schema import CategoryResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import FamilyRequest
from src.cookbook.adapters.inbound.api.schemas.resource_schema import FamilyResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import ResourceUsageResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import TagRequest
from src.cookbook.adapters.inbound.api.schemas.resource_schema import TagResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import UnitRequest
from src.cookbook.adapters.inbound.api.schemas.resource_schema import UnitResponse
from src.cookbook.adapters.inbound.api.schemas.resource_schema import UsageCount
from src.cookbook.application.use_cases.resources.manage_resources import CategoryCommand
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.application.use_cases.resources.manage_resources import TagCommand
from src.cookbook.application.use_cases.resources.manage_resources import UnitCommand
from src.cookbook.application.use_cases.resources.resource_usage import ReadResourceUsage
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["resources"])

_write = require_permission(Permission.WRITE_RESOURCES)


def _counts(counts: dict[UUID, int]) -> list[UsageCount]:
    return [UsageCount(id=i, usage_count=n) for i, n in counts.items()]


@router.get("/resources/usage", response_model=ResourceUsageResponse)
async def resource_usage(
    user: User = Depends(get_current_user),
    use_case: ReadResourceUsage = Depends(get_read_resource_usage),
) -> ResourceUsageResponse:
    usage = await use_case.resources(user)
    return ResourceUsageResponse(
        tags=_counts(usage.tags),
        units=_counts(usage.units),
        categories=_counts(usage.categories),
        families=_counts(usage.families),
        equipment=_counts(usage.equipment),
    )


def _unit_cmd(body: UnitRequest) -> UnitCommand:
    return UnitCommand(
        code=body.code,
        kind=body.kind,
        to_base=body.to_base,
        sort_order=body.sort_order,
        translations={
            k.value: UnitText(
                name=v.name.strip(),
                plural_name=(v.plural_name or v.name).strip(),
                abbreviation=(v.abbreviation or body.code).strip(),
            )
            for k, v in body.translations.items()
        },
    )


@router.get("/units", response_model=list[UnitResponse])
async def list_units(
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> list[UnitResponse]:
    return [unit_response(u, locale) for u in await use_case.units()]


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    body: UnitRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> UnitResponse:
    return unit_response(await use_case.create_unit(_unit_cmd(body)), locale)


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: str,
    body: UnitRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> UnitResponse:
    return unit_response(await use_case.update_unit(unit_id, _unit_cmd(body)), locale)


@router.get("/units/{unit_id}/deletion-impact", response_model=UnitDeletionImpact)
async def unit_deletion_impact(
    unit_id: str,
    _actor: User = Depends(_write),
    use_case: ManageResources = Depends(get_manage_resources),
) -> UnitDeletionImpact:
    seeded, in_use = await use_case.unit_impact(unit_id)
    return UnitDeletionImpact(seeded=seeded, in_use=in_use)


@router.post("/units/{unit_id}/merge", response_model=UnitResponse)
async def merge_unit(
    unit_id: str,
    body: MergeRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> UnitResponse:
    """Moves every use of the unit to the target and deletes it."""
    return unit_response(await use_case.merge_unit(unit_id, str(body.into_id)), locale)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: str,
    _actor: User = Depends(_write),
    use_case: ManageResources = Depends(get_manage_resources),
) -> None:
    await use_case.delete_unit(unit_id)


def _names(body: TagRequest | CategoryRequest) -> dict[str, NameText]:
    return {k.value: NameText(name=v.name) for k, v in body.translations.items()}


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> list[TagResponse]:
    return [tag_response(t, locale) for t in await use_case.tags()]


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> TagResponse:
    tag = await use_case.create_tag(
        TagCommand(kind=body.kind, translations=_names(body), color=body.color)
    )
    return tag_response(tag, locale)


@router.put("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    body: TagRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> TagResponse:
    tag = await use_case.update_tag(
        tag_id, TagCommand(kind=body.kind, translations=_names(body), color=body.color)
    )
    return tag_response(tag, locale)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    _actor: User = Depends(_write),
    use_case: ManageResources = Depends(get_manage_resources),
) -> None:
    await use_case.delete_tag(tag_id)


@router.get("/ingredient-families", response_model=list[FamilyResponse])
async def list_families(
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> list[FamilyResponse]:
    return [family_response(f, locale) for f in await use_case.families()]


@router.post(
    "/ingredient-families", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED
)
async def create_family(
    body: FamilyRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> FamilyResponse:
    family = await use_case.create_family(
        {k.value: NameText(name=v.name) for k, v in body.translations.items()}
    )
    return family_response(family, locale)


@router.put("/ingredient-families/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: str,
    body: FamilyRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> FamilyResponse:
    family = await use_case.update_family(
        family_id, {k.value: NameText(name=v.name) for k, v in body.translations.items()}
    )
    return family_response(family, locale)


@router.delete("/ingredient-families/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family(
    family_id: str,
    _actor: User = Depends(_write),
    use_case: ManageResources = Depends(get_manage_resources),
) -> None:
    """Its ingredients stay, without a family."""
    await use_case.delete_family(family_id)


@router.get("/ingredient-categories", response_model=list[CategoryResponse])
async def list_categories(
    _user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> list[CategoryResponse]:
    return [category_response(c, locale) for c in await use_case.categories()]


@router.post(
    "/ingredient-categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    body: CategoryRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> CategoryResponse:
    category = await use_case.create_category(
        CategoryCommand(translations=_names(body), sort_order=body.sort_order)
    )
    return category_response(category, locale)


@router.put("/ingredient-categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: CategoryRequest,
    _actor: User = Depends(_write),
    locale: str = Depends(get_locale),
    use_case: ManageResources = Depends(get_manage_resources),
) -> CategoryResponse:
    category = await use_case.update_category(
        category_id, CategoryCommand(translations=_names(body), sort_order=body.sort_order)
    )
    return category_response(category, locale)


@router.delete("/ingredient-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    replacement_id: str | None = Query(
        None, description="The category its ingredients move to; none leaves them uncategorised."
    ),
    _actor: User = Depends(_write),
    use_case: ManageResources = Depends(get_manage_resources),
) -> None:
    """Ingredients move to the replacement or to none; shopping items of
    the category fall into "Other"."""
    await use_case.delete_category(category_id, replacement_id)
