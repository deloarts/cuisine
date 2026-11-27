import { describe, expect, it } from 'vitest'

import type { IngredientAmount } from '@/features/recipes/api/recipes'
import {
  allPlainEquipment,
  attributionParams,
  extraIngredients,
  mergeStepLines,
  plainEquipmentOf,
  type MirrorView,
} from '@/features/recipes/utils/mirrors'

const gram = { id: 'g', code: 'g', kind: 'mass', name: 'gram', plural_name: 'grams', abbreviation: 'g' }
const line = (id: string): IngredientAmount => ({ ingredient_id: id, name: id, amount: 1, unit: null, note: '' })

function details(overrides: Partial<MirrorView> = {}): MirrorView {
  return {
    peer: { id: 'p1', name: 'Friends' },
    instance_name: 'Friends',
    author_name: 'Mia',
    source_url: 'https://friends.example/r/abc',
    source_revision: 'rev',
    accepted_at: '2026-11-22T10:00:00Z',
    updated_at: '2026-11-22T10:00:00Z',
    plain_lines: [],
    plain_equipment: [],
    unlinked_sub_recipes: [],
    ...overrides,
  }
}

const plain = (step: number, position: number, name: string, amount: number | null = 20) => ({
  step,
  position,
  name,
  amount,
  unit: gram,
  note: '',
  allergens: ['mustard'],
  diet_markers: [],
})

describe('mergeStepLines', () => {
  it('puts plain and unlinked lines back at their source positions', () => {
    const mirror = details({
      plain_lines: [plain(0, 1, 'Kren'), plain(1, 0, 'Elsewhere')],
      unlinked_sub_recipes: [{ step: 0, position: 3, title: 'Teig', amount: null, unit: null }],
    })
    const { items } = mergeStepLines([line('a'), line('b'), line('c')], mirror, 0)
    expect(items.map((i) => i.name)).toEqual(['a', 'Kren', 'b', 'Teig', 'c'])
    expect(items[1]!.origin).toBe('plain')
    expect(items[3]!.origin).toBe('unlinked')
  })

  it('appends lines whose position lies beyond the step and keeps the marks on their lines', () => {
    const mirror = details({ plain_lines: [plain(0, 0, 'First'), plain(0, 9, 'Last')] })
    const mark = { kind: 'added' as const, from: null }
    const merged = mergeStepLines([line('a')], mirror, 0, [mark])
    expect(merged.items.map((i) => i.name)).toEqual(['First', 'a', 'Last'])
    expect(merged.marks).toEqual([null, mark, null])
  })

  it('leaves the lines alone without details or for a step a variation added', () => {
    const lines = [line('a')]
    expect(mergeStepLines(lines, null, 0).items).toBe(lines)
    expect(mergeStepLines(lines, details({ plain_lines: [plain(0, 0, 'Kren')] }), null).items).toBe(lines)
  })
})

describe('plain equipment and the ingredient list', () => {
  it('shapes plain equipment per step and once for the whole recipe', () => {
    const mirror = details({
      plain_equipment: [
        { step: 0, name: 'Mörser', count: 1, note: 'groß' },
        { step: 1, name: 'mörser', count: null, note: '' },
      ],
    })
    expect(plainEquipmentOf(mirror, 0).map((e) => [e.equipment.name, e.count, e.note])).toEqual([['Mörser', 1, 'groß']])
    expect(plainEquipmentOf(mirror, 2)).toEqual([])
    expect(allPlainEquipment(mirror)).toHaveLength(1)
  })

  it('sums plain lines of the same name and unit and adds the unlinked sub-recipes', () => {
    const mirror = details({
      plain_lines: [plain(0, 0, 'Kren', 20), plain(1, 0, 'kren', 10), plain(1, 1, 'Salz', null)],
      unlinked_sub_recipes: [{ step: 0, position: 2, title: null, amount: 1, unit: null }],
    })
    const extras = extraIngredients(mirror)
    expect(extras.map((e) => [e.name, e.amount, e.origin])).toEqual([
      ['Kren', 30, 'plain'],
      ['Salz', null, 'plain'],
      ['', 1, 'unlinked'],
    ])
  })
})

describe('attributionParams', () => {
  it('names the author and the instance, or only the instance', () => {
    expect(attributionParams({ instance_name: 'Friends', author_name: 'Mia' })).toEqual({
      key: 'recipes.mirror.byAt',
      params: { name: 'Mia', instance: 'Friends' },
    })
    expect(attributionParams({ instance_name: 'Friends', author_name: null }).key).toBe('recipes.mirror.from')
  })
})
