import { Permission, type PermissionName } from '@/core/auth/permissions'

/**
 * The permissions grouped by area, in the order the user and group dialogs
 * list them. Every entry of `ALL_PERMISSIONS` belongs to exactly one group,
 * which a spec keeps true.
 */
export interface PermissionGroup {
  titleKey: string
  icon: string
  permissions: PermissionName[]
}

export const PERMISSION_GROUPS: PermissionGroup[] = [
  {
    titleKey: 'permissionChecklist.sections.recipes',
    icon: 'mdi-book-open-variant',
    permissions: [Permission.WRITE_RECIPES, Permission.MANAGE_RECIPES],
  },
  {
    titleKey: 'permissionChecklist.sections.catalogue',
    icon: 'mdi-food-apple-outline',
    permissions: [Permission.WRITE_INGREDIENTS, Permission.MANAGE_INGREDIENTS, Permission.WRITE_RESOURCES],
  },
  {
    titleKey: 'permissionChecklist.sections.access',
    icon: 'mdi-key-outline',
    permissions: [Permission.WRITE_PAT, Permission.USE_MCP],
  },
  {
    titleKey: 'permissionChecklist.sections.administration',
    icon: 'mdi-shield-account-outline',
    permissions: [
      Permission.READ_SETTINGS,
      Permission.WRITE_SETTINGS,
      Permission.WRITE_USERS,
      Permission.WRITE_GROUPS,
      Permission.READ_SECURITY_LOG,
      Permission.MANAGE_API_KEYS,
    ],
  },
]

/** The translation key of a permission's label. */
export function permissionLabelKey(permission: string): string {
  return `permissions.${permission.replace(':', '_')}`
}
