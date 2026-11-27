/**
 * The recipes feature's calls to the web API. Views and composables import
 * from here, so a spec mocks this module instead of axios.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi, type QueryOf } from '@/core/api/webRequest'
import type { ContentLocale } from '@/shared/cookbook/types'

export type RecipeSummaryResponse = Schemas['RecipeSummaryResponse']
export type RecipeDetailResponse = Schemas['RecipeDetailResponse']
export type RecipeEditResponse = Schemas['RecipeEditResponse']
export type RecipeRequest = Schemas['RecipeRequest']
export type TranslationRequest = Schemas['TranslationRequest']
export type IngredientAmount = Schemas['IngredientAmount']
export type StepView = Schemas['StepView']
export type TagResponse = Schemas['TagResponse']
export type UnitResponse = Schemas['UnitResponse']
export type IngredientResponse = Omit<Schemas['IngredientListItem'], 'usage_count'>
export type IngredientRequest = Schemas['IngredientRequest']
export type CookEventResponse = Schemas['CookEventResponse']
export type RatingResponse = Schemas['RatingResponse']
export type NoteResponse = Schemas['NoteResponse']
export type StoredFileResponse = Schemas['StoredFileResponse']
export type StepImageResponse = Schemas['StepImageResponse']
export type Difficulty = Schemas['Difficulty']
export type Diet = Schemas['Diet']
export type RecipeVisibility = Schemas['RecipeVisibility']
export type SubRecipeRef = Schemas['SubRecipeRef']
export type SubRecipeNeed = Schemas['SubRecipeNeed']
export type RecipeDeletionImpact = Schemas['RecipeDeletionImpact']
export type PrivacySettings = Schemas['PrivacySettingsSchema']
export type RecipeListQuery = QueryOf<'/recipes'>
export type VariationResponse = Schemas['VariationResponse']
export type VariationViewResponse = Schemas['VariationViewResponse']
export type VariationRequest = Schemas['VariationRequest']
export type VariationChangeRequest = Schemas['VariationChangeRequest']
export type VariationChangeView = Schemas['VariationChangeView']
export type VariationChangeKind = Schemas['VariationChangeKind']
export type StepMarkerView = Schemas['StepMarkerView']
export type StaleStepView = Schemas['StaleStepView']
export type RecipeCopyResponse = Schemas['RecipeCopyResponse']
export type PersonRef = Schemas['PersonRef']
export type PeerRef = Schemas['PeerRef']

export function listRecipes(query: RecipeListQuery) {
  return webApi.get('/recipes', { query })
}

export interface RecipeReadOptions {
  servings?: number
  locale?: ContentLocale
  /** Dinner guests' user ids; the answer only says whether someone won't like it. */
  guests?: string[]
}

export function getRecipe(id: string, options: RecipeReadOptions = {}) {
  return webApi.get('/recipes/{recipe_id}', {
    path: { recipe_id: id },
    query: {
      servings: options.servings ?? null,
      locale: options.locale ?? null,
      guests: options.guests ?? [],
    },
  })
}

/** The paired instances the user may share a recipe with; empty while peering is off. */
export function listShareTargets() {
  return webApi.get('/peers/share-targets')
}

export function getRecipeForEdit(id: string) {
  return webApi.get('/recipes/{recipe_id}/edit', { path: { recipe_id: id } })
}

export function createRecipe(body: RecipeRequest) {
  return webApi.post('/recipes', { body })
}

export function updateRecipe(id: string, body: RecipeRequest) {
  return webApi.put('/recipes/{recipe_id}', { path: { recipe_id: id }, body })
}

export function saveTranslation(id: string, body: TranslationRequest) {
  return webApi.put('/recipes/{recipe_id}/translation', { path: { recipe_id: id }, body })
}

export function publishRecipe(id: string) {
  return webApi.post('/recipes/{recipe_id}/publish', { path: { recipe_id: id } })
}

export function unpublishRecipe(id: string) {
  return webApi.post('/recipes/{recipe_id}/unpublish', { path: { recipe_id: id } })
}

export function deleteRecipe(id: string) {
  return webApi.delete('/recipes/{recipe_id}', { path: { recipe_id: id } })
}

export function setFavourite(id: string, favourite: boolean) {
  return webApi.put('/recipes/{recipe_id}/favourite', {
    path: { recipe_id: id },
    body: { favourite },
  })
}

/** Rates the recipe itself, or with `variationId` one of its variations. */
export function rateRecipe(id: string, stars: number, comment: string, variationId: string | null = null) {
  return webApi.put('/recipes/{recipe_id}/rating', {
    path: { recipe_id: id },
    body: { stars, comment, variation_id: variationId },
  })
}

/** Answers the new average and count of what was rated, so the page needs no reload. */
export function removeRating(id: string, variationId: string | null = null) {
  return webApi.delete('/recipes/{recipe_id}/rating', {
    path: { recipe_id: id },
    query: { variation_id: variationId },
  })
}

export function saveNote(id: string, text: string) {
  return webApi.put('/recipes/{recipe_id}/note', { path: { recipe_id: id }, body: { text } })
}

export function listRecipeCookEvents(id: string, mine = false) {
  return webApi.get('/recipes/{recipe_id}/cook-events', {
    path: { recipe_id: id },
    query: { mine },
  })
}

export function getDeletionImpact(id: string) {
  return webApi.get('/recipes/{recipe_id}/deletion-impact', { path: { recipe_id: id } })
}

export function getPrivacySettings() {
  return webApi.get('/settings/privacy')
}

/** Recipes a step line can use as a sub-recipe, found by title. */
export function searchRecipes(search: string, limit = 10) {
  return webApi.get('/recipes', { query: { search, limit, sort: 'title' } })
}

/** Every group by id and name, readable without the right to manage groups. */
export function listGroups() {
  return webApi.get('/groups/directory')
}

export function listShoppingLists() {
  return webApi.get('/shopping-lists')
}

export function addRecipeToList(
  listId: string,
  recipeId: string,
  servings: number,
  boughtSubRecipeIds: string[],
) {
  return webApi.post('/shopping-lists/{list_id}/recipes', {
    path: { list_id: listId },
    body: { recipe_id: recipeId, servings, bought_sub_recipe_ids: boughtSubRecipeIds },
  })
}

/** The viewer's household members, preselected as dinner guests. */
export function getMyHousehold() {
  return webApi.get('/households/mine')
}

export function logCookEvent(
  recipeId: string,
  cookedOn: string,
  servings: number,
  note: string,
  variationId: string | null = null,
) {
  return webApi.post('/cook-events', {
    body: { recipe_id: recipeId, variation_id: variationId, cooked_on: cookedOn, servings, note },
  })
}

export function listVariations(recipeId: string) {
  return webApi.get('/recipes/{recipe_id}/variations', { path: { recipe_id: recipeId } })
}

export function getVariation(recipeId: string, variationId: string) {
  return webApi.get('/recipes/{recipe_id}/variations/{variation_id}', {
    path: { recipe_id: recipeId, variation_id: variationId },
  })
}

/** The recipe with the variation applied, plus a marker per step for what differs. */
export function viewVariation(recipeId: string, variationId: string, options: RecipeReadOptions = {}) {
  return webApi.get('/recipes/{recipe_id}/variations/{variation_id}/view', {
    path: { recipe_id: recipeId, variation_id: variationId },
    query: {
      servings: options.servings ?? null,
      locale: options.locale ?? null,
      guests: options.guests ?? [],
    },
  })
}

export function createVariation(recipeId: string, body: VariationRequest) {
  return webApi.post('/recipes/{recipe_id}/variations', { path: { recipe_id: recipeId }, body })
}

export function updateVariation(recipeId: string, variationId: string, body: VariationRequest) {
  return webApi.put('/recipes/{recipe_id}/variations/{variation_id}', {
    path: { recipe_id: recipeId, variation_id: variationId },
    body,
  })
}

export function deleteVariation(recipeId: string, variationId: string) {
  return webApi.delete('/recipes/{recipe_id}/variations/{variation_id}', {
    path: { recipe_id: recipeId, variation_id: variationId },
  })
}

/** Writes all changes (`changeIds` null) or the chosen ones into the original. */
export function adoptVariation(
  recipeId: string,
  variationId: string,
  changeIds: string[] | null,
  revisionNote: string | null = null,
) {
  return webApi.post('/recipes/{recipe_id}/variations/{variation_id}/adopt', {
    path: { recipe_id: recipeId, variation_id: variationId },
    body: { change_ids: changeIds, revision_note: revisionNote },
  })
}

export function listCoEditors(recipeId: string) {
  return webApi.get('/recipes/{recipe_id}/co-editors', { path: { recipe_id: recipeId } })
}

export function setCoEditors(recipeId: string, userIds: string[]) {
  return webApi.put('/recipes/{recipe_id}/co-editors', {
    path: { recipe_id: recipeId },
    body: { user_ids: userIds },
  })
}

/** "Copy as my recipe": an independent draft of the reader's, linked to the original. */
export function copyRecipe(recipeId: string) {
  return webApi.post('/recipes/{recipe_id}/copy', { path: { recipe_id: recipeId } })
}

/** The recipe as a `.cui` file, with its sub-recipes and variations. */
export async function exportRecipe(recipeId: string): Promise<Blob> {
  const data = await webApi.get('/recipes/{recipe_id}/export', {
    path: { recipe_id: recipeId },
    config: { responseType: 'blob' },
  })
  return data as Blob
}

export function listCopies(recipeId: string) {
  return webApi.get('/recipes/{recipe_id}/copies', { path: { recipe_id: recipeId } })
}

/** The people every signed-in user may look up by name. */
export function listPeople() {
  return webApi.get('/users/directory')
}

export function listTags() {
  return webApi.get('/tags')
}

export function listUnits() {
  return webApi.get('/units')
}

export function searchIngredients(search: string, limit = 20) {
  return webApi.get('/ingredients', { query: { search, limit } })
}

export function createIngredient(body: IngredientRequest) {
  return webApi.post('/ingredients', { body })
}

/**
 * The step image library: images other steps already show, those sharing the
 * most of the given ingredients and equipment first.
 */
export function listStepImages(query: {
  ingredientIds: string[]
  equipmentIds: string[]
  search?: string
  limit?: number
  offset?: number
}) {
  return webApi.get('/step-images', {
    query: {
      ingredient_id: query.ingredientIds,
      equipment_id: query.equipmentIds,
      search: query.search || undefined,
      limit: query.limit,
      offset: query.offset,
    },
  })
}

export function uploadImage(file: File) {
  const body = new FormData()
  body.append('file', file)
  return webApi.post('/files', { body })
}

/** The whole equipment catalogue, names in the reader's language, for the step picker. */
export function listEquipment() {
  return webApi.get('/equipment')
}
