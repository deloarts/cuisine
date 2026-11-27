import { describe, expect, it } from 'vitest'

import { visibleTabs } from '@/features/admin-settings/adminTabs'
import {
  mayDecide,
  suggestionKey,
  suggestionRows,
  type PeerSuggestionGroup,
} from '@/features/admin-settings/peerSuggestions'

const peer = { id: 'p1', name: 'Friends' }

const groups: PeerSuggestionGroup[] = [
  {
    kind: 'ingredient',
    id: 'i1',
    name: 'Kren',
    warning: true,
    suggestions: [
      { peer, source_id: 's1', field: 'allergens', current: [], suggested: ['mustard'], unmapped_units: [] },
      { peer, source_id: 's1', field: 'conversions', current: {}, suggested: { tbsp: 15 }, unmapped_units: ['scoop'] },
    ],
  },
  {
    kind: 'unit',
    id: 'u1',
    name: 'Esslöffel',
    warning: false,
    suggestions: [{ peer, source_id: 's2', field: 'to_base', current: 15, suggested: 14.8, unmapped_units: [] }],
  },
]

describe('peerSuggestions', () => {
  it('flattens the groups into rows in the order the backend sent', () => {
    const rows = suggestionRows(groups)
    expect(rows.map((r) => [r.name, r.field])).toEqual([
      ['Kren', 'allergens'],
      ['Kren', 'conversions'],
      ['Esslöffel', 'to_base'],
    ])
    expect(rows[0]).toMatchObject({ kind: 'ingredient', entryId: 'i1', id: 'p1:ingredient:s1:allergens' })
    expect(rows[1]?.unmapped_units).toEqual(['scoop'])
  })

  it('keys a suggestion by peer, kind, source entry and field', () => {
    expect(suggestionKey({ peer, kind: 'tag', source_id: 'x', field: 'color' })).toBe('p1:tag:x:color')
  })

  it('needs the catalogue file rights of the kind to decide', () => {
    const has = (granted: string[]) => (p: string) => granted.includes(p)
    expect(mayDecide('ingredient', has(['manage:ingredients']))).toBe(false)
    expect(mayDecide('ingredient', has(['manage:ingredients', 'write:ingredients']))).toBe(true)
    expect(mayDecide('unit', has(['manage:ingredients', 'write:ingredients']))).toBe(false)
    expect(mayDecide('equipment', has(['write:resources']))).toBe(true)
  })

  it('shows the section only while peering is on', () => {
    const settings = (p: string) => p === 'read:settings'
    const catalogue = (featureOn: (f: string) => boolean) =>
      visibleTabs(settings, featureOn)
        .find((t) => t.value === 'catalogue')
        ?.sections.map((s) => s.key)
    expect(catalogue(() => false)).toEqual(['referenceUpdates'])
    expect(catalogue((f) => f === 'peering')).toEqual(['referenceUpdates', 'peerSuggestions'])
  })
})
