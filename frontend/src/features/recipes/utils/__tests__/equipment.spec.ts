import { describe, expect, it } from 'vitest'

import {
  equipmentLabel,
  groupEquipmentNeeds,
  matchEquipment,
  setOutList,
  type EquipmentNeed,
} from '@/features/recipes/utils/equipment'
import type { EquipmentResponse } from '@/shared/cookbook/types'

const ref = (id: string, name: string) => ({ id, name, kind: 'utensil', icon: null })
const sheets = { id: 's1', title: 'Pasta sheets', accessible: true, total_minutes: 45, cover_image_id: null }
const hidden = { id: null, title: null, accessible: false, total_minutes: null, cover_image_id: null }

function need(id: string, name: string, count: number | null, sub = null as EquipmentNeed['sub_recipe'], missing = null as boolean | null): EquipmentNeed {
  return { equipment: ref(id, name), count, sub_recipe: sub, missing }
}

function item(id: string, name: string, aliases: Record<string, string[]> = {}): EquipmentResponse {
  return {
    id,
    name,
    locale: 'de-AT',
    available_locales: ['de-AT'],
    kind: 'utensil',
    icon: null,
    basic: false,
    status: 'active',
    seeded: true,
    aliases,
    translations: {},
    changed: '',
  }
}

describe("You'll need", () => {
  it('groups the own items first, then one group per sub-recipe', () => {
    const groups = groupEquipmentNeeds([
      need('bowl', 'Bowl', 2),
      need('roller', 'Rolling pin', null, sheets),
      need('bowl', 'Bowl', 3, sheets),
      need('whisk', 'Whisk', null),
      need('pot', 'Pot', 1, hidden),
    ])
    expect(groups.map((g) => [g.subRecipe?.title ?? null, g.items.map((i) => i.equipment.name)])).toEqual([
      [null, ['Bowl', 'Whisk']],
      ['Pasta sheets', ['Rolling pin', 'Bowl']],
      [null, ['Pot']],
    ])
    expect(groups[2]!.subRecipe?.accessible).toBe(false)
  })

  it('labels counts above one and leaves the name alone otherwise', () => {
    expect(equipmentLabel('Bowl', 2)).toBe('2 × Bowl')
    expect(equipmentLabel('Bowl', 1)).toBe('Bowl')
    expect(equipmentLabel('Bowl', null)).toBe('Bowl')
  })

  it('sets every item out once, with the highest count and the missing mark', () => {
    const list = setOutList([
      need('bowl', 'Bowl', 2),
      need('mixer', 'Stand mixer', null, null, true),
      need('bowl', 'Bowl', 3, sheets),
      need('mixer', 'Stand mixer', 1, sheets, true),
    ])
    expect(list.map((n) => [n.equipment.name, n.count, n.missing, n.sub_recipe])).toEqual([
      ['Bowl', 3, null, null],
      ['Stand mixer', 1, true, null],
    ])
  })
})

describe('equipment suggestions', () => {
  const catalogue = [
    item('a', 'Rührbesen', { 'de-AT': ['Schneebesen'], 'en-GB': ['Whisk'] }),
    item('b', 'Schüssel'),
    item('c', 'Messbecher'),
  ]

  it('finds items by name without case or diacritics, then by alias with the alias shown', () => {
    expect(matchEquipment(catalogue, 'schu')).toEqual([{ kind: 'equipment', id: 'b', name: 'Schüssel' }])
    expect(matchEquipment(catalogue, 'schnee')).toEqual([
      { kind: 'equipment', id: 'a', name: 'Rührbesen', alias: 'Schneebesen' },
    ])
    expect(matchEquipment(catalogue, 'be').map((r) => r.id)).toEqual(['a', 'c'])
  })
})
