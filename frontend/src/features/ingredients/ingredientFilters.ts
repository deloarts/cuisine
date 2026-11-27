/**
 * The ingredient table's filters and sort. The backend list filters by name,
 * category, family, status, "mine" and the usage range, and sorts by name or
 * usage; allergens, diet markers, season months and the
 * kcal range it does not know yet, so when one of those is set the table loads the whole filtered
 * catalogue (a household's is a few hundred entries) and narrows and pages
 * it in the browser.
 */
import type { UrlFilterValues } from '@/shared/composables/urlFilters'
import type { IngredientResponse, IngredientStatus } from '@/shared/cookbook/types'

export const INGREDIENT_FILTERS = {
  q: 'string',
  category: 'string',
  family: 'string',
  status: 'string',
  mine: 'boolean',
  allergens: 'list',
  diets: 'list',
  season: 'list',
  kcalMin: 'number',
  kcalMax: 'number',
  usageMin: 'number',
  usageMax: 'number',
} as const

export type IngredientFilters = UrlFilterValues<typeof INGREDIENT_FILTERS>

/** The most the backend returns in one page, used to load everything for browser filtering. */
export const CLIENT_FILTER_LIMIT = 500

export function serverQuery(f: IngredientFilters) {
  return {
    search: f.q || null,
    category_id: f.category,
    family_id: f.family,
    status: f.status === 'draft' || f.status === 'active' ? (f.status as IngredientStatus) : null,
    mine: f.mine,
    min_usage: f.usageMin,
    max_usage: f.usageMax,
  }
}

/**
 * The server sort for the table's sorted column. Name ascending is the
 * backend's default, which ranks the best matches of a search first, so
 * only usage and name descending are sent.
 */
export function serverSort(field: string | undefined, order: 1 | -1) {
  const direction = order === -1 ? ('desc' as const) : ('asc' as const)
  if (field === 'usage') return { sort: 'usage' as const, order: direction }
  if (field === 'q' && order === -1) return { sort: 'name' as const, order: direction }
  return {}
}

export function needsClientFiltering(f: IngredientFilters): boolean {
  return (
    f.allergens.length > 0 || f.diets.length > 0 || f.season.length > 0 || f.kcalMin !== null || f.kcalMax !== null
  )
}

/**
 * Whether an ingredient passes the filters the backend does not apply: it
 * contains at least one chosen allergen and one chosen diet marker, is in
 * season in at least one chosen month, and its energy lies in the range. An
 * unknown energy fails any range.
 */
export function matchesClientFilters(item: IngredientResponse, f: IngredientFilters): boolean {
  if (f.allergens.length && !f.allergens.some((a) => item.allergens.includes(a))) return false
  if (f.diets.length && !f.diets.some((d) => item.diet_markers.includes(d))) return false
  if (f.season.length && !f.season.some((m) => item.season_months.includes(Number(m)))) return false
  if (f.kcalMin !== null || f.kcalMax !== null) {
    const kcal = item.nutrition.kcal
    if (kcal === null || kcal === undefined) return false
    if (f.kcalMin !== null && kcal < f.kcalMin) return false
    if (f.kcalMax !== null && kcal > f.kcalMax) return false
  }
  return true
}
