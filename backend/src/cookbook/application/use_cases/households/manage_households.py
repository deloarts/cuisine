"""
Households: the people who cook and shop together. A user belongs to at most
one. Anyone without a household founds one; a member invites people, who
accept or decline; anyone leaves, and the last one leaving dissolves the
household with its meal plan and default shopping list. There are no roles
inside a household. Administrators see who belongs to which household, never
its plan or lists.
"""

from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.household import Household
from src.cookbook.domain.entities.household import HouseholdInvitation
from src.cookbook.domain.exceptions import AlreadyInHouseholdError
from src.cookbook.domain.exceptions import FeatureDisabledError
from src.cookbook.domain.exceptions import HouseholdInvitationNotFoundError
from src.cookbook.domain.exceptions import InvalidPlanError
from src.cookbook.domain.exceptions import NotInHouseholdError
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.ports.outbound.feature_switches import IFeatureSwitches
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


class ManageHouseholds:
    def __init__(
        self,
        *,
        household_repo: IHouseholdRepository,
        list_repo: IShoppingListRepository,
        user_repo: IUserRepository,
        uow: IUnitOfWork,
        features: IFeatureSwitches | None = None,
    ) -> None:
        self._features = features
        self._households = household_repo
        self._lists = list_repo
        self._users = user_repo
        self._uow = uow

    async def _assert_enabled(self) -> None:
        """Founding, inviting and joining need the households feature;
        reading and leaving always work."""
        if self._features is not None and not (await self._features.get_features()).households:
            raise FeatureDisabledError("Households are switched off on this instance.")

    @staticmethod
    def _name(name: str) -> str:
        cleaned = name.strip()
        if not cleaned or len(cleaned) > 128:
            raise InvalidPlanError("The household name must have 1 to 128 characters.")
        return cleaned

    async def mine(self, actor: User) -> Household | None:
        return await self._households.of_user(actor.id)

    async def _own(self, actor: User) -> Household:
        household = await self._households.of_user(actor.id)
        if household is None:
            raise NotInHouseholdError("You do not belong to a household.")
        return household

    async def pending_invitations(self, household: Household) -> list[HouseholdInvitation]:
        return await self._households.invitations_of(household.id)

    async def invitations_for(self, actor: User) -> list[HouseholdInvitation]:
        return await self._households.invitations_for(actor.id)

    async def household_of_invitation(self, invitation: HouseholdInvitation) -> Household | None:
        for household in await self._households.list_all():
            if household.id == invitation.household_id:
                return household
        return None

    async def create(self, actor: User, name: str) -> Household:
        await self._assert_enabled()
        if await self._households.of_user(actor.id) is not None:
            raise AlreadyInHouseholdError("You already belong to a household.")
        now = now_utc()
        household = await self._households.save(
            Household(name=self._name(name), created=now, member_ids=[actor.id])
        )
        # Every household has one shopping list all its members are on. It
        # starts continuous and never deletes itself.
        await self._lists.save(
            ShoppingList(
                owner_id=actor.id,
                name=household.name,
                created=now,
                changed=now,
                last_activity_at=now,
                mode=ShoppingListMode.CONTINUOUS,
                household_id=household.id,
            )
        )
        await self._uow.commit()
        return household

    async def rename(self, actor: User, name: str) -> Household:
        household = await self._own(actor)
        household.name = self._name(name)
        saved = await self._households.save(household)
        await self._uow.commit()
        return saved

    async def invite(self, actor: User, user_public_id: str) -> HouseholdInvitation:
        await self._assert_enabled()
        household = await self._own(actor)
        invitee = await self._users.get_by_public_id(user_public_id)
        if invitee is None or not invitee.is_active or invitee.is_service_account:
            raise UserNotFoundError("No such user.")
        if invitee.id in household.member_ids:
            raise AlreadyInHouseholdError("This person already belongs to your household.")
        existing = await self._households.find_invitation(household.id, invitee.id)
        if existing is not None:
            return existing
        invitation = await self._households.save_invitation(
            HouseholdInvitation(
                household_id=household.id,
                inviter_id=actor.id,
                invitee_id=invitee.id,
                created=now_utc(),
            )
        )
        await self._uow.commit()
        return invitation

    async def _invitation_for(self, actor: User, public_id: str) -> HouseholdInvitation:
        invitation = await self._households.get_invitation(public_id)
        if invitation is None or invitation.invitee_id != actor.id:
            raise HouseholdInvitationNotFoundError("No such invitation for you.")
        return invitation

    async def accept(self, actor: User, public_id: str) -> Household:
        await self._assert_enabled()
        invitation = await self._invitation_for(actor, public_id)
        if await self._households.of_user(actor.id) is not None:
            raise AlreadyInHouseholdError("Leave your household before you join another.")
        household = await self.household_of_invitation(invitation)
        if household is None:
            raise HouseholdInvitationNotFoundError("No such invitation for you.")
        household.member_ids = [*household.member_ids, actor.id]
        saved = await self._households.save(household)
        await self._households.delete_invitation(invitation)
        await self._uow.commit()
        return saved

    async def decline(self, actor: User, public_id: str) -> None:
        await self._households.delete_invitation(await self._invitation_for(actor, public_id))
        await self._uow.commit()

    async def revoke(self, actor: User, public_id: str) -> None:
        """A member takes back an invitation of their household."""
        household = await self._own(actor)
        invitation = await self._households.get_invitation(public_id)
        if invitation is None or invitation.household_id != household.id:
            raise HouseholdInvitationNotFoundError("No such invitation of your household.")
        await self._households.delete_invitation(invitation)
        await self._uow.commit()

    async def leave(self, actor: User) -> None:
        """Own recipes and cook events stay with the user, the plan and the
        default list with the household; the last member dissolves it."""
        household = await self._own(actor)
        household.member_ids = [m for m in household.member_ids if m != actor.id]
        if household.member_ids:
            await self._households.save(household)
        else:
            await self._households.delete(household)
        await self._uow.commit()

    async def all(self) -> list[Household]:
        return await self._households.list_all()
