"""
My kitchen: the equipment a cook owns. In a household the kitchen is the
household's and every member reads and changes it; without one it is the
cook's own. Nobody else sees it, and the dinner guest check ignores it.

Until a kitchen is set up nothing is flagged: recipes carry no missing
equipment. Setting it up without a list ticks the catalogue's basic items.
A personal kitchen made before joining a household stays, unused, until the
cook leaves again.
"""

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.equipment import Kitchen
from src.cookbook.domain.exceptions import EquipmentNotFoundError
from src.cookbook.domain.exceptions import KitchenNotSetUpError
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.equipment_repository import IKitchenRepository
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


class ManageKitchen:
    def __init__(
        self,
        *,
        kitchen_repo: IKitchenRepository,
        equipment_repo: IEquipmentRepository,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
    ) -> None:
        self._kitchens = kitchen_repo
        self._equipment = equipment_repo
        self._viewers = viewers
        self._uow = uow

    async def of(self, actor: User) -> tuple[Kitchen | None, bool]:
        """The actor's kitchen, if set up, and whether it is the household's."""
        viewer = await self._viewers.of(actor)
        if viewer.household_id is not None:
            return await self._kitchens.of_household(viewer.household_id), True
        return await self._kitchens.of_user(actor.id), False

    async def owned(self, actor: User) -> set[int] | None:
        """The equipment the actor's kitchen holds; None before set-up."""
        kitchen, _ = await self.of(actor)
        return set(kitchen.equipment_ids) if kitchen is not None else None

    async def _ids(self, public_ids: list[str]) -> list[int]:
        ids: list[int] = []
        for public_id in dict.fromkeys(public_ids):
            item = await self._equipment.get_by_public_id(public_id)
            if item is None:
                raise EquipmentNotFoundError("An item of the kitchen does not exist.")
            ids.append(item.id)
        return ids

    async def set_up(self, actor: User, public_ids: list[str] | None) -> tuple[Kitchen, bool]:
        """Sets the kitchen up, or starts it over, with the given items or
        the catalogue's basic ones."""
        if public_ids is None:
            ids = [e.id for e in await self._equipment.find(EquipmentQuery()) if e.basic]
        else:
            ids = await self._ids(public_ids)
        existing, shared = await self.of(actor)
        now = now_utc()
        if existing is not None:
            existing.equipment_ids = ids
            existing.changed = now
            saved = await self._kitchens.save(existing)
        else:
            viewer = await self._viewers.of(actor)
            saved = await self._kitchens.save(
                Kitchen(
                    household_id=viewer.household_id,
                    user_id=None if viewer.household_id is not None else actor.id,
                    equipment_ids=ids,
                    set_up_at=now,
                    changed=now,
                )
            )
        await self._uow.commit()
        return saved, shared

    async def update(self, actor: User, public_ids: list[str]) -> tuple[Kitchen, bool]:
        kitchen, shared = await self.of(actor)
        if kitchen is None:
            raise KitchenNotSetUpError("Set up the kitchen first.")
        kitchen.equipment_ids = await self._ids(public_ids)
        kitchen.changed = now_utc()
        saved = await self._kitchens.save(kitchen)
        await self._uow.commit()
        return saved, shared

    async def reset(self, actor: User) -> None:
        """Forgets the kitchen, so nothing is flagged until it is set up again."""
        kitchen, _ = await self.of(actor)
        if kitchen is not None:
            await self._kitchens.delete(kitchen)
            await self._uow.commit()
