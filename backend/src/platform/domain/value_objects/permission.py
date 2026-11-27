"""Canonical permission strings. Using these instead of literals turns
typos into import-time errors.

Reading recipes needs no permission: each recipe's visibility decides who
sees it. Permissions are granted directly to a user or through the groups
they belong to; there are no denials. The cookbook's permissions
come in pairs: write:x creates records and edits the actor's own, manage:x
edits and deletes everybody's."""

from typing import ClassVar


class Permission:
    # Settings. Reading them needs a permission of its own, since they hold
    # the mail server and the security policy.
    READ_SETTINGS = "read:settings"
    WRITE_SETTINGS = "write:settings"

    # Accounts. There is no open sign-up: an administrator with write:users
    # creates every account, edits, deactivates and deletes it, resets its
    # second factor and signs it out everywhere.
    WRITE_USERS = "write:users"

    # Groups: freely named permission bundles. Write covers creating,
    # renaming, deleting and changing members and permissions.
    WRITE_GROUPS = "write:groups"

    # The instance-wide security log. Every user always sees their own.
    READ_SECURITY_LOG = "read:security_log"

    # Recipes: write creates recipes and edits, publishes and deletes the
    # actor's own; manage edits, publishes and deletes anybody's, and sees
    # every draft.
    WRITE_RECIPES = "write:recipes"
    MANAGE_RECIPES = "manage:recipes"

    # Ingredients: write creates ingredients and edits the actor's own;
    # manage edits, activates and deletes anybody's.
    WRITE_INGREDIENTS = "write:ingredients"
    MANAGE_INGREDIENTS = "manage:ingredients"

    # The shared resources recipes and ingredients refer to: units, tags and
    # ingredient categories.
    WRITE_RESOURCES = "write:resources"

    # Connecting an AI agent through the MCP surface with a personal access
    # token or an API key. The agent still needs the permissions of each
    # tool it calls, such as write:recipes for a recipe draft.
    USE_MCP = "use:mcp"

    # Personal access tokens: a user's own scoped bearer tokens, which act
    # as that user with a subset of their permissions.
    WRITE_PAT = "write:pat"

    # API keys: admin-issued credentials for a separate service account
    # with its own permission set, capped at the creator's permissions.
    MANAGE_API_KEYS = "manage:api_keys"

    ALL: ClassVar[list[str]] = [
        READ_SETTINGS,
        WRITE_SETTINGS,
        WRITE_USERS,
        WRITE_GROUPS,
        READ_SECURITY_LOG,
        WRITE_RECIPES,
        MANAGE_RECIPES,
        WRITE_INGREDIENTS,
        MANAGE_INGREDIENTS,
        WRITE_RESOURCES,
        USE_MCP,
        WRITE_PAT,
        MANAGE_API_KEYS,
    ]
