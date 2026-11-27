import { describe, expect, it } from 'vitest'

import type { UnitResponse } from '@/shared/cookbook/types'
import { gramsPerUnit, groupUnits, unitBase, unitSearchText, unitShortLabel } from '@/shared/cookbook/units'

function unit(code: string, kind: string, toBase: number | null, sortOrder: number, extra: Partial<UnitResponse> = {}): UnitResponse {
  return {
    id: `u-${code}`,
    seeded: true,
    code,
    kind,
    to_base: toBase,
    sort_order: sortOrder,
    name: code,
    plural_name: code,
    abbreviation: code,
    translations: {},
    ...extra,
  } as UnitResponse
}

const g = unit('g', 'mass', 1, 10, { name: 'Gram' })
const dag = unit('dag', 'mass', 10, 20, { name: 'Decagram', plural_name: 'Decagrams' })
const ml = unit('ml', 'volume', 1, 30)
const cl = unit('cl', 'volume', 10, 40)
const piece = unit('piece', 'count', null, 50, { abbreviation: '', name: 'Piece' })

describe('groupUnits', () => {
  it('groups by kind in list order and sorts within a kind, leaving out empty kinds', () => {
    const groups = groupUnits([piece, cl, dag, ml, g])
    expect(groups.map((gr) => gr.kind)).toEqual(['mass', 'volume', 'count'])
    expect(groups[0]?.units.map((u) => u.code)).toEqual(['g', 'dag'])
    expect(groups[1]?.units.map((u) => u.code)).toEqual(['ml', 'cl'])
  })
})

describe('unitBase', () => {
  it('says what a unit is worth in grams or millilitres', () => {
    expect(unitBase(dag)).toEqual({ amount: 10, symbol: 'g' })
    expect(unitBase(cl)).toEqual({ amount: 10, symbol: 'ml' })
  })

  it('adds nothing for the base unit itself or a unit without a factor', () => {
    expect(unitBase(g)).toBeNull()
    expect(unitBase(piece)).toBeNull()
  })
})

describe('labels and search', () => {
  it('shows the abbreviation, or the name when there is none', () => {
    expect(unitShortLabel(dag)).toBe('dag')
    expect(unitShortLabel(piece)).toBe('Piece')
  })

  it('finds a unit by abbreviation, names and code', () => {
    expect(unitSearchText(dag)).toBe('dag Decagram Decagrams dag')
  })
})

describe('gramsPerUnit', () => {
  const flour = { density_g_per_ml: 0.6, conversions: [] }

  it('weighs a mass unit by its factor', () => {
    expect(gramsPerUnit(dag, flour)).toBe(10)
  })

  it('weighs a volume unit by its factor and the density', () => {
    expect(gramsPerUnit(cl, flour)).toBeCloseTo(6)
    expect(gramsPerUnit(cl, { density_g_per_ml: null, conversions: [] })).toBeNull()
  })

  it('lets the ingredient\'s own conversion win', () => {
    const egg = {
      density_g_per_ml: null,
      conversions: [{ unit_id: piece.id, unit_code: 'piece', unit_name: 'Piece', grams: 55 }],
    }
    expect(gramsPerUnit(piece, egg)).toBe(55)
    expect(gramsPerUnit(piece, flour)).toBeNull()
  })
})
