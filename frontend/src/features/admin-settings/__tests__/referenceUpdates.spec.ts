import { describe, expect, it } from 'vitest'

import {
  fieldName,
  filterUpdates,
  formatValue,
  isSafetyField,
  rowKey,
  type ReferenceUpdate,
} from '@/features/admin-settings/referenceUpdates'

const labels = {
  marker: (field: string, key: string) => `${field}:${key}`,
  month: (m: number) => `M${m}`,
  yes: 'yes',
  no: 'no',
  empty: '–',
}

const row = (kind: string, name: string, field: string) =>
  ({ kind, key: name.toLowerCase(), name, field, current: null, seed: null, base: null }) as ReferenceUpdate

describe('referenceUpdates', () => {
  it('splits a field id into its family and detail', () => {
    expect(fieldName('names.de-AT')).toEqual({ base: 'names', detail: 'de-AT', known: true })
    expect(fieldName('allergens')).toEqual({ base: 'allergens', detail: null, known: true })
    expect(fieldName('something.new').known).toBe(false)
  })

  it('marks allergens and diet markers as safety fields', () => {
    expect(isSafetyField('allergens')).toBe(true)
    expect(isSafetyField('diet_markers')).toBe(true)
    expect(isSafetyField('nutrition.kcal')).toBe(false)
  })

  it('formats every kind of stored value', () => {
    expect(formatValue('allergens', ['milk', 'eggs'], labels)).toBe('allergens:milk, allergens:eggs')
    expect(formatValue('season_months', [6, 7], labels)).toBe('M6, M7')
    expect(formatValue('names.en-GB', ['Gram', null, 'g'], labels)).toBe('Gram / – / g')
    expect(formatValue('conversions', { piece: 50 }, labels)).toBe('piece: 50')
    expect(formatValue('basic', true, labels)).toBe('yes')
    expect(formatValue('nutrition.kcal', 52, labels)).toBe('52')
    expect(formatValue('allergens', [], labels)).toBe('–')
    expect(formatValue('icon', null, labels)).toBe('–')
  })

  it('keys rows by kind, key and field', () => {
    expect(rowKey(row('unit', 'Gram', 'names.en-GB'))).toBe('unit:gram:names.en-GB')
  })

  it('filters by kind and text', () => {
    const rows = [row('ingredient', 'Milk', 'allergens'), row('unit', 'Gram', 'to_base')]
    const all = () => true
    expect(filterUpdates(rows, 'unit', all).map((r) => r.name)).toEqual(['Gram'])
    expect(filterUpdates(rows, null, (...t) => t.includes('Milk')).map((r) => r.name)).toEqual(['Milk'])
  })
})
