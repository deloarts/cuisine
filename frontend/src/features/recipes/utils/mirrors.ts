/**
 * Mirrors are recipes a paired instance shares with this one. They are read
 * only here, and what this instance's catalogue could not place stays text:
 * plain ingredient lines, plain equipment and sub-recipe lines whose
 * sub-recipe is not mirrored here. The backend keeps those apart from the
 * steps (`mirror_details`), each with the index of its step and its place
 * among the step's lines at the source; these helpers put them back where
 * the source had them, so the page reads like the original.
 */
import type { Schemas } from '@/core/api/generated'
import type { IngredientAmount } from '@/features/recipes/api/recipes'
import type { LineMark } from '@/features/recipes/utils/variations'
import type { EquipmentRef } from '@/shared/cookbook/types'

export type MirrorView = Schemas['MirrorView']
export type MirrorSourceRef = Schemas['MirrorSourceRef']
export type MirrorPlainLine = Schemas['MirrorPlainLine']
export type MirrorPlainEquipment = Schemas['MirrorPlainEquipment']
export type MirrorUnlinkedSubRecipe = Schemas['MirrorUnlinkedSubRecipe']

/** The shape `EquipmentList` takes. */
export interface EquipmentLine {
  equipment: EquipmentRef
  count: number | null
  note?: string
}

/**
 * An ingredient line as the page shows it. `plain` marks a line this
 * instance keeps as text; `unlinked` a sub-recipe that is not on this
 * instance, named by `ingredient.name` (its title, or empty when the source
 * does not share it).
 */
export interface ShownLine extends IngredientAmount {
  origin?: 'plain' | 'unlinked'
}

export function plainLineItem(line: MirrorPlainLine): ShownLine {
  return {
    ingredient_id: null,
    sub_recipe: null,
    name: line.name,
    amount: line.amount,
    unit: line.unit,
    note: line.note,
    origin: 'plain',
  }
}

export function unlinkedItem(line: MirrorUnlinkedSubRecipe): ShownLine {
  return {
    ingredient_id: null,
    sub_recipe: null,
    name: line.title ?? '',
    amount: line.amount,
    unit: line.unit,
    note: '',
    origin: 'unlinked',
  }
}

/**
 * The lines of one source step (index from 0): the step's own lines with the
 * plain and unlinked lines of that step put back at their source positions.
 * A position beyond the end goes last. `marks` (a variation's line marks by
 * index) are moved along, so each mark stays on its line.
 */
export function mergeStepLines(
  lines: IngredientAmount[],
  details: MirrorView | null | undefined,
  stepIndex: number | null,
  marks: (LineMark | null)[] = [],
): { items: ShownLine[]; marks: (LineMark | null)[] } {
  if (!details || stepIndex === null) return { items: lines, marks }
  const extras: { position: number; item: ShownLine }[] = [
    ...details.plain_lines
      .filter((l) => l.step === stepIndex)
      .map((l) => ({ position: l.position, item: plainLineItem(l) })),
    ...details.unlinked_sub_recipes
      .filter((l) => l.step === stepIndex)
      .map((l) => ({ position: l.position, item: unlinkedItem(l) })),
  ].sort((a, b) => a.position - b.position)
  if (!extras.length) return { items: lines, marks }
  const items: ShownLine[] = []
  const moved: (LineMark | null)[] = []
  let own = 0
  let next = 0
  const total = lines.length + extras.length
  for (let position = 0; position < total; position += 1) {
    const extra = extras[next]
    if (extra && (extra.position <= position || own >= lines.length)) {
      items.push(extra.item)
      moved.push(null)
      next += 1
    } else {
      items.push(lines[own]!)
      moved.push(marks[own] ?? null)
      own += 1
    }
  }
  return { items, marks: moved }
}

/** The plain equipment of one source step, shaped for `EquipmentList`. */
export function plainEquipmentOf(
  details: MirrorView | null | undefined,
  stepIndex: number | null,
): EquipmentLine[] {
  if (!details || stepIndex === null) return []
  return details.plain_equipment
    .filter((e) => e.step === stepIndex)
    .map((e, i) => plainEquipmentLine(e, `${stepIndex}-${i}`))
}

function plainEquipmentLine(item: MirrorPlainEquipment, key: string): EquipmentLine {
  return {
    equipment: { id: `plain-${key}`, name: item.name, kind: 'tool', icon: null },
    count: item.count,
    note: item.note,
  }
}

/** Every plain equipment item of the mirror once, for the "You'll need" card. */
export function allPlainEquipment(details: MirrorView | null | undefined): EquipmentLine[] {
  if (!details) return []
  const seen = new Set<string>()
  const lines: EquipmentLine[] = []
  details.plain_equipment.forEach((item, i) => {
    const key = item.name.trim().toLocaleLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    lines.push(plainEquipmentLine(item, `all-${i}`))
  })
  return lines
}

/**
 * The plain and unlinked lines for the summed ingredient list: plain lines
 * of the same name and unit add up, the way the backend sums catalogue
 * ingredients.
 */
export function extraIngredients(details: MirrorView | null | undefined): ShownLine[] {
  if (!details) return []
  const summed = new Map<string, ShownLine>()
  for (const line of details.plain_lines) {
    const key = `${line.name.trim().toLocaleLowerCase()}|${line.unit?.id ?? ''}|${line.amount === null}`
    const found = summed.get(key)
    if (found && found.amount !== null && line.amount !== null) {
      found.amount += line.amount
    } else if (!found) {
      summed.set(key, { ...plainLineItem(line), note: '' })
    }
  }
  return [...summed.values(), ...details.unlinked_sub_recipes.map(unlinkedItem)]
}

/** "by <author> · <instance>", or only the instance when no author is shown. */
export function attributionParams(source: MirrorSourceRef): { key: string; params: Record<string, string> } {
  return source.author_name
    ? { key: 'recipes.mirror.byAt', params: { name: source.author_name, instance: source.instance_name } }
    : { key: 'recipes.mirror.from', params: { instance: source.instance_name } }
}
