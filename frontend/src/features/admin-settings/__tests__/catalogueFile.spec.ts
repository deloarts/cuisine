import { describe, expect, it } from 'vitest'

import type { CataloguePreview } from '@/features/admin-settings/api/catalogueFile'
import {
  acceptKey,
  catalogueFileName,
  differenceRows,
  entryKeys,
  filterRows,
  newEntries,
  toggleAll,
} from '@/features/admin-settings/catalogueFile'

const preview: CataloguePreview = {
  source_instance_id: null,
  exported_at: '2026-11-22T10:00:00+00:00',
  kinds: [],
  conflicts: [],
  entries: [
    {
      kind: 'ingredient',
      source_id: 'p',
      name: 'Peanut',
      local_id: 'local-p',
      differences: [
        { field: 'allergens', current: ['peanuts'], incoming: ['nuts', 'peanuts'] },
        { field: 'nutrition.kcal', current: 560, incoming: 600 },
      ],
    },
    { kind: 'tag', source_id: 't', name: 'Brunch', local_id: 'local-t', differences: [{ field: 'color', current: null, incoming: '#123456' }] },
    { kind: 'ingredient', source_id: 'l', name: 'Lupin flour', local_id: null, differences: [] },
    { kind: 'category', source_id: 'c', name: 'Pantry', local_id: null, differences: [] },
    { kind: 'ingredient', source_id: 'a', name: 'Amaranth', local_id: null, differences: [] },
  ],
}

describe('catalogueFile', () => {
  it('turns every differing field into a row keyed like the import takes it', () => {
    const rows = differenceRows(preview)
    expect(rows.map((r) => r.id)).toEqual(['ingredient:p:allergens', 'ingredient:p:nutrition.kcal', 'tag:t:color'])
    expect(rows[0]).toMatchObject({ name: 'Peanut', current: ['peanuts'], incoming: ['nuts', 'peanuts'] })
    expect(acceptKey('unit', 'u', 'names.de-AT')).toBe('unit:u:names.de-AT')
  })

  it('groups the new entries per kind in the order the import writes them', () => {
    expect(newEntries(preview)).toEqual([
      { kind: 'category', names: ['Pantry'] },
      { kind: 'ingredient', names: ['Amaranth', 'Lupin flour'] },
    ])
  })

  it('accepts a whole entry at once, and none of it when all is accepted', () => {
    const rows = differenceRows(preview)
    const keys = entryKeys(rows, 'ingredient', 'p')
    expect(keys).toEqual(['ingredient:p:allergens', 'ingredient:p:nutrition.kcal'])
    const some = toggleAll(['ingredient:p:allergens', 'tag:t:color'], keys)
    expect(some.sort()).toEqual(['ingredient:p:allergens', 'ingredient:p:nutrition.kcal', 'tag:t:color'])
    expect(toggleAll(some, keys)).toEqual(['tag:t:color'])
  })

  it('filters by kind and by text', () => {
    const rows = differenceRows(preview)
    expect(filterRows(rows, 'tag', () => true).map((r) => r.id)).toEqual(['tag:t:color'])
    expect(filterRows(rows, null, (...texts) => texts.includes('nutrition.kcal')).map((r) => r.id)).toEqual([
      'ingredient:p:nutrition.kcal',
    ])
  })

  it('names the download after the day', () => {
    expect(catalogueFileName(new Date('2026-11-22T12:00:00Z'))).toBe('cuisine-catalogue-2026-11-22.json')
  })
})
