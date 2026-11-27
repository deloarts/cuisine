import { describe, expect, it } from 'vitest'

import { emptyValues } from '@/shared/composables/urlFilters'
import type { IngredientResponse } from '@/shared/cookbook/types'
import {
  INGREDIENT_FILTERS,
  matchesClientFilters,
  needsClientFiltering,
  serverQuery,
  serverSort,
} from '@/features/ingredients/ingredientFilters'

const none = () => emptyValues(INGREDIENT_FILTERS)

function ingredient(extra: Partial<IngredientResponse>): IngredientResponse {
  return {
    allergens: [],
    diet_markers: [],
    nutrition: { kcal: null },
    ...extra,
  } as IngredientResponse
}

describe('ingredient filters', () => {
  it('sends only what the backend knows', () => {
    const f = { ...none(), q: 'egg', status: 'draft', mine: true, allergens: ['eggs'] }
    expect(serverQuery(f)).toEqual({
      search: 'egg',
      category_id: null,
      family_id: null,
      status: 'draft',
      mine: true,
      min_usage: null,
      max_usage: null,
    })
    expect(serverQuery({ ...none(), status: 'bogus' }).status).toBeNull()
  })

  it('filters in the browser only for allergens, diet markers and energy', () => {
    expect(needsClientFiltering({ ...none(), q: 'egg', mine: true })).toBe(false)
    expect(needsClientFiltering({ ...none(), kcalMax: 100 })).toBe(true)
  })

  it('matches any chosen allergen or marker and an inclusive energy range', () => {
    const egg = ingredient({ allergens: ['eggs'], diet_markers: ['eggs'], nutrition: { kcal: 143 } })
    expect(matchesClientFilters(egg, { ...none(), allergens: ['milk', 'eggs'] })).toBe(true)
    expect(matchesClientFilters(egg, { ...none(), diets: ['meat'] })).toBe(false)
    expect(matchesClientFilters(egg, { ...none(), kcalMin: 143, kcalMax: 143 })).toBe(true)
    expect(matchesClientFilters(egg, { ...none(), kcalMax: 100 })).toBe(false)
    expect(matchesClientFilters(ingredient({}), { ...none(), kcalMin: 0 })).toBe(false)
  })

  it('matches an ingredient in season in any chosen month', () => {
    const asparagus = ingredient({ season_months: [4, 5, 6] })
    expect(needsClientFiltering({ ...none(), season: ['5'] })).toBe(true)
    expect(matchesClientFilters(asparagus, { ...none(), season: ['1', '5'] })).toBe(true)
    expect(matchesClientFilters(asparagus, { ...none(), season: ['12'] })).toBe(false)
  })
  it('filters by the usage range on the server', () => {
    const f = { ...none(), usageMin: 1, usageMax: 3 }
    expect(serverQuery(f)).toMatchObject({ min_usage: 1, max_usage: 3 })
    expect(needsClientFiltering(f)).toBe(false)
  })

  it('sends a sort only for usage and for name descending', () => {
    expect(serverSort('usage', -1)).toEqual({ sort: 'usage', order: 'desc' })
    expect(serverSort('usage', 1)).toEqual({ sort: 'usage', order: 'asc' })
    expect(serverSort('q', -1)).toEqual({ sort: 'name', order: 'desc' })
    expect(serverSort('q', 1)).toEqual({})
    expect(serverSort(undefined, 1)).toEqual({})
  })
})
