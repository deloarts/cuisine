import { describe, expect, it } from 'vitest'

import { cardDiet } from '@/shared/components/recipes/dietBadge'

describe('cardDiet', () => {
  it('prefers vegan over vegetarian', () => {
    expect(cardDiet(['vegetarian', 'vegan', 'halal'])).toBe('vegan')
    expect(cardDiet(['pescetarian', 'vegetarian'])).toBe('vegetarian')
  })

  it('shows nothing for the other diets', () => {
    expect(cardDiet(['halal', 'no_pork'])).toBeNull()
    expect(cardDiet([])).toBeNull()
  })
})
