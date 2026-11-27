/**
 * Importing `.cui` files: the preview names, per recipe of the file, the
 * user's earlier import of it, and the import then updates the earlier
 * imports the user chose and adds every other recipe as a new draft.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type RecipeImportReport = Schemas['RecipeImportResponse']
export type RecipeImportPreview = Schemas['RecipeImportPreviewResponse']
export type PreviewedRecipe = Schemas['ImportPreviewRecipeResponse']

/** What the file picker accepts: `.cui` files and older `.zip` archives. */
export const RECIPE_FILE_TYPES = '.cui,.zip,application/vnd.cuisine.recipe+zip,application/zip'

export function previewRecipeImport(file: File): Promise<RecipeImportPreview> {
  const body = new FormData()
  body.append('file', file)
  return webApi.post('/recipes/import/preview', { body })
}

/** `update` holds the source ids whose earlier import is to be updated. */
export function importRecipes(file: File, update: string[]): Promise<RecipeImportReport> {
  const body = new FormData()
  body.append('file', file)
  for (const sourceId of update) body.append('update', sourceId)
  return webApi.post('/recipes/import', { body })
}
