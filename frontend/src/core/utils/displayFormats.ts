/**
 * The instance's display defaults from the public info: how dates and times
 * are written and which day a week starts on. The public info store sets
 * them once it has loaded; until then they are the usual European ones.
 */
import type { Schemas } from '@/core/api/generated'

export type DateFormat = Schemas['DateFormat']
export type TimeFormat = Schemas['TimeFormat']
export type Weekday = Schemas['Weekday']

export interface DisplayFormats {
  date_format: DateFormat
  time_format: TimeFormat
  first_day_of_week: Weekday
}

export const DEFAULT_FORMATS: DisplayFormats = {
  date_format: 'dd.mm.yyyy',
  time_format: '24h',
  first_day_of_week: 'monday',
}

let current: DisplayFormats = { ...DEFAULT_FORMATS }

export function setDisplayFormats(formats: Partial<DisplayFormats>): void {
  current = { ...current, ...formats }
}

export function displayFormats(): DisplayFormats {
  return current
}

/** The JavaScript weekday number (Sunday 0) a week starts on. */
export function firstWeekday(): number {
  return { sunday: 0, monday: 1, saturday: 6 }[current.first_day_of_week]
}

const pad = (n: number) => String(n).padStart(2, '0')

/** A date in the instance's date format. */
export function formatDateParts(date: Date, format: DateFormat = current.date_format): string {
  const d = pad(date.getDate())
  const m = pad(date.getMonth() + 1)
  const y = String(date.getFullYear())
  switch (format) {
    case 'dd/mm/yyyy':
      return `${d}/${m}/${y}`
    case 'yyyy-mm-dd':
      return `${y}-${m}-${d}`
    case 'mm/dd/yyyy':
      return `${m}/${d}/${y}`
    default:
      return `${d}.${m}.${y}`
  }
}

/** A time of day in the instance's time format. */
export function formatTimeParts(date: Date, format: TimeFormat = current.time_format): string {
  const minutes = pad(date.getMinutes())
  if (format === '12h') {
    const hours = date.getHours() % 12 || 12
    return `${hours}:${minutes} ${date.getHours() < 12 ? 'am' : 'pm'}`
  }
  return `${pad(date.getHours())}:${minutes}`
}
