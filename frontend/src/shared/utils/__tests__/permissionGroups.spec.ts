import { describe, expect, it } from 'vitest'

import { ALL_PERMISSIONS } from '@/core/auth/permissions'
import { PERMISSION_GROUPS } from '@/shared/utils/permissionGroups'

describe('PERMISSION_GROUPS', () => {
  it('lists every permission in exactly one group', () => {
    const listed = PERMISSION_GROUPS.flatMap((g) => g.permissions)
    expect([...listed].sort()).toEqual([...ALL_PERMISSIONS].sort())
  })
})
