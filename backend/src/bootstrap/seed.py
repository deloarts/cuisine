"""
Seeding on every start: the system user from the INIT__ values, found by its
system flag rather than by its address. The first start creates it; every
later start syncs it back to the INIT__ values, so the environment stays the
source of truth for its name, address and password and it is always active. A password
or address changed in the app therefore lasts only until the next start.
Several workers may start at once; the loser of the race hits a unique
constraint and moves on.

The instance's own id (`instance_id`) is created here on the first start as
well and never changed afterwards.

The default groups are created once, on the start that creates the system
user, so a fresh install has a sensible set of permission bundles and
sharing circles. They are ordinary groups afterwards: an administrator may
rename, change or delete them, and a deleted one does not return.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_group_repository import (
    SqlAlchemyUserGroupRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_group import UserGroup
from src.platform.domain.value_objects.permission import Permission
from src.platform.infrastructure.config.settings import InitSettings
from src.platform.infrastructure.config.settings import cfg
from src.platform.infrastructure.logging.logger import log
from src.platform.infrastructure.security.hashing import BcryptPasswordHasher
from src.platform.ports.outbound.unit_of_work import ConstraintViolationError
from src.shared_kernel.domain.services.clock import now_utc


async def ensure_system_user(init: InitSettings | None = None) -> bool:
    """Creates the system user unless one exists, otherwise syncs it to the
    INIT__ values. Returns whether it created the account."""
    init = init or cfg.init
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        existing = next((u for u in await users.list_all() if u.is_systemuser), None)
        if existing is not None:
            await _sync(db, users, existing, init)
            return False
        general = await SqlAlchemySettingsRepository(db).get_general()
        created = User(
            full_name=init.full_name,
            email=init.mail,
            created=now_utc(),
            hashed_password=await BcryptPasswordHasher().hash(init.password),
            is_systemuser=True,
            language=general.default_language,
        )
        if not await _save(db, users, created):
            return False
    log.info("Created the system user %r from the INIT__ settings.", init.mail)
    return True


async def _sync(
    db: AsyncSession, users: SqlAlchemyUserRepository, user: User, init: InitSettings
) -> None:
    """Brings an existing system user back to the INIT__ values and
    reactivates it. Nothing is written when it already matches. An ordinary
    account holding the address blocks the sync; that needs an
    administrator, so it is logged rather than forced."""
    hasher = BcryptPasswordHasher()
    password_matches = await hasher.verify(init.password, user.hashed_password)
    old_mail = user.email
    if (
        user.full_name == init.full_name
        and user.email == init.mail
        and user.is_active
        and password_matches
    ):
        return
    user.full_name = init.full_name
    user.email = init.mail
    user.is_active = True
    if not password_matches:
        user.hashed_password = await hasher.hash(init.password)
    if not await _save(db, users, user):
        log.error(
            "The system user %r cannot be synced to the INIT__ settings: another account "
            "holds the address %r.",
            old_mail,
            init.mail,
        )
        return
    log.warning("The system user drifted from the INIT__ settings and was synced back.")


async def _save(db: AsyncSession, users: SqlAlchemyUserRepository, user: User) -> bool:
    """Saves and commits the user. Returns False and rolls back when a unique
    constraint refuses it; the repository flushes on save, so the violation
    can surface there as well as at the commit."""
    try:
        await users.save(user)
        await SqlAlchemyUnitOfWork(db).commit()
    except IntegrityError:
        await db.rollback()
        return False
    except ConstraintViolationError:
        return False
    return True


async def ensure_instance_id() -> UUID:
    """Creates the instance's own id on the first start and returns it; on
    every later start it returns the stored one unchanged."""
    async with SessionLocal() as db:
        instance_id = await SqlAlchemySettingsRepository(db).instance_id()
        await SqlAlchemyUnitOfWork(db).commit()
    return instance_id


@dataclass(frozen=True)
class DefaultGroup:
    name: str
    description: str
    permissions: tuple[str, ...] = ()


COOKS = "Cooks"
KITCHEN_HELPERS = "Kitchen helpers"

# Permission bundles stack, since there are no denials: a person gets every
# group they need. Someone in no group reads what they may see and keeps
# their personal layer, meal plan and shopping lists, but writes no recipes.
# The last two groups hold no permissions and only decide who sees recipes
# shared with them.
DEFAULT_GROUPS: tuple[DefaultGroup, ...] = (
    DefaultGroup(
        COOKS,
        "Writes recipes and ingredients and edits their own.",
        (Permission.WRITE_RECIPES, Permission.WRITE_INGREDIENTS),
    ),
    DefaultGroup(
        KITCHEN_HELPERS,
        "May connect an AI agent and create personal access tokens for it, "
        "for example to import recipes as drafts.",
        (Permission.USE_MCP, Permission.WRITE_PAT),
    ),
    DefaultGroup(
        "Curators",
        "Looks after the shared catalogue: everybody's ingredients, the units, "
        "tags, categories, families and equipment.",
        (Permission.MANAGE_INGREDIENTS, Permission.WRITE_RESOURCES),
    ),
    DefaultGroup(
        "Editors",
        "Edits, publishes and deletes anybody's recipes they can see, and sees "
        "every draft. Keep this group small.",
        (Permission.MANAGE_RECIPES,),
    ),
    DefaultGroup(
        "Administrators",
        "Runs the instance: settings, accounts, groups, the security log and API keys.",
        (
            Permission.READ_SETTINGS,
            Permission.WRITE_SETTINGS,
            Permission.WRITE_USERS,
            Permission.WRITE_GROUPS,
            Permission.READ_SECURITY_LOG,
            Permission.MANAGE_API_KEYS,
        ),
    ),
    DefaultGroup("Family", "A sharing circle for recipes shared with the family."),
    DefaultGroup("Friends", "A sharing circle for recipes shared with friends."),
)


async def ensure_default_groups() -> int:
    """Creates every default group whose name is still free and returns how
    many it created. The app calls it only on the start that created the
    system user, so groups an administrator deleted stay deleted."""
    created = 0
    async with SessionLocal() as db:
        groups = SqlAlchemyUserGroupRepository(db)
        for default in DEFAULT_GROUPS:
            if await groups.name_taken(default.name):
                continue
            await groups.save(
                UserGroup(
                    name=default.name,
                    description=default.description,
                    permissions=sorted(default.permissions),
                    created=now_utc(),
                )
            )
            created += 1
        await SqlAlchemyUnitOfWork(db).commit()
    if created:
        log.info("Created %d default groups.", created)
    return created
