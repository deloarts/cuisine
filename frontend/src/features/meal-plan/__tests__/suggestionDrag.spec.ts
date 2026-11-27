import { describe, expect, it } from 'vitest'

import { carriesSuggestion, readSuggestion, SUGGESTION_TYPE } from '@/features/meal-plan/suggestionDrag'

function dragEvent(data: Record<string, string>): DragEvent {
  return {
    dataTransfer: { types: Object.keys(data), getData: (type: string) => data[type] ?? '' },
  } as unknown as DragEvent
}

describe('suggestion drag data', () => {
  it('accepts only a dragged suggestion', () => {
    expect(carriesSuggestion(dragEvent({ [SUGGESTION_TYPE]: '{}' }))).toBe(true)
    expect(carriesSuggestion(dragEvent({ 'text/plain': 'Gulasch' }))).toBe(false)
  })

  it('reads the recipe and refuses malformed data', () => {
    const recipe = { id: 'r1', title: 'Gulasch', servings: 4 }
    expect(readSuggestion(dragEvent({ [SUGGESTION_TYPE]: JSON.stringify(recipe) }))).toEqual(recipe)
    expect(readSuggestion(dragEvent({ [SUGGESTION_TYPE]: '{"id": 1}' }))).toBeNull()
    expect(readSuggestion(dragEvent({ [SUGGESTION_TYPE]: 'not json' }))).toBeNull()
    expect(readSuggestion(dragEvent({ 'text/plain': 'Gulasch' }))).toBeNull()
  })
})
