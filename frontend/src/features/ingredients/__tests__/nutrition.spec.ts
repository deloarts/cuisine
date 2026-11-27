import { describe, expect, it } from 'vitest'

import { emptyNutrition, hasNutrition, mergeNutrition } from '@/features/ingredients/nutrition'

describe('nutrition helpers', () => {
  it('starts with every value unknown', () => {
    const empty = emptyNutrition()
    expect(Object.values(empty).every((v) => v === null)).toBe(true)
    expect(hasNutrition(empty)).toBe(false)
  })

  it('keeps typed values a lookup does not provide and rounds the found ones', () => {
    const current = { ...emptyNutrition(), kcal: 100, salt: 1.5 }
    const merged = mergeNutrition(current, { kcal: 88.456, protein: 3.14159, salt: null })
    expect(merged.kcal).toBe(88.46)
    expect(merged.protein).toBe(3.14)
    expect(merged.salt).toBe(1.5)
    expect(hasNutrition(merged)).toBe(true)
  })
})
