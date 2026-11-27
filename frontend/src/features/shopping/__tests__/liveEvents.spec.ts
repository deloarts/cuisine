import { describe, expect, it } from 'vitest'

import { actionFor } from '@/features/shopping/liveEvents'

const change = (data: object) => ({ type: 'change', data: JSON.stringify(data) })

describe('actionFor', () => {
  it('ignores the first ready and refetches after a reconnect', () => {
    expect(actionFor({ type: 'ready', data: '' }, 'l1', false)).toBe('ignore')
    expect(actionFor({ type: 'ready', data: '' }, 'l1', true)).toBe('refetch')
  })

  it('refetches on item and list changes of this list', () => {
    expect(actionFor(change({ type: 'items_changed', list_id: 'l1', by: 'u2' }), 'l1', true)).toBe('refetch')
    expect(actionFor(change({ type: 'list_changed', list_id: 'l1', by: null }), 'l1', true)).toBe('refetch')
  })

  it('reports a deleted list and ignores other lists', () => {
    expect(actionFor(change({ type: 'list_deleted', list_id: 'l1', by: 'u2' }), 'l1', true)).toBe('deleted')
    expect(actionFor(change({ type: 'items_changed', list_id: 'l2', by: 'u2' }), 'l1', true)).toBe('ignore')
  })

  it('refetches when the payload cannot be read', () => {
    expect(actionFor({ type: 'change', data: 'not json' }, 'l1', true)).toBe('refetch')
    expect(actionFor({ type: 'message', data: '' }, 'l1', true)).toBe('ignore')
  })
})
