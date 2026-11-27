import { describe, expect, it } from 'vitest'

import type { IngredientAmount } from '@/features/recipes/api/recipes'
import {
  formatAmount,
  scaleFactor,
  scaleIngredients,
  unitLabel,
} from '@/features/recipes/utils/scaling'

function item(amount: number | null, unit: Partial<NonNullable<IngredientAmount['unit']>> | null = null): IngredientAmount {
  return {
    ingredient_id: 'onion',
    name: 'Onion',
    amount,
    unit: unit
      ? { id: 'u', code: 'x', kind: 'count', name: 'piece', plural_name: 'pieces', abbreviation: '', ...unit }
      : null,
    note: '',
  }
}

describe('servings scaling', () => {
  it('scales by the ratio of chosen to base servings', () => {
    expect(scaleFactor(6, 4)).toBe(1.5)
    expect(scaleFactor(2, 4)).toBe(0.5)
  })

  it('falls back to no scaling for nonsense servings', () => {
    expect(scaleFactor(0, 4)).toBe(1)
    expect(scaleFactor(4, 0)).toBe(1)
  })

  it('scales every amount and keeps "to taste" as it is', () => {
    const scaled = scaleIngredients([item(200), item(null)], 1.5)
    expect(scaled.map((i) => i.amount)).toEqual([300, null])
  })
})

describe('formatAmount', () => {
  it('shows small counts as fractions', () => {
    expect(formatAmount(0.5, 'en-GB')).toBe('½')
    expect(formatAmount(1.25, 'en-GB')).toBe('1 ¼')
    expect(formatAmount(2 / 3, 'en-GB')).toBe('⅔')
  })

  it('keeps decimals for mass and volume', () => {
    expect(formatAmount(0.5, 'en-GB', 'volume')).toBe('0.5')
    expect(formatAmount(0.5, 'de-AT', 'volume')).toBe('0,5')
  })

  it('rounds large amounts to whole numbers', () => {
    expect(formatAmount(333.333, 'en-GB', 'mass')).toBe('333')
    expect(formatAmount(1234, 'en-GB', 'mass')).toBe('1,234')
  })

  it('is empty for no amount', () => {
    expect(formatAmount(null, 'en-GB')).toBe('')
  })
})

describe('unitLabel', () => {
  it('prefers the abbreviation', () => {
    expect(unitLabel(item(200, { abbreviation: 'g', name: 'gram' }))).toBe('g')
  })

  it('uses the plural above one', () => {
    expect(unitLabel(item(2))).toBe('')
    expect(unitLabel(item(2, {}))).toBe('pieces')
    expect(unitLabel(item(1, {}))).toBe('piece')
  })
})
