import { describe, expect, it } from 'vitest'

import type { EquipmentResponse } from '@/shared/cookbook/types'
import { groupByKind, initialSelection } from '@/features/kitchen/kitchen'

function item(id: string, name: string, kind: string, extra: Partial<EquipmentResponse> = {}): EquipmentResponse {
  return { id, name, kind, basic: false, status: 'active', aliases: {}, ...extra } as EquipmentResponse
}

const catalogue = [
  item('knife', 'Messer', 'utensil', { basic: true }),
  item('pot', 'Topf', 'cookware', { basic: true, aliases: { 'de-AT': ['Kochtopf'] } }),
  item('mixer', 'Küchenmaschine', 'appliance'),
  item('whisk', 'Schneebesen', 'utensil'),
  item('draft', 'Spiralschneider', 'utensil', { status: 'draft', basic: true }),
]

describe('my kitchen', () => {
  it('ticks the basic items before the kitchen is set up, drafts left out', () => {
    expect([...initialSelection({ set_up: false, equipment: [] }, catalogue)].sort()).toEqual(['knife', 'pot'])
  })

  it('ticks the kitchen\'s own items once it is set up', () => {
    expect([...initialSelection({ set_up: true, equipment: [{ id: 'mixer' }] }, catalogue)]).toEqual(['mixer'])
  })

  it('groups by kind in catalogue order, sorted by name, and searches other names', () => {
    const groups = groupByKind(catalogue, new Set())
    expect(groups.map((g) => g.kind)).toEqual(['cookware', 'appliance', 'utensil'])
    expect(groups.at(-1)?.items.map((i) => i.name)).toEqual(['Messer', 'Schneebesen'])
    expect(groupByKind(catalogue, new Set(), 'kochtopf').flatMap((g) => g.items.map((i) => i.id))).toEqual(['pot'])
  })

  it('shows a draft only when it is already ticked', () => {
    const ids = (selected: Set<string>) => groupByKind(catalogue, selected).flatMap((g) => g.items.map((i) => i.id))
    expect(ids(new Set())).not.toContain('draft')
    expect(ids(new Set(['draft']))).toContain('draft')
  })
})
