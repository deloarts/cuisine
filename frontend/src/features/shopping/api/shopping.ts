/** The shopping lists' calls: the lists and their notes, one list's items, and adding a recipe to a list. */
import type { Schemas } from '@/core/api/generated'
import { webApi, type WebRequestOptions } from '@/core/api/webRequest'

export type ShoppingList = Schemas['ShoppingListResponse']
export type ShoppingListSummary = Schemas['ShoppingListSummaryResponse']
export type ShoppingListNote = Schemas['ShoppingListNoteResponse']

type ListForm = WebRequestOptions<'/shopping-lists', 'post'>['body']
type ListChanges = WebRequestOptions<'/shopping-lists/{list_id}', 'put'>['body']
type NewItem = WebRequestOptions<'/shopping-lists/{list_id}/items', 'post'>['body']
type ItemChanges = WebRequestOptions<'/shopping-lists/{list_id}/items/{item_id}', 'patch'>['body']
type RecipeToList = WebRequestOptions<'/shopping-lists/{list_id}/recipes', 'post'>['body']

export const listShoppingLists = (): Promise<ShoppingListSummary[]> => webApi.get('/shopping-lists')

export const createShoppingList = (body: ListForm) => webApi.post('/shopping-lists', { body })

export const listShoppingListNotes = (): Promise<ShoppingListNote[]> => webApi.get('/shopping-lists/notes')

export const dismissShoppingListNote = (id: string) =>
  webApi.delete('/shopping-lists/notes/{note_id}', { path: { note_id: id } })

export const getShoppingList = (id: string): Promise<ShoppingList> =>
  webApi.get('/shopping-lists/{list_id}', { path: { list_id: id } })

export const updateShoppingList = (id: string, body: ListChanges): Promise<ShoppingList> =>
  webApi.put('/shopping-lists/{list_id}', { path: { list_id: id }, body })

export const deleteShoppingList = (id: string) => webApi.delete('/shopping-lists/{list_id}', { path: { list_id: id } })

export const leaveShoppingList = (id: string) =>
  webApi.post('/shopping-lists/{list_id}/leave', { path: { list_id: id } })

export const addShoppingItem = (id: string, body: NewItem): Promise<ShoppingList> =>
  webApi.post('/shopping-lists/{list_id}/items', { path: { list_id: id }, body })

export const updateShoppingItem = (id: string, itemId: string, body: ItemChanges): Promise<ShoppingList> =>
  webApi.patch('/shopping-lists/{list_id}/items/{item_id}', { path: { list_id: id, item_id: itemId }, body })

export const removeShoppingItem = (id: string, itemId: string): Promise<ShoppingList> =>
  webApi.delete('/shopping-lists/{list_id}/items/{item_id}', { path: { list_id: id, item_id: itemId } })

export const clearCheckedItems = (id: string) =>
  webApi.post('/shopping-lists/{list_id}/clear-checked', { path: { list_id: id } })

export const addRecipeToShoppingList = (id: string, body: RecipeToList) =>
  webApi.post('/shopping-lists/{list_id}/recipes', { path: { list_id: id }, body })

/** The ingredients matching typed text, for the add-item suggestions. */
export const searchIngredients = (search: string, limit: number) =>
  webApi.get('/ingredients', { query: { search, limit } })

/** One recipe's detail, read for the sub-recipes it needs. */
export const getRecipe = (id: string) => webApi.get('/recipes/{recipe_id}', { path: { recipe_id: id } })
