/**
 * Puts shopping items into the order someone walks through a shop: open
 * items grouped by ingredient category in the category's sort order, items
 * without a category after them, and everything already in the basket in a
 * last group of its own. Inside a group, the items of one ingredient family
 * (all the tomatoes, say) stand next to each other without being merged.
 */
import type { Schemas } from '@/core/api/generated'

export type ShoppingItem = Schemas['ShoppingItemResponse']

export interface ItemGroup {
  /** The category id, `uncategorised` or `checked`. */
  key: string
  /** The category's name; empty for the two fixed groups, which the view labels. */
  name: string
  items: ShoppingItem[]
}

export const UNCATEGORISED = 'uncategorised'
export const CHECKED = 'checked'

function byName(a: ShoppingItem, b: ShoppingItem): number {
  return a.name.localeCompare(b.name)
}

/**
 * Sorts by name, but keeps the members of a family together: the family
 * takes the place of its alphabetically first member, and its members follow
 * one another in name order.
 */
export function sortWithFamilies(items: ShoppingItem[]): ShoppingItem[] {
  const anchor = new Map<string, string>()
  for (const item of items) {
    if (!item.family_id) continue
    const current = anchor.get(item.family_id)
    if (current === undefined || item.name.localeCompare(current) < 0) anchor.set(item.family_id, item.name)
  }
  const keyOf = (item: ShoppingItem) => (item.family_id ? (anchor.get(item.family_id) ?? item.name) : item.name)
  return [...items].sort(
    (a, b) =>
      keyOf(a).localeCompare(keyOf(b)) ||
      (a.family_id ?? '').localeCompare(b.family_id ?? '') ||
      byName(a, b),
  )
}

export function groupItems(
  items: ShoppingItem[],
  inBasket: (item: ShoppingItem) => boolean = (item) => item.checked,
): ItemGroup[] {
  const open = items.filter((i) => !inBasket(i))
  const checked = items.filter((i) => inBasket(i))

  const byCategory = new Map<string, { name: string; order: number; items: ShoppingItem[] }>()
  const loose: ShoppingItem[] = []
  for (const item of open) {
    if (!item.category) {
      loose.push(item)
      continue
    }
    const group = byCategory.get(item.category.id) ?? {
      name: item.category.name,
      order: item.category.sort_order,
      items: [],
    }
    group.items.push(item)
    byCategory.set(item.category.id, group)
  }

  const groups: ItemGroup[] = [...byCategory.entries()]
    .sort(([, a], [, b]) => a.order - b.order || a.name.localeCompare(b.name))
    .map(([key, g]) => ({ key, name: g.name, items: sortWithFamilies(g.items) }))
  if (loose.length) groups.push({ key: UNCATEGORISED, name: '', items: sortWithFamilies(loose) })
  if (checked.length) groups.push({ key: CHECKED, name: '', items: [...checked].sort(byName) })
  return groups
}

/** "250 g", "2 tbsp", "3" or nothing, shown in bold before an item's name. */
export function amountLabel(item: ShoppingItem, locale: string): string {
  if (item.amount === null) return item.unit ? item.unit.abbreviation || item.unit.name : ''
  const amount = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(item.amount)
  if (!item.unit) return amount
  const unitName = item.unit.abbreviation || (item.amount === 1 ? item.unit.name : item.unit.plural_name)
  return `${amount} ${unitName}`
}

/**
 * Where an item came from, for the line under its name. `sub` is an
 * ingredient of a sub-recipe ("for Lasagna sheets, in Lasagna"), `bought`
 * a sub-recipe someone chose to buy ready-made instead of making it. `via`
 * holds the sub-recipes between the top recipe and the one the item belongs
 * to, outermost first. `recipes` holds every recipe the item is for, since
 * the same ingredient from several recipes joins one item. A title is null
 * when the viewer cannot see that recipe; the view names it as such.
 */
export type ItemSource =
  | { kind: 'recipe'; recipes: (string | null)[] }
  | { kind: 'sub'; sub: string | null; via: (string | null)[]; recipes: (string | null)[] }
  | { kind: 'bought'; via: (string | null)[]; recipes: (string | null)[] }

/** A sub-recipe put on the list as one item: no ingredient and no text of its own. */
export function isBoughtSubRecipe(item: ShoppingItem): boolean {
  return item.ingredient_id === null && item.text === '' && item.sub_recipe_path.length > 0
}

export function itemSource(item: ShoppingItem): ItemSource | null {
  const recipes = item.recipes.map((ref) => (ref.accessible ? ref.title : null))
  const path = item.sub_recipe_path.map((ref) => (ref.accessible ? ref.title : null))
  if (!path.length) return recipes.length ? { kind: 'recipe', recipes } : null
  // A sub-recipe path always hangs below a recipe; when that one is gone
  // the item still reads "in a recipe you don't have access to".
  const top = recipes.length ? recipes : [null]
  if (isBoughtSubRecipe(item)) return { kind: 'bought', via: path.slice(0, -1), recipes: top }
  return { kind: 'sub', sub: path.at(-1) ?? null, via: path.slice(0, -1), recipes: top }
}

/** How many recipe names an item's source line spells out before "+N". */
export const SHOWN_RECIPES = 2

/** The recipe names shown on the line and how many more follow as "+N". */
export function shownRecipes<T>(recipes: T[]): { shown: T[]; more: number } {
  // "+1" saves no room over the name itself, so a third name is spelled out.
  if (recipes.length <= SHOWN_RECIPES + 1) return { shown: recipes, more: 0 }
  return { shown: recipes.slice(0, SHOWN_RECIPES), more: recipes.length - SHOWN_RECIPES }
}
