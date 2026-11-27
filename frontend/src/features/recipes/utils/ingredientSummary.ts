/**
 * The math behind the editor's ingredient summary: how much of each
 * declared line the steps use, and which ingredients only the steps name.
 *
 * Amounts compare the way the backend merges the two lists
 * (`recipe_derivation.merged_lines`): in the one unit both sides use, in
 * grams when every unit involved can be weighed for the ingredient, and in
 * the kind's base unit when every unit is of one kind with a factor.
 * Anything else cannot be compared, so the editor says it cannot check it
 * rather than guessing. Sub-recipe lines compare only within one unit.
 */
import { formatAmount, type AmountStyle } from '@/features/recipes/utils/scaling'
import type { UnitResponse } from '@/shared/cookbook/types'
import { gramsPerUnit, unitShortLabel, type WeighableIngredient } from '@/shared/cookbook/units'

/** A line of the declared list or of a step, as far as the summary needs it. */
export interface SummaryLine {
  ingredient_id: string | null
  sub_recipe_id: string | null
  ingredient_name: string
  amount: number | null
  unit_id: string | null
}

export type WeightsOf = (ingredientId: string | null | undefined) => WeighableIngredient | null

/** How the steps use what a declared line lists. */
export type LineUsage =
  | { state: 'used' }
  | { state: 'unused' }
  // The steps use less; `missing` is in `unit`, or in grams or the kind's
  // base unit (`symbol`) when the lines were compared that way.
  | { state: 'partly'; missing: number; unit: UnitResponse | null; symbol: string }
  | { state: 'unchecked' }

/** An ingredient only the steps name, with what they use of it summed where that is possible. */
export interface StepOnlyLine {
  key: string
  ingredient_id: string | null
  sub_recipe_id: string | null
  ingredient_name: string
  amount: number | null
  unit_id: string | null
}

// Rounding noise of summed decimals is not a missing amount.
const EPSILON = 1e-6
const BASE_SYMBOL: Record<string, string> = { mass: 'g', volume: 'ml' }

/** What a line names: an ingredient or a sub-recipe, as one comparable key. */
export function lineKey(line: SummaryLine): string | null {
  if (line.sub_recipe_id) return `recipe:${line.sub_recipe_id}`
  if (line.ingredient_id) return `ingredient:${line.ingredient_id}`
  return null
}

function perUnit(lines: readonly SummaryLine[]): Map<string | null, number> {
  const sums = new Map<string | null, number>()
  for (const line of lines) {
    if (line.amount === null) continue
    sums.set(line.unit_id, (sums.get(line.unit_id) ?? 0) + line.amount)
  }
  return sums
}

function unitOf(units: readonly UnitResponse[], id: string | null): UnitResponse | null {
  return id === null ? null : (units.find((u) => u.id === id) ?? null)
}

/** The base unit of a kind (`to_base` 1), when the catalogue has one. */
function baseUnit(units: readonly UnitResponse[], kind: string): UnitResponse | null {
  return units.find((u) => u.kind === kind && u.to_base === 1) ?? null
}

type Converted = { total: (sums: Map<string | null, number>) => number; unit: UnitResponse | null; symbol: string }

/**
 * How amounts in these units add up into one number: in the one unit, in
 * grams, or in the kind's base unit; null when they cannot.
 */
function converter(
  unitIds: readonly (string | null)[],
  units: readonly UnitResponse[],
  weights: WeighableIngredient | null,
): Converted | null {
  if (unitIds.length === 1) {
    const unit = unitOf(units, unitIds[0] ?? null)
    return { total: (sums) => [...sums.values()].reduce((a, b) => a + b, 0), unit, symbol: '' }
  }
  const resolved = unitIds.map((id) => unitOf(units, id))
  if (resolved.some((u) => u === null)) return null
  const known = resolved as UnitResponse[]
  if (weights) {
    const grams = known.map((u) => gramsPerUnit(u, weights))
    if (grams.every((g) => g !== null)) {
      const factor = new Map(known.map((u, i) => [u.id, grams[i] as number]))
      return {
        total: (sums) => [...sums].reduce((a, [id, amount]) => a + amount * (factor.get(id ?? '') ?? 0), 0),
        unit: baseUnit(units, 'mass'),
        symbol: 'g',
      }
    }
  }
  const kind = known[0]!.kind
  if (known.every((u) => u.kind === kind && u.to_base !== null)) {
    const factor = new Map(known.map((u) => [u.id, u.to_base as number]))
    return {
      total: (sums) => [...sums].reduce((a, [id, amount]) => a + amount * (factor.get(id ?? '') ?? 0), 0),
      unit: baseUnit(units, kind),
      symbol: BASE_SYMBOL[kind] ?? '',
    }
  }
  return null
}

/**
 * How the steps use what the declared lines of one ingredient or sub-recipe
 * list. Several declared lines of the same thing count together.
 */
export function usageOf(
  declared: readonly SummaryLine[],
  steps: readonly SummaryLine[],
  units: readonly UnitResponse[],
  weightsOf: WeightsOf,
): LineUsage {
  if (steps.length === 0) return { state: 'unused' }
  const have = perUnit(declared)
  // "To taste" in the list is covered by any use in a step.
  if (have.size === 0) return { state: 'used' }
  const need = perUnit(steps)
  if (need.size === 0) return { state: 'unchecked' }
  const unitIds = [...new Set([...have.keys(), ...need.keys()])]
  const first = declared[0]!
  const isRecipe = first.sub_recipe_id !== null
  if (isRecipe && unitIds.length > 1) return { state: 'unchecked' }
  const convert = converter(unitIds, units, isRecipe ? null : weightsOf(first.ingredient_id))
  if (!convert) return { state: 'unchecked' }
  const missing = convert.total(have) - convert.total(need)
  if (missing <= EPSILON) return { state: 'used' }
  return { state: 'partly', missing, unit: convert.unit, symbol: convert.symbol }
}

/**
 * The ingredients and sub-recipes the steps name that the declared list
 * lacks, in the order the steps first name them. What the steps use is
 * summed when it is in one unit, or in grams when every unit can be weighed
 * and the catalogue has a gram unit; otherwise the line has no amount, so
 * adding it to the list never states an amount nobody wrote.
 */
export function stepOnlyLines(
  declared: readonly SummaryLine[],
  steps: readonly SummaryLine[],
  units: readonly UnitResponse[],
  weightsOf: WeightsOf,
): StepOnlyLine[] {
  const listed = new Set(declared.map(lineKey).filter((k) => k !== null))
  const found = new Map<string, SummaryLine[]>()
  for (const line of steps) {
    const key = lineKey(line)
    if (key === null || listed.has(key)) continue
    found.set(key, [...(found.get(key) ?? []), line])
  }
  return [...found].map(([key, lines]) => {
    const first = lines[0]!
    const base = {
      key,
      ingredient_id: first.ingredient_id,
      sub_recipe_id: first.sub_recipe_id,
      ingredient_name: first.ingredient_name,
    }
    const sums = perUnit(lines)
    if (sums.size === 0) return { ...base, amount: null, unit_id: first.unit_id }
    if (sums.size === 1) {
      const [unitId, amount] = [...sums][0]!
      return { ...base, amount, unit_id: unitId }
    }
    const convert = first.sub_recipe_id
      ? null
      : converter([...sums.keys()], units, weightsOf(first.ingredient_id))
    if (convert?.unit && convert.symbol === 'g') {
      return { ...base, amount: convert.total(sums), unit_id: convert.unit.id }
    }
    return { ...base, amount: null, unit_id: null }
  })
}

/**
 * A declared line the steps do not use up yet, as a step's ingredient picker
 * offers it: what adding it to a step puts on the line (`amount` in
 * `unit_id`), and for a partly used line the remaining amount as `usageOf`
 * reports it.
 */
export interface ListSuggestion {
  key: string
  ingredient_id: string | null
  sub_recipe_id: string | null
  ingredient_name: string
  amount: number | null
  unit_id: string | null
  usage: Extract<LineUsage, { state: 'unused' } | { state: 'partly' }>
}

// What the declared lines list minus what the steps use, in one unit, or
// null when the units involved do not compare.
function remainingIn(
  declared: readonly SummaryLine[],
  steps: readonly SummaryLine[],
  unitId: string | null,
  units: readonly UnitResponse[],
  weightsOf: WeightsOf,
): number | null {
  const have = perUnit(declared)
  const need = perUnit(steps)
  const unitIds = [...new Set([...have.keys(), ...need.keys(), unitId])]
  const first = declared[0]!
  const isRecipe = first.sub_recipe_id !== null
  if (isRecipe && unitIds.length > 1) return null
  const convert = converter(unitIds, units, isRecipe ? null : weightsOf(first.ingredient_id))
  if (!convert) return null
  const perTarget = convert.total(new Map([[unitId, 1]]))
  if (!perTarget) return null
  return (convert.total(have) - convert.total(need)) / perTarget
}

/**
 * The declared ingredients and sub-recipes that no step uses, or the steps
 * use less of, in the order of the list. Each carries the unit of its first
 * declared line with an amount and the amount still missing in that unit,
 * rounded up to three decimals so adding it clears the hint; a line listed
 * "to taste" or in units that do not compare carries no amount.
 */
export function listSuggestions(
  declared: readonly SummaryLine[],
  steps: readonly SummaryLine[],
  units: readonly UnitResponse[],
  weightsOf: WeightsOf,
): ListSuggestion[] {
  const groups = new Map<string, SummaryLine[]>()
  for (const line of declared) {
    const key = lineKey(line)
    if (key !== null) groups.set(key, [...(groups.get(key) ?? []), line])
  }
  const found: ListSuggestion[] = []
  for (const [key, lines] of groups) {
    const used = steps.filter((l) => lineKey(l) === key)
    const usage = usageOf(lines, used, units, weightsOf)
    if (usage.state !== 'unused' && usage.state !== 'partly') continue
    const first = lines[0]!
    const unitId = (lines.find((l) => l.amount !== null) ?? first).unit_id
    const missing = lines.some((l) => l.amount !== null)
      ? remainingIn(lines, used, unitId, units, weightsOf)
      : null
    found.push({
      key,
      ingredient_id: first.ingredient_id,
      sub_recipe_id: first.sub_recipe_id,
      ingredient_name: first.ingredient_name,
      amount: missing !== null && missing > EPSILON ? Math.ceil((missing - EPSILON) * 1000) / 1000 : null,
      unit_id: unitId,
      usage,
    })
  }
  return found
}

/**
 * An amount as the summary and the pickers show it, in a unit record or,
 * when the lines were compared in grams or millilitres without one, in that
 * base unit's symbol.
 */
export function amountLabel(
  amount: number,
  unit: UnitResponse | null,
  symbol: string,
  locale: string,
  style: AmountStyle,
): string {
  const label = unit ? unitShortLabel(unit) : symbol
  const kind = unit?.kind ?? (symbol === 'ml' ? 'volume' : symbol === 'g' ? 'mass' : undefined)
  return `${formatAmount(amount, locale, kind, { style, unitCode: unit?.code })} ${label}`.trim()
}
