from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.household_models import (
    HouseholdInvitationModel,
)
from src.cookbook.adapters.outbound.persistence.models.household_models import HouseholdMemberModel
from src.cookbook.adapters.outbound.persistence.models.household_models import HouseholdModel
from src.cookbook.domain.entities.household import Household
from src.cookbook.domain.entities.household import HouseholdInvitation
from src.platform.adapters.outbound.persistence.repositories._common import entity_from_row
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


class SqlAlchemyHouseholdRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[HouseholdModel]) -> list[Household]:
        ids = [r.id for r in rows]
        members: dict[int, list[int]] = {i: [] for i in ids}
        if ids:
            for household_id, user_id in (
                await self._db.execute(
                    select(HouseholdMemberModel.household_id, HouseholdMemberModel.user_id).where(
                        HouseholdMemberModel.household_id.in_(ids)
                    )
                )
            ).all():
                members[household_id].append(user_id)
        return [
            Household(
                id=r.id,
                public_id=r.public_id,
                name=r.name,
                created=r.created,
                member_ids=sorted(members.get(r.id, [])),
            )
            for r in rows
        ]

    async def of_user(self, user_id: int) -> Household | None:
        household_id = await self._db.scalar(
            select(HouseholdMemberModel.household_id).where(HouseholdMemberModel.user_id == user_id)
        )
        if household_id is None:
            return None
        row = await self._db.get(HouseholdModel, household_id)
        return (await self._entities([row]))[0] if row is not None else None

    async def get_by_public_id(self, public_id: str) -> Household | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(HouseholdModel).where(HouseholdModel.public_id == uid))
        return (await self._entities([row]))[0] if row is not None else None

    async def list_all(self) -> list[Household]:
        rows = await self._db.scalars(select(HouseholdModel).order_by(HouseholdModel.name))
        return await self._entities(list(rows.all()))

    async def save(self, household: Household) -> Household:
        row = await self._db.get(HouseholdModel, household.id) if household.id else None
        if row is None:
            row = HouseholdModel(public_id=household.public_id, created=household.created)
            self._db.add(row)
        row.name = household.name
        await self._db.flush()
        await self._db.execute(
            delete(HouseholdMemberModel).where(HouseholdMemberModel.household_id == row.id)
        )
        for user_id in sorted(set(household.member_ids)):
            self._db.add(HouseholdMemberModel(user_id=user_id, household_id=row.id))
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, household: Household) -> None:
        await self._db.execute(delete(HouseholdModel).where(HouseholdModel.id == household.id))

    async def invitations_for(self, user_id: int) -> list[HouseholdInvitation]:
        rows = await self._db.scalars(
            select(HouseholdInvitationModel)
            .where(HouseholdInvitationModel.invitee_id == user_id)
            .order_by(HouseholdInvitationModel.created)
        )
        return [entity_from_row(HouseholdInvitation, r) for r in rows.all()]

    async def invitations_of(self, household_id: int) -> list[HouseholdInvitation]:
        rows = await self._db.scalars(
            select(HouseholdInvitationModel)
            .where(HouseholdInvitationModel.household_id == household_id)
            .order_by(HouseholdInvitationModel.created)
        )
        return [entity_from_row(HouseholdInvitation, r) for r in rows.all()]

    async def get_invitation(self, public_id: str) -> HouseholdInvitation | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(HouseholdInvitationModel).where(HouseholdInvitationModel.public_id == uid)
        )
        return entity_from_row(HouseholdInvitation, row) if row is not None else None

    async def find_invitation(
        self, household_id: int, invitee_id: int
    ) -> HouseholdInvitation | None:
        row = await self._db.scalar(
            select(HouseholdInvitationModel).where(
                HouseholdInvitationModel.household_id == household_id,
                HouseholdInvitationModel.invitee_id == invitee_id,
            )
        )
        return entity_from_row(HouseholdInvitation, row) if row is not None else None

    async def save_invitation(self, invitation: HouseholdInvitation) -> HouseholdInvitation:
        row = HouseholdInvitationModel(
            public_id=invitation.public_id,
            household_id=invitation.household_id,
            inviter_id=invitation.inviter_id,
            invitee_id=invitation.invitee_id,
            created=invitation.created,
        )
        self._db.add(row)
        await self._db.flush()
        return entity_from_row(HouseholdInvitation, row)

    async def delete_invitation(self, invitation: HouseholdInvitation) -> None:
        await self._db.execute(
            delete(HouseholdInvitationModel).where(HouseholdInvitationModel.id == invitation.id)
        )
