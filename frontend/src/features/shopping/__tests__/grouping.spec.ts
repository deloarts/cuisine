import { describe, expect, it } from 'vitest'

import {
  amountLabel,
  CHECKED,
  groupItems,
  isBoughtSubRecipe,
  itemSource,
  shownRecipes,
  sortWithFamilies,
  UNCATEGORISED,
  type ShoppingItem,
} from '@/features/shopping/grouping'

function item(name: string, extra: Partial<ShoppingItem> = {}): ShoppingItem {
  return {
    id: name,
    ingredient_id: null,
    name,
    text: name,
    amount: null,
    unit: null,
    category: null,
    family_id: null,
    checked: false,
    checked_by: null,
    checked_at: null,
    recipe: null,
    recipes: [],
    sub_recipe_path: [],
    has_warning: false,
    ...extra,
  }
}

const veg = { id: 'veg', name: 'Vegetables', sort_order: 10 }
const dairy = { id: 'dairy', name: 'Dairy', sort_order: 30 }
const bakery = { id: 'bakery', name: 'Bakery', sort_order: 20 }

describe('groupItems', () => {
  it('orders categories by aisle, then uncategorised, then the checked items', () => {
    const groups = groupItems([
      item('Milk', { category: dairy }),
      item('Tomatoes', { category: veg }),
      item('Bread', { category: bakery }),
      item('Candles'),
      item('Carrots', { category: veg }),
      item('Butter', { category: dairy, checked: true }),
    ])
    expect(groups.map((g) => g.key)).toEqual(['veg', 'bakery', 'dairy', UNCATEGORISED, CHECKED])
    expect(groups[0]?.items.map((i) => i.name)).toEqual(['Carrots', 'Tomatoes'])
    expect(groups.at(-1)?.items.map((i) => i.name)).toEqual(['Butter'])
  })

  it('leaves out empty fixed groups', () => {
    expect(groupItems([item('Tomatoes', { category: veg })]).map((g) => g.key)).toEqual(['veg'])
    expect(groupItems([])).toEqual([])
  })
})

describe('sortWithFamilies', () => {
  it('keeps the members of a family together at the place of the first one', () => {
    const sorted = sortWithFamilies([
      item('Passata', { family_id: 'tomatoes' }),
      item('Basil'),
      item('Cherry tomatoes', { family_id: 'tomatoes' }),
      item('Onion'),
      item('Tinned tomatoes', { family_id: 'tomatoes' }),
    ])
    expect(sorted.map((i) => i.name)).toEqual(['Basil', 'Cherry tomatoes', 'Passata', 'Tinned tomatoes', 'Onion'])
  })

  it('is applied inside every category group', () => {
    const groups = groupItems([
      item('Tomatoes', { category: veg, family_id: 'tomatoes' }),
      item('Leek', { category: veg }),
      item('Cherry tomatoes', { category: veg, family_id: 'tomatoes' }),
      item('Carrots', { category: veg }),
    ])
    expect(groups[0]?.items.map((i) => i.name)).toEqual(['Carrots', 'Cherry tomatoes', 'Tomatoes', 'Leek'])
  })
})

describe('itemSource', () => {
  const lasagna = { id: 'r1', title: 'Lasagna', cover_image_id: null, status: 'published' }
  const lasagnaRef = { id: 'r1', title: 'Lasagna', accessible: true, total_minutes: 60, cover_image_id: null }
  const pizzaRef = { id: 'r2', title: 'Pizza', accessible: true, total_minutes: 30, cover_image_id: null }
  const sheets = { id: 's1', title: 'Lasagna sheets', accessible: true, total_minutes: 45, cover_image_id: null }
  const hidden = { id: null, title: null, accessible: false, total_minutes: null, cover_image_id: null }

  it('names the recipe of a plain recipe item and nothing for a free item', () => {
    expect(itemSource(item('Flour', { ingredient_id: 'f', recipe: lasagna, recipes: [lasagnaRef] }))).toEqual({
      kind: 'recipe',
      recipes: ['Lasagna'],
    })
    expect(itemSource(item('Candles'))).toBeNull()
  })

  it('names every recipe the item is for and hides each one the viewer cannot see', () => {
    const flour = item('Flour', { ingredient_id: 'f', recipe: lasagna, recipes: [lasagnaRef, hidden, pizzaRef] })
    expect(itemSource(flour)).toEqual({ kind: 'recipe', recipes: ['Lasagna', null, 'Pizza'] })
  })

  it('names the sub-recipe and the recipe for an ingredient of a sub-recipe', () => {
    const flour = item('Flour', { ingredient_id: 'f', recipe: lasagna, recipes: [lasagnaRef], sub_recipe_path: [sheets] })
    expect(itemSource(flour)).toEqual({ kind: 'sub', sub: 'Lasagna sheets', via: [], recipes: ['Lasagna'] })
  })

  it('keeps the levels in between and hides recipes the viewer cannot see', () => {
    const egg = item('Egg', { ingredient_id: 'e', recipes: [hidden], sub_recipe_path: [hidden, sheets] })
    expect(itemSource(egg)).toEqual({ kind: 'sub', sub: 'Lasagna sheets', via: [null], recipes: [null] })
  })

  it('recognises a sub-recipe bought ready-made', () => {
    const bought = item('Lasagna sheets', { text: '', recipe: lasagna, recipes: [lasagnaRef], sub_recipe_path: [sheets] })
    expect(isBoughtSubRecipe(bought)).toBe(true)
    expect(itemSource(bought)).toEqual({ kind: 'bought', via: [], recipes: ['Lasagna'] })
    expect(isBoughtSubRecipe(item('Candles', { text: '' }))).toBe(false)
  })
})

describe('shownRecipes', () => {
  it('spells out up to three names and folds the rest into a count', () => {
    expect(shownRecipes(['A', 'B', 'C'])).toEqual({ shown: ['A', 'B', 'C'], more: 0 })
    expect(shownRecipes(['A', 'B', 'C', 'D'])).toEqual({ shown: ['A', 'B'], more: 2 })
  })
})

describe('amountLabel', () => {
  const g = { id: 'g', code: 'g', kind: 'mass', name: 'gram', plural_name: 'grams', abbreviation: 'g' }
  const piece = { id: 'p', code: 'piece', kind: 'count', name: 'piece', plural_name: 'pieces', abbreviation: '' }

  it('prefers the abbreviation and picks the plural without one', () => {
    expect(amountLabel(item('Flour', { amount: 250, unit: g }), 'en-GB')).toBe('250 g')
    expect(amountLabel(item('Egg', { amount: 2, unit: piece }), 'en-GB')).toBe('2 pieces')
    expect(amountLabel(item('Egg', { amount: 1, unit: piece }), 'en-GB')).toBe('1 piece')
  })

  it('formats decimals for the locale and handles missing parts', () => {
    expect(amountLabel(item('Milk', { amount: 0.5 }), 'de-AT')).toBe('0,5')
    expect(amountLabel(item('Salt'), 'en-GB')).toBe('')
  })
})
