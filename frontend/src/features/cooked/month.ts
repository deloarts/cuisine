/**
 * Month arithmetic for the cooking calendar: the grid of whole
 * weeks that covers a month, and the date range to ask the API for. Dates
 * are local `YYYY-MM-DD` strings, like the meal plan's.
 */
import { addDays, isoDate, parseIsoDate, startOfWeek } from '@/shared/cookbook/dates'

export interface MonthCell {
  date: string
  inMonth: boolean
}

/** `YYYY-MM` of a date string. */
export function monthOf(date: string): string {
  return date.slice(0, 7)
}

export function shiftMonth(month: string, by: number): string {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y ?? 1970, (m ?? 1) - 1 + by, 1)
  return isoDate(d).slice(0, 7)
}

export function monthRange(month: string): { from: string; to: string } {
  const first = `${month}-01`
  const next = `${shiftMonth(month, 1)}-01`
  return { from: first, to: addDays(next, -1) }
}

/** The weeks shown for a month: from the first weekday on or before the 1st to the week's end on or after the last day. */
export function monthGrid(month: string): MonthCell[][] {
  const { from, to } = monthRange(month)
  const weeks: MonthCell[][] = []
  let day = startOfWeek(from)
  while (day <= to) {
    const week: MonthCell[] = []
    for (let i = 0; i < 7; i++) {
      week.push({ date: day, inMonth: monthOf(day) === month })
      day = addDays(day, 1)
    }
    weeks.push(week)
  }
  return weeks
}

/** Events keyed by their date, for the cells. */
export function byDate<T extends { cooked_on: string }>(events: T[]): Map<string, T[]> {
  const map = new Map<string, T[]>()
  for (const event of events) {
    const list = map.get(event.cooked_on) ?? []
    list.push(event)
    map.set(event.cooked_on, list)
  }
  return map
}

/** The short weekday names, from the first day of the week, for the grid header. */
export function weekdayNames(locale: string): string[] {
  const monday = parseIsoDate(startOfWeek('2026-11-18'))
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return new Intl.DateTimeFormat(locale, { weekday: 'short' }).format(d)
  })
}

/** Up to two initials of a person's name, for the small calendar badges. */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
