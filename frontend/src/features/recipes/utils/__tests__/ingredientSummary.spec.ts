import { describe, expect, it } from 'vitest'

import {
  listSuggestions,
  stepOnlyLines,
  usageOf,
  type SummaryLine,
  type WeightsOf,
} from '@/features/recipes/utils/ingredientSummary'
import type { UnitResponse } from '@/shared/cookbook/types'

function unit(id: string, kind: string, toBase: number | null): UnitResponse {
  return {
    ...({} as UnitResponse),
    id,
    code: id,
    kind,
    to_base: toBase,
    name: id,
    plural_name: id,
    abbreviation: id,
    sort_order: 0,
  }
}

const units = [
  unit('g', 'mass', 1),
  unit('kg', 'mass', 1000),
  unit('ml', 'volume', 1),
  unit('l', 'volume', 1000),
  unit('cup', 'volume', 240),
  unit('pc', 'count', null),
]

const line = (amount: number | null, unitId: string | null, id = 'flour'): SummaryLine => ({
  ingredient_id: id,
  sub_recipe_id: null,
  ingredient_name: id,
  amount,
  unit_id: unitId,
})

const noWeights: WeightsOf = () => null
// Flour weighs 120 g a cup and an egg 60 g a piece.
const weights: WeightsOf = (id) =>
  id === 'flour'
    ? { density_g_per_ml: null, conversions: [{ unit_id: 'cup', grams: 120 } as never] }
    : id === 'egg'
      ? { density_g_per_ml: null, conversions: [{ unit_id: 'pc', grams: 60 } as never] }
      : null

describe('usageOf', () => {
  it('says a line no step uses is unused', () => {
    expect(usageOf([line(200, 'g')], [], units, noWeights)).toEqual({ state: 'unused' })
  })

  it('compares in one unit and names the part no step uses', () => {
    const usage = usageOf([line(500, 'g')], [line(200, 'g'), line(100, 'g')], units, noWeights)
    expect(usage).toMatchObject({ state: 'partly', missing: 200, unit: { id: 'g' } })
    expect(usageOf([line(300, 'g')], [line(200, 'g'), line(100, 'g')], units, noWeights)).toEqual({
      state: 'used',
    })
  })

  it('compares within one kind by the base unit', () => {
    expect(usageOf([line(1, 'l', 'milk')], [line(250, 'ml', 'milk')], units, noWeights)).toMatchObject({
      state: 'partly',
      missing: 750,
      unit: { id: 'ml' },
    })
    expect(usageOf([line(1, 'kg')], [line(1000, 'g')], units, noWeights)).toEqual({ state: 'used' })
  })

  it('compares in grams when every unit can be weighed', () => {
    expect(usageOf([line(300, 'g')], [line(1, 'cup')], units, weights)).toMatchObject({
      state: 'partly',
      missing: 180,
      symbol: 'g',
    })
    expect(usageOf([line(2, 'cup')], [line(240, 'g')], units, weights)).toEqual({ state: 'used' })
  })

  it('cannot check units that do not compare', () => {
    expect(usageOf([line(300, 'g')], [line(1, 'cup')], units, noWeights)).toEqual({ state: 'unchecked' })
    expect(usageOf([line(2, 'pc', 'egg')], [line(100, 'g', 'egg')], units, noWeights)).toEqual({
      state: 'unchecked',
    })
    // The steps say "to taste" while the list measures.
    expect(usageOf([line(5, 'g')], [line(null, null)], units, noWeights)).toEqual({ state: 'unchecked' })
  })

  it('takes any use in a step as enough for a "to taste" line', () => {
    expect(usageOf([line(null, null)], [line(5, 'g')], units, noWeights)).toEqual({ state: 'used' })
  })
})

describe('stepOnlyLines', () => {
  it('lists what only the steps name, summed in one unit, in step order', () => {
    const found = stepOnlyLines(
      [line(200, 'g')],
      [line(2, 'pc', 'egg'), line(100, 'g'), line(1, 'pc', 'egg'), line(50, 'ml', 'milk')],
      units,
      noWeights,
    )
    expect(found.map((l) => [l.ingredient_id, l.amount, l.unit_id])).toEqual([
      ['egg', 3, 'pc'],
      ['milk', 50, 'ml'],
    ])
  })

  it('sums in grams when every unit can be weighed and leaves the amount out otherwise', () => {
    expect(stepOnlyLines([], [line(1, 'cup'), line(30, 'g')], units, weights)[0]).toMatchObject({
      amount: 150,
      unit_id: 'g',
    })
    expect(stepOnlyLines([], [line(1, 'cup'), line(30, 'g')], units, noWeights)[0]).toMatchObject({
      amount: null,
      unit_id: null,
    })
  })

  it('treats a sub-recipe like an ingredient of its own', () => {
    const sub: SummaryLine = { ...line(1, null), ingredient_id: null, sub_recipe_id: 'r2', ingredient_name: 'Dough' }
    expect(stepOnlyLines([], [sub], units, noWeights)).toEqual([
      { key: 'recipe:r2', ingredient_id: null, sub_recipe_id: 'r2', ingredient_name: 'Dough', amount: 1, unit_id: null },
    ])
    expect(stepOnlyLines([sub], [sub], units, noWeights)).toEqual([])
  })
})

describe('listSuggestions', () => {
  it('offers an unused line with its declared amount and unit', () => {
    const [onion] = listSuggestions([line(2, 'pc', 'onion')], [], units, noWeights)
    expect(onion).toMatchObject({ key: 'ingredient:onion', amount: 2, unit_id: 'pc', usage: { state: 'unused' } })
  })

  it('offers an unused line listed to taste without an amount', () => {
    const [salt] = listSuggestions([line(null, null, 'salt')], [], units, noWeights)
    expect(salt).toMatchObject({ amount: null, unit_id: null, usage: { state: 'unused' } })
  })

  it('offers a partly used line with what is missing in the declared unit', () => {
    const [flour] = listSuggestions([line(1, 'kg')], [line(200, 'g')], units, noWeights)
    expect(flour).toMatchObject({ amount: 0.8, unit_id: 'kg', usage: { state: 'partly', missing: 800 } })
  })

  it('rounds the missing amount up, so adding it uses the line up', () => {
    // 1 cup of flour is 120 g; 50 g used leaves 70/120 of a cup.
    const declared = [line(1, 'cup')]
    const [flour] = listSuggestions(declared, [line(50, 'g')], units, weights)
    expect(flour!.amount).toBe(0.584)
    expect(listSuggestions(declared, [line(50, 'g'), line(flour!.amount, 'cup')], units, weights)).toEqual([])
  })

  it('leaves out lines the steps use up, and those it cannot check', () => {
    const declared = [line(200, 'g'), line(1, 'pc', 'egg'), line(null, null, 'salt')]
    const steps = [line(200, 'g'), line(100, 'ml', 'egg'), line(1, 'g', 'salt')]
    expect(listSuggestions(declared, steps, units, noWeights)).toEqual([])
  })

  it('counts several declared lines of one ingredient together', () => {
    const declared = [line(100, 'g'), line(200, 'g')]
    expect(listSuggestions(declared, [line(100, 'g')], units, noWeights)).toMatchObject([
      { amount: 200, unit_id: 'g' },
    ])
  })
})
