/** The cookbook reads the shared pickers and the resource cache make. */
import { webApi, type QueryOf } from '@/core/api/webRequest'

export const listRecipes = (query: QueryOf<'/recipes'>) => webApi.get('/recipes', { query })

export const listIngredients = (query: QueryOf<'/ingredients'>) => webApi.get('/ingredients', { query })

export const listUnits = () => webApi.get('/units')

export const listTags = () => webApi.get('/tags')

export const listCategories = () => webApi.get('/ingredient-categories')

export const listFamilies = () => webApi.get('/ingredient-families')
