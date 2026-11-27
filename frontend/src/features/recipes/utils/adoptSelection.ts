/**
 * Which changes of a variation an editor adopts into the original. Only a
 * change whose ingredient still exists and whose step or line is still
 * there can be adopted; the request sends null ("all of them") only when
 * every change of the variation is chosen.
 */
import type { VariationChangeView, VariationResponse } from '@/features/recipes/api/recipes'

export function adoptableChanges(variation: VariationResponse): VariationChangeView[] {
  return variation.changes.filter((c) => c.available && c.applies)
}

/** Every adoptable change, the starting selection. */
export function selectAll(variation: VariationResponse): string[] {
  return adoptableChanges(variation).map((c) => c.id)
}

export function toggleChange(selected: readonly string[], id: string): string[] {
  return selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]
}

/** The chosen changes in the variation's own order, for the preview. */
export function chosenChanges(variation: VariationResponse, selected: readonly string[]): VariationChangeView[] {
  return adoptableChanges(variation).filter((c) => selected.includes(c.id))
}

/** The `change_ids` to send: null when the whole variation goes in, else the chosen ids in order. */
export function adoptPayload(variation: VariationResponse, selected: readonly string[]): string[] | null {
  const chosen = chosenChanges(variation, selected).map((c) => c.id)
  return chosen.length === variation.changes.length ? null : chosen
}
