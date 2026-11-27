/**
 * Equipment in recipes: finding catalogue items for the step picker and the
 * `@` suggestions, labelling an item with its count, grouping the recipe's
 * "You'll need" list into the recipe's own items and those each sub-recipe
 * needs, and the set-out list of cook mode. The backend already takes the
 * highest count any single step needs, so nothing here adds counts up.
 */
import type { RecipeDetailResponse } from '@/features/recipes/api/recipes'
import type { MentionRef } from '@/shared/components/richText/mentions'
import type { EquipmentResponse } from '@/shared/cookbook/types'
import { normaliseText } from '@/shared/composables/tableText'

export type EquipmentNeed = RecipeDetailResponse['equipment'][number]
export type SubRecipeRef = NonNullable<EquipmentNeed['sub_recipe']>

/**
 * Catalogue items whose name or one of whose aliases contains `query`,
 * without case and diacritics. Items found by a name start first; one
 * found only by an alias carries that alias, for "Schneebesen → Rührbesen".
 */
export function matchEquipment(
  catalogue: readonly EquipmentResponse[],
  query: string,
  limit = 8,
): MentionRef[] {
  const q = normaliseText(query.trim())
  const byName: MentionRef[] = []
  const byAlias: MentionRef[] = []
  for (const item of catalogue) {
    if (normaliseText(item.name).includes(q)) {
      byName.push({ kind: 'equipment', id: item.id, name: item.name })
      continue
    }
    const alias = Object.values(item.aliases)
      .flat()
      .find((a) => normaliseText(a).includes(q))
    if (alias) byAlias.push({ kind: 'equipment', id: item.id, name: item.name, alias })
  }
  const starts = (ref: MentionRef) => normaliseText(ref.alias ?? ref.name).startsWith(q)
  const sorted = (list: MentionRef[]) => [...list.filter(starts), ...list.filter((r) => !starts(r))]
  return [...sorted(byName), ...sorted(byAlias)].slice(0, limit)
}

/** The search text of an item for a filtering select: its name and every alias. */
export function equipmentSearchText(item: EquipmentResponse): string {
  return [item.name, ...Object.values(item.aliases).flat()].join(' ')
}

/** "2 × Bowl", or just the name when the count is unknown or one. */
export function equipmentLabel(name: string, count: number | null): string {
  return count && count > 1 ? `${count} × ${name}` : name
}

export interface EquipmentGroup {
  /** Null for the recipe's own items. */
  subRecipe: SubRecipeRef | null
  items: EquipmentNeed[]
}

/**
 * The "You'll need" list in groups, the recipe's own items first, then one
 * group per sub-recipe in the order the backend lists them. A sub-recipe
 * that needs an item the recipe also needs lists it too, since it may be
 * cooked on its own or ahead.
 */
export function groupEquipmentNeeds(needs: readonly EquipmentNeed[]): EquipmentGroup[] {
  const own: EquipmentNeed[] = []
  const groups = new Map<string, EquipmentGroup>()
  for (const need of needs) {
    if (!need.sub_recipe) {
      own.push(need)
      continue
    }
    const key = need.sub_recipe.id ?? `hidden:${need.sub_recipe.title ?? ''}`
    let group = groups.get(key)
    if (!group) {
      group = { subRecipe: need.sub_recipe, items: [] }
      groups.set(key, group)
    }
    group.items.push(need)
  }
  return [...(own.length ? [{ subRecipe: null, items: own }] : []), ...groups.values()]
}

/**
 * What to set out before cooking: every item once, with the highest count
 * the recipe or any sub-recipe needs, missing when the kitchen lacks it.
 */
export function setOutList(needs: readonly EquipmentNeed[]): EquipmentNeed[] {
  const merged = new Map<string, EquipmentNeed>()
  for (const need of needs) {
    const known = merged.get(need.equipment.id)
    if (!known) {
      merged.set(need.equipment.id, { ...need, sub_recipe: null })
      continue
    }
    if (need.count !== null && (known.count === null || need.count > known.count)) known.count = need.count
    if (need.missing) known.missing = true
  }
  return [...merged.values()]
}

/** The items the reader's kitchen lacks; empty before the kitchen is set up. */
export function missingNeeds(needs: readonly EquipmentNeed[]): EquipmentNeed[] {
  return needs.filter((n) => n.missing === true)
}
