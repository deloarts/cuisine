import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import type { NeededEntry, PeerMapping } from '@/features/admin-settings/api/peering'
import {
  ACTIONS,
  decisionRequests,
  entryKey,
  incompleteKeys,
  initialDecision,
  mappingDecision,
  missingKeysOf,
} from '@/features/admin-settings/incomingRecipes'

function entry(kind: NeededEntry['kind'], id: string, overrides: Partial<NeededEntry> = {}): NeededEntry {
  return {
    kind,
    source_id: id,
    name: id,
    names: { 'de-AT': id },
    suggestion: null,
    category_suggestion: null,
    allergens: [],
    diet_markers: [],
    ...overrides,
  }
}

describe('incoming recipe decisions', () => {
  it('offers each kind only the decisions the backend takes', () => {
    expect(ACTIONS.unit).toEqual(['map', 'none'])
    expect(ACTIONS.tag).toEqual(['map', 'create', 'none'])
    expect(ACTIONS.ingredient).toEqual(['map', 'create', 'plain'])
  })

  it('starts at the suggestion, else creates ingredients and equipment and leaves units and tags out', () => {
    expect(initialDecision(entry('ingredient', 'i1', { suggestion: { id: 'kren', name: 'Kren' } }))).toEqual({
      action: 'map',
      target_id: 'kren',
      target_name: 'Kren',
      category_id: null,
    })
    expect(initialDecision(entry('ingredient', 'i2', { category_suggestion: { id: 'veg', name: 'Gemüse' } }))).toMatchObject({
      action: 'create',
      category_id: 'veg',
    })
    expect(initialDecision(entry('equipment', 'e1')).action).toBe('create')
    expect(initialDecision(entry('tag', 't1')).action).toBe('none')
    expect(initialDecision(entry('unit', 'u1')).action).toBe('none')
  })

  it('finds maps without a target and builds the request with only what each action needs', () => {
    const entries = [entry('ingredient', 'i1'), entry('ingredient', 'i2'), entry('tag', 't1')]
    const states = {
      'ingredient:i1': { action: 'create' as const, target_id: 'x', target_name: null, category_id: 'veg' },
      'ingredient:i2': { action: 'map' as const, target_id: null, target_name: null, category_id: 'veg' },
      'tag:t1': { action: 'none' as const, target_id: null, target_name: null, category_id: null },
    }
    expect(incompleteKeys(entries, states)).toEqual(['ingredient:i2'])
    expect(decisionRequests(entries, states)).toEqual([
      { kind: 'ingredient', source_id: 'i1', action: 'create', target_id: null, category_id: 'veg' },
      { kind: 'ingredient', source_id: 'i2', action: 'map', target_id: null, category_id: null },
      { kind: 'tag', source_id: 't1', action: 'none', target_id: null, category_id: null },
    ])
  })

  it('reads the entries a refused accept names as missing', () => {
    const config = { headers: new AxiosHeaders() }
    const refused = new AxiosError('x', 'ERR', config, null, {
      status: 422,
      statusText: '',
      headers: {},
      config,
      data: { code: 'PeerMappingError', missing: ['unit:u1', 7] },
    })
    expect(missingKeysOf(refused)).toEqual(['unit:u1'])
    expect(missingKeysOf(new Error('x'))).toEqual([])
    expect(entryKey({ kind: 'unit', source_id: 'u1' })).toBe('unit:u1')
  })

  it('starts a correction at the current mapping', () => {
    const mapping: PeerMapping = {
      kind: 'unit',
      source_id: 'u1',
      name: 'Gramm',
      action: null,
      target_id: null,
      target_name: null,
      created_here: false,
      matched_by: null,
      used_by: 0,
      updated: '2026-11-22T10:00:00Z',
    }
    expect(mappingDecision(mapping).action).toBe('map')
    expect(mappingDecision({ ...mapping, action: 'none' }).action).toBe('none')
  })
})
