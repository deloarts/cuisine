/** The home page's calls to the web API, mocked by its specs. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type HomeResponse = Schemas['HomeResponse']
export type CookEventResponse = Schemas['CookEventResponse']
export type FoodFactResponse = Schemas['FoodFactResponse']
export type ShoppingListSummary = Schemas['ShoppingListSummaryResponse']

export function getHome() {
  return webApi.get('/home')
}

export function getShoppingLists() {
  return webApi.get('/shopping-lists')
}

export function setFavourite(recipeId: string, favourite: boolean) {
  return webApi.put('/recipes/{recipe_id}/favourite', {
    path: { recipe_id: recipeId },
    body: { favourite },
  })
}
