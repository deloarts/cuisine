/**
 * The nutrition fields of an ingredient, per 100 g, in the order the editor
 * and the list show them, with their unit for display.
 */
import type { Schemas } from '@/core/api/generated'

export type Nutrition = Schemas['NutritionSchema']
export type NutritionKey = keyof Nutrition

export const NUTRITION_FIELDS: { key: NutritionKey; unit: 'kcal' | 'g' }[] = [
  { key: 'kcal', unit: 'kcal' },
  { key: 'protein', unit: 'g' },
  { key: 'fat', unit: 'g' },
  { key: 'saturated_fat', unit: 'g' },
  { key: 'carbohydrates', unit: 'g' },
  { key: 'sugar', unit: 'g' },
  { key: 'fibre', unit: 'g' },
  { key: 'salt', unit: 'g' },
]

/** An empty nutrition record, every value unknown. */
export function emptyNutrition(): Nutrition {
  return Object.fromEntries(NUTRITION_FIELDS.map((f) => [f.key, null])) as Nutrition
}

/** True when at least one value is known. */
export function hasNutrition(nutrition: Nutrition): boolean {
  return NUTRITION_FIELDS.some((f) => nutrition[f.key] !== null && nutrition[f.key] !== undefined)
}

/**
 * Takes the values a lookup found and keeps the ones it did not find from
 * the current record, so applying a USDA match never wipes a value the user
 * typed in for a nutrient USDA does not list.
 */
export function mergeNutrition(current: Nutrition, found: Nutrition): Nutrition {
  const merged = { ...current }
  for (const { key } of NUTRITION_FIELDS) {
    const value = found[key]
    if (value !== null && value !== undefined) merged[key] = Math.round(value * 100) / 100
  }
  return merged
}
