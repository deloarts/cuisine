import { describe, expect, it } from 'vitest'

import { buildWebUrl } from '@/core/api/webRequest'

describe('buildWebUrl', () => {
  it('substitutes and encodes path parameters', () => {
    expect(buildWebUrl('/users/{user_id}/logout', { user_id: 'a b' })).toBe('/users/a%20b/logout')
  })

  it('refuses a missing parameter', () => {
    expect(() => buildWebUrl('/groups/{group_id}', {})).toThrow('group_id')
  })
})
