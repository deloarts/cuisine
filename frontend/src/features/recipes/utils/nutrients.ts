/**
 * The extended nutrients of a recipe as the recipe page lists them: label,
 * the amount per serving with its unit, and whether that amount is complete.
 * An amount is incomplete when some ingredient lacks the value or cannot be
 * weighed, so the real value is higher than shown.
 */
import type { RecipeDetailResponse } from '@/features/recipes/api/recipes'

export type ExtendedNutrient = RecipeDetailResponse['nutrition']['extended'][number]

const UNIT_LABELS: Record<string, string> = { ug: 'µg', mg: 'mg', g: 'g' }

export function nutrientUnit(unit: string): string {
  return UNIT_LABELS[unit] ?? unit
}

/** "0.35 mg", "4.2 µg", "120 mg": fewer decimals as the amount grows. */
export function formatNutrient(value: number, unit: string, locale: string): string {
  const digits = value < 1 ? 2 : value < 10 ? 1 : 0
  const amount = new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)
  return `${amount} ${nutrientUnit(unit)}`
}

export interface ExtendedRow {
  key: string
  label: string
  value: string
  complete: boolean
}

/** The rows in the backend's display order, labelled through `label(key)`. */
export function extendedRows(
  extended: ExtendedNutrient[],
  locale: string,
  label: (key: string) => string,
): ExtendedRow[] {
  return extended.map((n) => ({
    key: n.key,
    label: label(n.key),
    value: formatNutrient(n.per_serving, n.unit, locale),
    complete: n.complete,
  }))
}
