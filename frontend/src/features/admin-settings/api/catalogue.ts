/** The catalogue calls the admin area makes: reviewing draft ingredients and reading the equipment list. */
import { webApi, type QueryOf } from '@/core/api/webRequest'

export type IngredientListQuery = QueryOf<'/ingredients'>

export const catalogueApi = {
  ingredients: (query: IngredientListQuery) => webApi.get('/ingredients', { query }),
  duplicates: (name: string) => webApi.get('/ingredients/duplicates', { query: { name } }),
  activate: (id: string) =>
    webApi.post('/ingredients/{ingredient_id}/activate', { path: { ingredient_id: id } }),
  merge: (id: string, intoId: string) =>
    webApi.post('/ingredients/{ingredient_id}/merge', { path: { ingredient_id: id }, body: { into_id: intoId } }),
  equipment: () => webApi.get('/equipment'),
}
