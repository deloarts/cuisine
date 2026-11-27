import { describe, expect, it } from 'vitest'

import { mergeSuggestions } from '@/features/admin-settings/catalogueReview'

describe('mergeSuggestions', () => {
  it('leaves out the draft and puts exact matches first', () => {
    const suggestions = mergeSuggestions('draft', [
      { id: 'draft', name: 'Sahne', matched: 'Sahne', exact: true },
      { id: 'b', name: 'Sauerrahm', matched: 'Sauerrahm', exact: false },
      { id: 'a', name: 'Schlagobers', matched: 'Sahne', exact: true },
      { id: 'c', name: 'Rahm', matched: 'Rahm', exact: false },
    ])
    expect(suggestions.map((s) => s.id)).toEqual(['a', 'c', 'b'])
  })
})
