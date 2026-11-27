/**
 * Calendar days as the recipes feature shows them. A cook event's day is a
 * plain `YYYY-MM-DD` date without a time zone, so it is read as a local day;
 * `new Date('2025-03-01')` would read it as UTC midnight and show the day
 * before west of Greenwich.
 */
import type { AppLocale } from '@/core/i18n'
import { localeTag } from '@/core/utils/dates'

export function parseDay(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1)
}

export function formatDay(value: string, locale: AppLocale | string): string {
  return new Intl.DateTimeFormat(localeTag(locale as AppLocale), { dateStyle: 'medium' }).format(
    parseDay(value),
  )
}

/** Today, or another day, as a `YYYY-MM-DD` string in the local time zone. */
export function isoDay(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
