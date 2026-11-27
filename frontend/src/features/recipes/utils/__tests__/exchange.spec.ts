import { describe, expect, it } from 'vitest'

import { cuiFileName } from '@/features/recipes/utils/exchange'

describe('cuiFileName', () => {
  it('slugs the title like the backend', () => {
    expect(cuiFileName('Marillentarte')).toBe('marillentarte.cui')
    expect(cuiFileName('Mürbteig für Kekse!')).toBe('murbteig-fur-kekse.cui')
    expect(cuiFileName('  Crème brûlée / 2 ')).toBe('creme-brulee-2.cui')
    expect(cuiFileName('寿司')).toBe('recipe.cui')
    expect(cuiFileName('a'.repeat(200))).toBe(`${'a'.repeat(80)}.cui`)
  })
})
