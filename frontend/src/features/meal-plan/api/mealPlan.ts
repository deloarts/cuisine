/** The meal plan's calls: the week's entries, suggestions, and putting planned recipes on a shopping list. */
import type { Schemas } from '@/core/api/generated'
import { webApi, type QueryOf, type WebRequestOptions } from '@/core/api/webRequest'
import type { MealSlot } from '@/shared/cookbook/types'

export type MealPlanSuggestion = Schemas['MealPlanSuggestionResponse']
export type SuggestionReason = Schemas['SuggestionReason']
export type MealPlanRequest = Schemas['MealPlanRequest']
export type MealPlanEntry = Schemas['MealPlanEntryResponse']
export type MealPlanQuery = QueryOf<'/meal-plan'>
export type ShoppingListSummary = Schemas['ShoppingListSummaryResponse']

type EntryChanges = WebRequestOptions<'/meal-plan/{entry_id}', 'put'>['body']
type WeekToList = WebRequestOptions<'/meal-plan/shopping-list', 'post'>['body']
type RecipeToList = WebRequestOptions<'/shopping-lists/{list_id}/recipes', 'post'>['body']

export interface SuggestionQuery {
  date_from: string
  date_to: string
  scope?: Schemas['MealPlanScope']
  slot?: MealSlot
  limit?: number
}

export function getSuggestions(query: SuggestionQuery) {
  return webApi.get('/meal-plan/suggestions', { query })
}

export function planMeal(body: MealPlanRequest) {
  return webApi.post('/meal-plan', { body })
}

export function listEntries(query: MealPlanQuery): Promise<MealPlanEntry[]> {
  return webApi.get('/meal-plan', { query })
}

export function updateEntry(id: string, body: EntryChanges) {
  return webApi.put('/meal-plan/{entry_id}', { path: { entry_id: id }, body })
}

export function deleteEntry(id: string) {
  return webApi.delete('/meal-plan/{entry_id}', { path: { entry_id: id } })
}

/** Adds every planned recipe of a range to a shopping list in one call. */
export function addRangeToShoppingList(body: WeekToList) {
  return webApi.post('/meal-plan/shopping-list', { body })
}

/** Adds one recipe to a shopping list, with the sub-recipes bought for it. */
export function addRecipeToShoppingList(listId: string, body: RecipeToList) {
  return webApi.post('/shopping-lists/{list_id}/recipes', { path: { list_id: listId }, body })
}

export function listShoppingLists(): Promise<ShoppingListSummary[]> {
  return webApi.get('/shopping-lists')
}

/** One recipe's detail, read for the sub-recipes it needs. */
export function getRecipe(id: string) {
  return webApi.get('/recipes/{recipe_id}', { path: { recipe_id: id } })
}
