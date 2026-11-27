"""/api/v1/web/nutrition/sources: where the seeded nutrition values come
from, so the UI can credit the source next to them; and the admin view of
reference data updates that edits hold back, with the action that accepts
one. Both read the reference data the composition root seeds, which is why
they live here."""

from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from pydantic import Field

from src.bootstrap.reference_data import load_reference_data
from src.bootstrap.seed_merge import SeedMerge
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["nutrition"])
admin_router = APIRouter(tags=["reference data"])

_read_settings = require_permission(Permission.READ_SETTINGS)
_write_settings = require_permission(Permission.WRITE_SETTINGS)


class NutritionSourcesResponse(ResponseSchema):
    # The credit line per content locale, such as "Nutrition data: USDA
    # FoodData Central (public domain)."
    credit: dict[str, str]
    citation: str
    license: str


@router.get("/nutrition/sources", response_model=NutritionSourcesResponse)
async def nutrition_sources(_user: User = Depends(get_current_user)) -> NutritionSourcesResponse:
    data = load_reference_data()
    return NutritionSourcesResponse(
        credit=data.credit, citation=data.citation, license=data.license
    )


# ── Reference data updates (admin) ───────────────────────────────────


class ReferenceUpdateResponse(ResponseSchema):
    """A seed update an edit holds back: the field's current value, the
    seed's new value and the value the seed wrote before."""

    kind: str
    key: str
    name: str
    field: str
    current: Any
    seed: Any
    base: Any


class AcceptReferenceUpdateRequest(RequestSchema):
    kind: str = Field(max_length=16)
    key: str = Field(max_length=64)
    field: str = Field(max_length=64)


@admin_router.get("/admin/reference-updates", response_model=list[ReferenceUpdateResponse])
async def list_reference_updates(
    _actor: User = Depends(_read_settings),
    p: Platform = Depends(get_platform),
) -> list[ReferenceUpdateResponse]:
    """Overridden seed updates, allergens and diet markers first. Every
    other seed update was applied at start-up."""
    found = await SeedMerge(p.db, load_reference_data()).overridden()
    return [
        ReferenceUpdateResponse(
            kind=o.kind,
            key=o.key,
            name=o.name,
            field=o.field,
            current=o.current,
            seed=o.seed,
            base=o.base,
        )
        for o in found
    ]


@admin_router.post("/admin/reference-updates/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_reference_update(
    body: AcceptReferenceUpdateRequest,
    _actor: User = Depends(_write_settings),
    p: Platform = Depends(get_platform),
) -> None:
    """Writes the seed's value into the field; 404 when the field holds no
    overridden update."""
    if not await SeedMerge(p.db, load_reference_data()).accept(body.kind, body.key, body.field):
        raise NotFoundError("No such reference data update.")
    await p.uow.commit()
