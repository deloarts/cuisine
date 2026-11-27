import type { Schemas } from '@/core/api/generated'

export type Diet = Schemas['Diet']
export type DietMarker = Schemas['DietMarker']

/** The diets a recipe can fit and a person can follow. */
export const DIETS: Diet[] = ['vegetarian', 'vegan', 'pescetarian', 'halal', 'no_pork', 'no_beef', 'no_alcohol']

/** What an ingredient can contain that a diet rules out. */
export const DIET_MARKERS: DietMarker[] = [
  'meat',
  'poultry',
  'pork',
  'beef',
  'fish',
  'seafood',
  'gelatin',
  'dairy',
  'eggs',
  'honey',
  'alcohol',
]
