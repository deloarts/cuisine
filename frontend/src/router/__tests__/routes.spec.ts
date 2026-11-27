import { describe, expect, it } from 'vitest'

import { routes } from '@/router'

describe('feature routes', () => {
  it('collects the pages of every feature module', () => {
    const names = routes.map((route) => route.name)
    expect(names).toEqual(
      expect.arrayContaining([
        'login',
        'home',
        'recipes',
        'recipe-cook',
        'meal-plan',
        'shopping',
        'cooked',
        'ingredients',
        'resources',
        'account',
      ]),
    )
  })

  it('keeps the catch-all last', () => {
    expect(routes.at(-1)?.path).toBe('/:pathMatch(.*)*')
  })

  it('renders cook mode without the app shell', () => {
    expect(routes.find((route) => route.name === 'recipe-cook')?.meta?.layout).toBe('fullscreen')
  })
})
