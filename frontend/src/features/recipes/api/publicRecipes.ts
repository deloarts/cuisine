/**
 * The public recipe pages' calls to the anonymous surface
 * (/api/v1/public/recipes). They carry no session, so a refusal never marks
 * anybody signed out. Views import from here, so a spec mocks this module.
 */
import { publicApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import type { ContentLocale } from '@/shared/cookbook/types'

export type PublicRecipeSummary = Schemas['PublicRecipeSummaryResponse']
export type PublicRecipeDetail = Schemas['PublicRecipeDetailResponse']
export type PublicRecipePage = Schemas['Page_PublicRecipeSummaryResponse_']
export type PublicTag = Schemas['PublicTag']
export type PublicIngredientLine = Schemas['PublicIngredientLine']
export type PublicStep = Schemas['PublicStep']

export interface PublicRecipeQuery {
  search?: string
  tag_id?: string[]
  diets?: Schemas['Diet'][]
  sort?: 'newest' | 'title'
  limit?: number
  offset?: number
  locale?: ContentLocale
}

const API_ROOT = import.meta.env.VITE_API_URL ?? ''

// Lists repeat the key (`tag_id=a&tag_id=b`), as the backend reads them.
function serialize(params: Record<string, unknown>): string {
  const usp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const v of value) usp.append(key, String(v))
    } else if (value !== undefined && value !== null && value !== '') {
      usp.append(key, String(value))
    }
  }
  return usp.toString()
}

export async function listPublicRecipes(query: PublicRecipeQuery): Promise<PublicRecipePage> {
  return (
    await publicApi.get<PublicRecipePage>('/recipes', {
      params: query,
      paramsSerializer: (params) => serialize(params as Record<string, unknown>),
    })
  ).data
}

export async function listPublicTags(locale?: ContentLocale): Promise<PublicTag[]> {
  return (await publicApi.get<PublicTag[]>('/recipes/tags', { params: { locale } })).data
}

export async function getPublicRecipe(
  id: string,
  options: { servings?: number; locale?: ContentLocale } = {},
): Promise<PublicRecipeDetail> {
  return (
    await publicApi.get<PublicRecipeDetail>(`/recipes/${encodeURIComponent(id)}`, {
      params: options,
    })
  ).data
}

/** The display-size image of a public recipe; the original is never served. */
/** The author's avatar, served while the author shows their name (`author_avatar`). */
export function publicAuthorAvatarUrl(recipeId: string): string {
  return `${API_ROOT}/api/v1/public/recipes/${encodeURIComponent(recipeId)}/author-avatar`
}

export function publicImageUrl(recipeId: string, imageId: string): string {
  return `${API_ROOT}/api/v1/public/recipes/${encodeURIComponent(recipeId)}/images/${encodeURIComponent(imageId)}`
}
