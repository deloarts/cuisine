/**
 * Units in pickers: grouped by kind in the order lists show them, the
 * conversion to the kind's base unit ("= 10 g"), and whether an amount in a
 * unit can be weighed for one ingredient. The weighing follows the backend's
 * rule (`domain/services/quantity.py`): the ingredient's own conversion
 * wins, then a mass unit by its factor, then a volume unit by its factor and
 * the ingredient's density. Kind labels live in the core `unitKinds`
 * namespace.
 */
import type { IngredientResponse, UnitKind, UnitResponse } from './types'

export const UNIT_KINDS: UnitKind[] = ['mass', 'volume', 'count', 'other']

/** The symbol of the base unit each convertible kind's `to_base` counts in. */
const BASE_SYMBOL: Partial<Record<UnitKind, string>> = { mass: 'g', volume: 'ml' }

export interface UnitGroup {
  kind: UnitKind
  units: UnitResponse[]
}

/** The units of each kind in their sort order, leaving out empty kinds. */
export function groupUnits(units: readonly UnitResponse[]): UnitGroup[] {
  const sorted = [...units].sort((a, b) => a.sort_order - b.sort_order)
  return UNIT_KINDS.map((kind) => ({ kind, units: sorted.filter((u) => u.kind === kind) })).filter(
    (g) => g.units.length > 0,
  )
}

/** What a unit is worth in its kind's base unit, or null for the base unit itself and units without a factor. */
export function unitBase(unit: UnitResponse): { amount: number; symbol: string } | null {
  const symbol = BASE_SYMBOL[unit.kind as UnitKind]
  if (!symbol || unit.to_base === null || unit.to_base === 1) return null
  return { amount: unit.to_base, symbol }
}

/** The text a filtering select matches a unit by: abbreviation, names and code. */
export function unitSearchText(unit: UnitResponse): string {
  return [unit.abbreviation, unit.name, unit.plural_name, unit.code].filter(Boolean).join(' ')
}

/** The short label a selected unit shows in a narrow field. */
export function unitShortLabel(unit: UnitResponse): string {
  return unit.abbreviation || unit.name
}

/** What of an ingredient decides how its amounts weigh. */
export type WeighableIngredient = Pick<IngredientResponse, 'density_g_per_ml' | 'conversions'>

/** Grams of one `unit` of `ingredient`, or null when the backend cannot weigh it either. */
export function gramsPerUnit(unit: UnitResponse, ingredient: WeighableIngredient): number | null {
  const own = ingredient.conversions.find((c) => c.unit_id === unit.id)
  if (own) return own.grams
  if (unit.to_base === null) return null
  if (unit.kind === 'mass') return unit.to_base
  if (unit.kind === 'volume' && ingredient.density_g_per_ml !== null) {
    return unit.to_base * ingredient.density_g_per_ml
  }
  return null
}
