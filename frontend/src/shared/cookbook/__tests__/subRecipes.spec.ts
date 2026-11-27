import { describe, expect, it } from 'vitest'

import { boughtFor, subRecipeChoices, type SubRecipeNeed } from '@/shared/cookbook/subRecipes'

function need(id: string | null, title: string | null, accessible = true): SubRecipeNeed {
  return {
    sub_recipe: { id, title, accessible, total_minutes: null, cover_image_id: null },
    amount: 1,
    unit: null,
    batches: 1,
  }
}

describe('subRecipeChoices', () => {
  it('offers each visible sub-recipe once with every recipe that needs it', () => {
    const choices = subRecipeChoices([
      { id: 'lasagna', title: 'Lasagna', needs: [need('sheets', 'Lasagna sheets'), need('ragu', 'Ragù')] },
      { id: 'cannelloni', title: 'Cannelloni', needs: [need('sheets', 'Lasagna sheets')] },
    ])
    expect(choices.map((c) => c.id)).toEqual(['sheets', 'ragu'])
    expect(choices[0]?.recipeTitles).toEqual(['Lasagna', 'Cannelloni'])
  })

  it('never offers a sub-recipe the viewer cannot see', () => {
    expect(subRecipeChoices([{ id: 'r', title: 'R', needs: [need(null, null, false)] }])).toEqual([])
  })

  it('counts a recipe planned twice only once', () => {
    const lasagna = { id: 'lasagna', title: 'Lasagna', needs: [need('sheets', 'Lasagna sheets')] }
    expect(subRecipeChoices([lasagna, lasagna])[0]?.recipeIds).toEqual(['lasagna'])
  })
})

describe('boughtFor', () => {
  it('sends a bought sub-recipe only with the recipes that need it', () => {
    const choices = subRecipeChoices([
      { id: 'lasagna', title: 'Lasagna', needs: [need('sheets', 'Lasagna sheets'), need('ragu', 'Ragù')] },
      { id: 'cannelloni', title: 'Cannelloni', needs: [need('sheets', 'Lasagna sheets')] },
    ])
    expect(boughtFor('cannelloni', ['sheets', 'ragu'], choices)).toEqual(['sheets'])
    expect(boughtFor('lasagna', ['ragu'], choices)).toEqual(['ragu'])
    expect(boughtFor('soup', ['sheets'], choices)).toEqual([])
  })
})
