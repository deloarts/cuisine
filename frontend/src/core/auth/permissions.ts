/**
 * The permission strings the backend knows (backend/src/platform/domain/
 * value_objects/permission.py). The UI only hides what a user cannot do;
 * the backend enforces every check on its own.
 */
export const Permission = {
  READ_SETTINGS: 'read:settings',
  WRITE_SETTINGS: 'write:settings',
  WRITE_USERS: 'write:users',
  WRITE_GROUPS: 'write:groups',
  READ_SECURITY_LOG: 'read:security_log',
  WRITE_PAT: 'write:pat',
  MANAGE_API_KEYS: 'manage:api_keys',
  WRITE_RECIPES: 'write:recipes',
  MANAGE_RECIPES: 'manage:recipes',
  WRITE_INGREDIENTS: 'write:ingredients',
  MANAGE_INGREDIENTS: 'manage:ingredients',
  WRITE_RESOURCES: 'write:resources',
  USE_MCP: 'use:mcp',
} as const

export type PermissionName = (typeof Permission)[keyof typeof Permission]

export const ALL_PERMISSIONS: PermissionName[] = Object.values(Permission)

/**
 * The permissions the backend only honours once the account has two-factor
 * authentication (backend/src/platform/domain/services/login_rules.py).
 */
export const TOTP_GUARDED_PERMISSIONS: readonly string[] = [Permission.READ_SETTINGS, Permission.WRITE_SETTINGS]
