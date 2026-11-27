import type { Schemas } from '@/core/api/generated'

/**
 * The one diet worth showing on a recipe card: vegan beats vegetarian, and
 * the other diets only show on the recipe page, where there is room.
 */
export function cardDiet(diets: readonly string[]): 'vegan' | 'vegetarian' | null {
  if (diets.includes('vegan')) return 'vegan'
  if (diets.includes('vegetarian')) return 'vegetarian'
  return null
}

/** The diets in the order the pickers list them. */
export const DIETS = [
  'vegetarian',
  'vegan',
  'pescetarian',
  'halal',
  'no_pork',
  'no_beef',
  'no_alcohol',
] as const satisfies readonly Schemas['Diet'][]
