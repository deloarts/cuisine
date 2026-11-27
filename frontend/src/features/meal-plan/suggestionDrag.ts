/**
 * Dragging a suggested recipe onto a meal of the week. The recipe travels in
 * the drag data under a type of its own, so a slot accepts only a suggestion
 * and ignores dragged text, links or files.
 */
export const SUGGESTION_TYPE = 'application/x-cuisine-suggestion'

export interface DraggedRecipe {
  id: string
  title: string
  servings: number
}

export function carriesSuggestion(event: DragEvent): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes(SUGGESTION_TYPE)
}

export function writeSuggestion(event: DragEvent, recipe: DraggedRecipe): void {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData(SUGGESTION_TYPE, JSON.stringify(recipe))
  event.dataTransfer.setData('text/plain', recipe.title)
}

/** The dropped recipe, or null when the drop carries none or is malformed. */
export function readSuggestion(event: DragEvent): DraggedRecipe | null {
  const raw = event.dataTransfer?.getData(SUGGESTION_TYPE)
  if (!raw) return null
  try {
    const value = JSON.parse(raw) as Partial<DraggedRecipe>
    if (typeof value.id !== 'string' || typeof value.title !== 'string') return null
    return { id: value.id, title: value.title, servings: Number(value.servings) || 2 }
  } catch {
    return null
  }
}
