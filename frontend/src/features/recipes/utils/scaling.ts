/**
 * Servings scaling and the way amounts read in a recipe. The recipe page
 * fetches a recipe once at its base servings and scales every amount here,
 * so the stepper answers instantly without a request per click.
 */
import type { IngredientAmount } from '@/features/recipes/api/recipes'

export function scaleFactor(servings: number, baseServings: number): number {
  if (baseServings <= 0 || servings <= 0) return 1
  return servings / baseServings
}

export function scaleAmount(amount: number | null, factor: number): number | null {
  return amount === null ? null : amount * factor
}

export function scaleIngredients<T extends IngredientAmount>(items: T[], factor: number): T[] {
  return items.map((item) => ({ ...item, amount: scaleAmount(item.amount, factor) }))
}

// Cooks read small counts as fractions ("½ onion", "1 ¼ cups"), so an amount
// close to one of these is shown with its glyph.
const FRACTIONS: [number, string][] = [
  [1 / 8, '⅛'],
  [1 / 4, '¼'],
  [1 / 3, '⅓'],
  [1 / 2, '½'],
  [2 / 3, '⅔'],
  [3 / 4, '¾'],
]
const FRACTION_TOLERANCE = 0.02

function asFraction(value: number): string | null {
  const whole = Math.floor(value)
  const rest = value - whole
  if (rest < FRACTION_TOLERANCE) return null
  for (const [fraction, glyph] of FRACTIONS) {
    if (Math.abs(rest - fraction) < FRACTION_TOLERANCE) {
      return whole > 0 ? `${whole} ${glyph}` : glyph
    }
  }
  return null
}

// How a user reads small metric amounts, chosen on the account page.
export type AmountStyle = 'decimals' | 'fractions'

// The kitchen fractions of a litre or kilogram ("⅛ l Rotwein", "¼ kg
// Topfen"). Thirds stay decimal, since no measuring jug marks them.
const METRIC_FRACTIONS: [number, string][] = [
  [1 / 8, '⅛'],
  [1 / 4, '¼'],
  [1 / 2, '½'],
  [3 / 4, '¾'],
]
const METRIC_FRACTION_UNITS = new Set(['l', 'kg'])
const METRIC_TOLERANCE = 0.001

function asMetricFraction(value: number): string | null {
  const whole = Math.floor(value)
  const rest = value - whole
  for (const [fraction, glyph] of METRIC_FRACTIONS) {
    if (Math.abs(rest - fraction) < METRIC_TOLERANCE) {
      return whole > 0 ? `${whole} ${glyph}` : glyph
    }
  }
  return null
}

export interface AmountFormat {
  // The reader's choice for mass and volume; decimals when not given.
  style?: AmountStyle
  // The unit's code, so the fractions style knows a litre from a millilitre.
  unitCode?: string | null
}

/**
 * Formats an amount for reading: fractions for small counts, whole numbers
 * from ten on, in the reader's number format. Mass and volume below ten stay
 * exact, to three decimals below one and two below ten, so ⅛ l reads
 * "0,125 l" and never "0,1 l". With the fractions style, a litre or kilogram
 * amount that is a kitchen fraction reads "⅛ l" or "1 ½ kg" instead.
 */
export function formatAmount(
  amount: number | null,
  locale: string,
  unitKind?: string,
  format: AmountFormat = {},
): string {
  if (amount === null || Number.isNaN(amount)) return ''
  const metric = unitKind === 'mass' || unitKind === 'volume'
  if (!metric && amount < 10) {
    const fraction = asFraction(amount)
    if (fraction) return fraction
  }
  if (metric && format.style === 'fractions' && format.unitCode && METRIC_FRACTION_UNITS.has(format.unitCode)) {
    const fraction = asMetricFraction(amount)
    if (fraction) return fraction
  }
  const digits = amount >= 10 ? 0 : !metric ? 1 : amount < 1 ? 3 : 2
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(amount)
}

/** The unit as it reads after an amount: the abbreviation, else singular or plural. */
export function unitLabel(item: IngredientAmount): string {
  const unit = item.unit
  if (!unit) return ''
  if (unit.abbreviation) return unit.abbreviation
  return item.amount !== null && item.amount > 1 && unit.plural_name ? unit.plural_name : unit.name
}

/** Splits minutes into hours and minutes for a duration label. */
export function splitMinutes(total: number): { hours: number; minutes: number } {
  return { hours: Math.floor(total / 60), minutes: total % 60 }
}
