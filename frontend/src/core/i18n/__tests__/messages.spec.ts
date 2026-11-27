import { describe, expect, it } from 'vitest'

import { featureOf, mergeMessages } from '@/core/i18n/messages'

describe('mergeMessages', () => {
  it('adds every module namespace next to the core ones', () => {
    const { messages, collisions } = mergeMessages(
      { common: { save: 'Save' } },
      { recipes: { recipes: { title: 'Recipes' } }, shopping: { shopping: { title: 'Shop' } } },
    )
    expect(messages).toEqual({
      common: { save: 'Save' },
      recipes: { title: 'Recipes' },
      shopping: { title: 'Shop' },
    })
    expect(collisions).toEqual([])
  })

  it('reports a namespace two sources define and keeps the first', () => {
    const { messages, collisions } = mergeMessages(
      { common: { save: 'Save' } },
      { recipes: { common: { save: 'Overwritten' } } },
    )
    expect(messages.common).toEqual({ save: 'Save' })
    expect(collisions).toEqual(['common (core and recipes)'])
  })
})

describe('featureOf', () => {
  it('reads the feature folder out of a module path', () => {
    expect(featureOf('../../features/meal-plan/locales/en-GB.ts')).toBe('meal-plan')
  })
})
