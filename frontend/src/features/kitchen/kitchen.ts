/**
 * The checklist logic of "My kitchen": the equipment catalogue grouped by
 * kind for ticking, and the selection the list starts from. Before the
 * kitchen is set up the basic items are ticked in advance; afterwards the
 * kitchen's own items are.
 */
import { matchesText } from '@/shared/composables/tableText'
import { EQUIPMENT_KINDS } from '@/shared/cookbook/equipment'
import type { EquipmentKind, EquipmentResponse } from '@/shared/cookbook/types'

export interface KitchenGroup {
  kind: EquipmentKind
  items: EquipmentResponse[]
}

/**
 * The items to offer, grouped by kind in the catalogue's kind order and
 * sorted by name, narrowed by a search over names and other names. Drafts
 * only show when they are already ticked, so an agent's unreviewed item does
 * not clutter the list.
 */
export function groupByKind(
  catalogue: readonly EquipmentResponse[],
  selected: ReadonlySet<string>,
  query = '',
): KitchenGroup[] {
  const visible = catalogue.filter(
    (item) =>
      (item.status !== 'draft' || selected.has(item.id)) &&
      matchesText(query, item.name, ...Object.values(item.aliases).flat()),
  )
  return EQUIPMENT_KINDS.map((kind) => ({
    kind,
    items: visible.filter((item) => item.kind === kind).sort((a, b) => a.name.localeCompare(b.name)),
  })).filter((group) => group.items.length > 0)
}

/** The ids ticked when the checklist opens. */
export function initialSelection(
  kitchen: { set_up: boolean; equipment: readonly { id: string }[] },
  catalogue: readonly EquipmentResponse[],
): Set<string> {
  if (kitchen.set_up) return new Set(kitchen.equipment.map((e) => e.id))
  return new Set(catalogue.filter((item) => item.basic && item.status !== 'draft').map((item) => item.id))
}
