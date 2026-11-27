/**
 * The kinds of kitchen equipment in the order lists group them, and the
 * icon class of an item. Items store an @mdi/font icon name without the
 * `mdi-` prefix; one without an icon shows a generic one. Kind labels live
 * in the core `equipmentKinds` namespace.
 */
import type { EquipmentKind } from './types'

export const EQUIPMENT_KINDS: EquipmentKind[] = ['cookware', 'bakeware', 'appliance', 'utensil']

export const DEFAULT_EQUIPMENT_ICON = 'silverware-variant'

export function equipmentIcon(icon: string | null | undefined): string {
  return `mdi mdi-${icon || DEFAULT_EQUIPMENT_ICON}`
}
