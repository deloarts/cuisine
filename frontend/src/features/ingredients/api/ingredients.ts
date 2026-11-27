/**
 * The ingredient calls: the list, the editor round trip, the deletion
 * impact, merging, the near-duplicate check, the USDA lookup, the nutrition
 * credit and the extended nutrient catalogue. Kept in one module so specs can
 * mock them.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi, type QueryOf, type WebRequestOptions } from '@/core/api/webRequest'
import type { ContentLocale } from '@/shared/cookbook/types'

export type IngredientDeletionImpact = Schemas['IngredientDeletionImpact']
export type IngredientDetail = Schemas['IngredientDetailResponse']
export type DuplicateCandidate = Schemas['DuplicateCandidate']
export type NutritionSources = Schemas['NutritionSourcesResponse']
export type ExtendedNutrient = Schemas['ExtendedNutrientResponse']
export type FoodMatch = Schemas['FoodMatchResponse']
export type IngredientListQuery = QueryOf<'/ingredients'>
export type IngredientForm = WebRequestOptions<'/ingredients', 'post'>['body']

export const listIngredients = (query: IngredientListQuery) => webApi.get('/ingredients', { query })

export const getIngredient = (id: string): Promise<IngredientDetail> =>
  webApi.get('/ingredients/{ingredient_id}', { path: { ingredient_id: id } })

export const createIngredient = (body: IngredientForm): Promise<IngredientDetail> =>
  webApi.post('/ingredients', { body })

export const updateIngredient = (id: string, body: IngredientForm): Promise<IngredientDetail> =>
  webApi.put('/ingredients/{ingredient_id}', { path: { ingredient_id: id }, body })

export const activateIngredient = (id: string) =>
  webApi.post('/ingredients/{ingredient_id}/activate', { path: { ingredient_id: id } })

export const searchUsda = (query: string, limit: number): Promise<FoodMatch[]> =>
  webApi.get('/nutrition/usda/search', { query: { query, limit } })

export const ingredientDeletionImpact = (id: string): Promise<IngredientDeletionImpact> =>
  webApi.get('/ingredients/{ingredient_id}/deletion-impact', { path: { ingredient_id: id } })

export const mergeIngredient = (id: string, intoId: string): Promise<IngredientDetail> =>
  webApi.post('/ingredients/{ingredient_id}/merge', { path: { ingredient_id: id }, body: { into_id: intoId } })

export const deleteIngredient = (id: string) =>
  webApi.delete('/ingredients/{ingredient_id}', { path: { ingredient_id: id } })

export const ingredientDuplicates = (name: string, locale: ContentLocale): Promise<DuplicateCandidate[]> =>
  webApi.get('/ingredients/duplicates', { query: { name, locale } })

let sources: Promise<NutritionSources> | null = null
let nutrients: Promise<ExtendedNutrient[]> | null = null

/** The credit line for the nutrition data, fetched once per page load. */
export function nutritionSources(): Promise<NutritionSources> {
  sources ??= webApi.get('/nutrition/sources').catch((err: unknown) => {
    sources = null
    throw err
  })
  return sources
}

/** The extended nutrient catalogue in display order, fetched once per page load. */
export function extendedNutrients(): Promise<ExtendedNutrient[]> {
  nutrients ??= webApi.get('/nutrition/nutrients').catch((err: unknown) => {
    nutrients = null
    throw err
  })
  return nutrients
}
