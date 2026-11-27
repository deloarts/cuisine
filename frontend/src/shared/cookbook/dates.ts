/**
 * Calendar dates as local `YYYY-MM-DD` strings, the shape the API takes for
 * meal plans and cook events, so no time zone can shift a meal onto another
 * day. Weeks start on the instance's first day of the week (Monday unless
 * the admin chose otherwise).
 */
import { firstWeekday } from '@/core/utils/displayFormats'

/** A local date as `YYYY-MM-DD`. */
export function isoDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Parses `YYYY-MM-DD` as a local date at midnight. */
export function parseIsoDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1)
}

export function addDays(value: string, days: number): string {
  const date = parseIsoDate(value)
  date.setDate(date.getDate() + days)
  return isoDate(date)
}

/** The first day of the week that holds `value`; `first` is a JavaScript weekday (Sunday 0). */
export function startOfWeek(value: string, first: number = firstWeekday()): string {
  const date = parseIsoDate(value)
  const weekday = (date.getDay() - first + 7) % 7
  date.setDate(date.getDate() - weekday)
  return isoDate(date)
}
