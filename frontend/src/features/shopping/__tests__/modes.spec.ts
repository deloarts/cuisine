import { describe, expect, it } from 'vitest'

import type { ShoppingItem } from '@/features/shopping/grouping'
import {
  DELETION_WARNING_DAYS,
  deletionDay,
  deletionIsNear,
  leavesAt,
  recentlyBought,
  undoPurchase,
} from '@/features/shopping/modes'

function item(name: string, extra: Partial<ShoppingItem> = {}): ShoppingItem {
  return {
    id: name,
    ingredient_id: null,
    name,
    text: name,
    amount: null,
    unit: null,
    category: null,
    family_id: null,
    checked: false,
    checked_by: null,
    checked_at: null,
    recipe: null,
    recipes: [],
    sub_recipe_path: [],
    has_warning: false,
    ...extra,
  }
}

const anna = { id: 'anna', display_name: 'Anna' }

describe('recentlyBought', () => {
  it('lists only ticked items, the latest tick first and untimed ones last', () => {
    const items = [
      item('Milch', { checked: true, checked_at: '2026-11-22T08:00:00Z' }),
      item('Brot'),
      item('Käse', { checked: true, checked_at: '2026-11-22T09:30:00Z' }),
      item('Butter', { checked: true }),
    ]
    expect(recentlyBought(items).map((i) => i.name)).toEqual(['Käse', 'Milch', 'Butter'])
  })
})

describe('leavesAt', () => {
  it('adds the window to the tick time', () => {
    const ticked = item('Milch', { checked: true, checked_at: '2026-11-22T08:00:00Z' })
    expect(leavesAt(ticked, 12)?.toISOString()).toBe('2026-11-22T20:00:00.000Z')
  })

  it('knows nothing for open or untimed items', () => {
    expect(leavesAt(item('Brot'), 12)).toBeNull()
    expect(leavesAt(item('Butter', { checked: true }), 12)).toBeNull()
  })
})

describe('undoPurchase', () => {
  it('reopens the item and leaves the others and the original array alone', () => {
    const items = [
      item('Milch', { checked: true, checked_by: anna, checked_at: '2026-11-22T08:00:00Z' }),
      item('Käse', { checked: true, checked_by: anna, checked_at: '2026-11-22T09:00:00Z' }),
    ]
    const undone = undoPurchase(items, 'Milch')
    expect(undone[0]).toMatchObject({ checked: false, checked_by: null, checked_at: null })
    expect(undone[1]).toBe(items[1])
    expect(items[0]?.checked).toBe(true)
    expect(recentlyBought(undone).map((i) => i.name)).toEqual(['Käse'])
  })
})

describe('deletionDay', () => {
  it('reads the plain date as a local calendar day', () => {
    const day = deletionDay({ mode: 'normal', deletes_on: '2026-12-22' })
    expect([day?.getFullYear(), day?.getMonth(), day?.getDate()]).toEqual([2026, 11, 22])
  })

  it('is empty for continuous lists and lists that never delete themselves', () => {
    expect(deletionDay({ mode: 'continuous', deletes_on: '2026-12-22' })).toBeNull()
    expect(deletionDay({ mode: 'normal', deletes_on: null })).toBeNull()
  })
})

describe('deletionIsNear', () => {
  const today = new Date(2026, 11, 1, 18, 30)

  it('warns within the last days before the deletion', () => {
    expect(deletionIsNear({ mode: 'normal', deletes_on: '2026-12-08' }, today)).toBe(true)
    expect(DELETION_WARNING_DAYS).toBe(7)
  })

  it('stays calm further out and when nothing is deleted', () => {
    expect(deletionIsNear({ mode: 'normal', deletes_on: '2026-12-09' }, today)).toBe(false)
    expect(deletionIsNear({ mode: 'normal', deletes_on: null }, today)).toBe(false)
  })
})
