/**
 * The two list modes as the list view shows them. A continuous list keeps
 * ticked items under "Recently bought", newest first and with undo, until
 * the backend's purge removes them a configured number of hours after the
 * tick. A normal list keeps every item and shows ahead of time the day it
 * deletes itself unless someone uses it or a member keeps it.
 */
import type { Schemas } from '@/core/api/generated'

import type { ShoppingItem } from './grouping'

export type ShoppingListMode = Schemas['ShoppingListMode']
type ListLike = Pick<Schemas['ShoppingListSummaryResponse'], 'mode' | 'deletes_on'>

/** The days before the deletion day from which the notice turns into a warning. */
export const DELETION_WARNING_DAYS = 7

/** Ticked items, the most recently ticked first; items without a tick time last. */
export function recentlyBought(items: ShoppingItem[]): ShoppingItem[] {
  const time = (item: ShoppingItem) => (item.checked_at ? Date.parse(item.checked_at) : 0)
  return items.filter((i) => i.checked).sort((a, b) => time(b) - time(a) || a.name.localeCompare(b.name))
}

/** When the purge removes a ticked item from a continuous list, or null if unknown. */
export function leavesAt(item: ShoppingItem, windowHours: number): Date | null {
  if (!item.checked || !item.checked_at) return null
  return new Date(Date.parse(item.checked_at) + windowHours * 3_600_000)
}

/**
 * The items after undoing the purchase of one of them, shown at once while
 * the request is under way. The original array is left alone, so a failed
 * request restores it.
 */
export function undoPurchase(items: ShoppingItem[], itemId: string): ShoppingItem[] {
  return items.map((i) => (i.id === itemId ? { ...i, checked: false, checked_by: null, checked_at: null } : i))
}

/**
 * The day a normal list deletes itself, as a local calendar date (the API
 * sends a plain date, which `new Date()` would read as UTC midnight and can
 * shift to the day before), or null when it never does.
 */
export function deletionDay(list: ListLike): Date | null {
  if (list.mode !== 'normal' || !list.deletes_on) return null
  const [year = 0, month = 1, day = 1] = list.deletes_on.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** Whether the deletion day is close enough to show the notice as a warning. */
export function deletionIsNear(list: ListLike, today: Date = new Date()): boolean {
  const day = deletionDay(list)
  if (!day) return false
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return (day.getTime() - start.getTime()) / 86_400_000 <= DELETION_WARNING_DAYS
}
