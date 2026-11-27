/**
 * Week arithmetic for the meal plan, on the shared calendar-date helpers.
 */
import { addDays } from '@/shared/cookbook/dates'
import type { MealSlot } from '@/shared/cookbook/types'

export { addDays, isoDate, parseIsoDate, startOfWeek } from '@/shared/cookbook/dates'

export const SLOTS: MealSlot[] = ['breakfast', 'lunch', 'dinner', 'snack']

/** The seven dates of the week that starts on `first`. */
export function weekDays(first: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(first, i))
}

/** The entries of one day and slot, in the order they were planned. */
export function entriesFor<T extends { plan_date: string; slot: string }>(
  entries: T[],
  day: string,
  slot: MealSlot,
): T[] {
  return entries.filter((e) => e.plan_date === day && e.slot === slot)
}
