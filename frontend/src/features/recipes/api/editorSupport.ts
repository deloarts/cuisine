/**
 * The calls the recipe editors' composables make in the background: an
 * ingredient's weights for the unit hints and whether a stored file still
 * exists for a restored draft. They live apart from `recipes.ts` so the
 * editor specs that mock that module keep these calls on their own mock.
 */
import { webApi } from '@/core/api/webRequest'

export const getIngredient = (id: string) =>
  webApi.get('/ingredients/{ingredient_id}', { path: { ingredient_id: id } })

export const getFile = (id: string) => webApi.get('/files/{file_id}', { path: { file_id: id } })
