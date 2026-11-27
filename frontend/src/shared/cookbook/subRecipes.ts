/**
 * The "I'll buy it" choice when recipes go on a shopping list: every
 * sub-recipe the recipes need directly may be bought ready-made instead of
 * being expanded into its ingredients. Only sub-recipes the viewer can see
 * are offered; a hidden one is always expanded.
 */
import type { Schemas } from '@/core/api/generated'

export type SubRecipeNeed = Schemas['SubRecipeNeed']

export interface RecipeNeeds {
  id: string
  title: string
  needs: SubRecipeNeed[]
}

export interface SubRecipeChoice {
  id: string
  title: string
  /** The recipes (ids) that need it, so a bought one is sent with each of them. */
  recipeIds: string[]
  /** Their titles, for the "in Lasagna" line. */
  recipeTitles: string[]
}

export function subRecipeChoices(recipes: RecipeNeeds[]): SubRecipeChoice[] {
  const byId = new Map<string, SubRecipeChoice>()
  for (const recipe of recipes) {
    for (const need of recipe.needs) {
      const { id, title, accessible } = need.sub_recipe
      if (!accessible || !id) continue
      const choice = byId.get(id) ?? { id, title: title ?? '', recipeIds: [], recipeTitles: [] }
      if (!choice.recipeIds.includes(recipe.id)) {
        choice.recipeIds.push(recipe.id)
        choice.recipeTitles.push(recipe.title)
      }
      byId.set(id, choice)
    }
  }
  return [...byId.values()].sort((a, b) => a.title.localeCompare(b.title))
}

/** The bought sub-recipes that belong to one recipe, for its add request. */
export function boughtFor(recipeId: string, bought: string[], choices: SubRecipeChoice[]): string[] {
  return choices.filter((c) => bought.includes(c.id) && c.recipeIds.includes(recipeId)).map((c) => c.id)
}
