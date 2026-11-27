/**
 * What the recipe page and cook mode need to know about a recipe's
 * variations: which version the reader chose, which variations change a
 * given step of the original, where a variation is based on an older
 * version of a step, and what the backend's step markers say about a line.
 */
import type {
  StaleStepView,
  StepMarkerView,
  StepView,
  VariationChangeView,
  VariationResponse,
} from '@/features/recipes/api/recipes'

/** The value the `variation` query takes for the original recipe. */
export const ORIGINAL = 'original'

/**
 * The version a `variation` query names: a variation id the reader can see,
 * or null for the original. An unknown id falls back to the original.
 */
export function versionFromQuery(value: unknown, variations: readonly VariationResponse[]): string | null {
  if (typeof value !== 'string' || value === ORIGINAL) return null
  return variations.some((v) => v.id === value) ? value : null
}

/**
 * Cook mode asks which version to cook when the recipe has variations and
 * the link did not already say; `chosen` is null for the original.
 */
export function cookVersion(
  value: unknown,
  variations: readonly VariationResponse[],
): { chosen: string | null; ask: boolean } {
  if (!variations.length) return { chosen: null, ask: false }
  if (value === ORIGINAL) return { chosen: null, ask: false }
  const chosen = versionFromQuery(value, variations)
  return { chosen, ask: chosen === null }
}

/** One variation that does a step of the original differently, with the changes that do it. */
export interface StepDifference {
  variation: VariationResponse
  changes: VariationChangeView[]
}

/**
 * Whether a change touches a step of the original. An extra step belongs
 * to the step it follows (the first step when it comes before all of them),
 * and a swap for the whole recipe to every step that uses the ingredient.
 */
export function changeTouchesStep(change: VariationChangeView, step: StepView): boolean {
  if (!change.available) return false
  if (change.kind === 'extra_step') return Math.max(change.step ?? 0, 1) === step.position
  if (change.kind === 'swap' && change.step === null) {
    return step.ingredients.some((line) => line.ingredient_id === change.ingredient_id)
  }
  return change.step === step.position
}

/** The variations that change a step of the original, in the order the backend lists them. */
export function stepDifferences(variations: readonly VariationResponse[], step: StepView): StepDifference[] {
  return variations.flatMap((variation) => {
    const changes = variation.changes.filter((c) => changeTouchesStep(c, step))
    return changes.length ? [{ variation, changes }] : []
  })
}

/** The stale note of a step a variation changes, when the step changed or went since. */
export function staleStep(variation: VariationResponse, step: number | null): StaleStepView | undefined {
  if (step === null) return undefined
  return variation.stale_steps.find((s) => s.step === step)
}

/** The marker of a step of the applied recipe. */
export function markerAt(markers: readonly StepMarkerView[], position: number): StepMarkerView | undefined {
  return markers.find((m) => m.position === position)
}

/** How a line of a step differs in the variation, for the ingredient list to highlight it. */
export interface LineMark {
  kind: 'swapped' | 'added'
  from: string | null
}

/** The marks of a step's lines by index, null for a line the variation leaves alone. */
export function lineMarks(marker: StepMarkerView | undefined, count: number): (LineMark | null)[] {
  const marks: (LineMark | null)[] = Array.from({ length: count }, () => null)
  for (const line of marker?.lines ?? []) {
    if (line.index < 0 || line.index >= count) continue
    marks[line.index] = {
      kind: line.kind === 'swapped' ? 'swapped' : 'added',
      from: line.swapped_from_name,
    }
  }
  return marks
}

/**
 * The name the page shows for whoever wrote a variation: the local author,
 * or for a variation that came with a mirror its author's display name at
 * the source; null for a former member or an author the source keeps unnamed.
 */
export function authorName(variation: VariationResponse): string | null {
  return variation.author?.display_name ?? variation.source_author_name ?? null
}
