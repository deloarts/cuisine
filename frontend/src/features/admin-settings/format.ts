/** Byte counts and durations for the admin readings. */

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

export function formatBytes(bytes: number | null | undefined, locale: string): string {
  if (bytes === null || bytes === undefined) return '–'
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit++
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)} ${UNITS[unit]}`
}

/** "3 d 4 h", "5 h 12 min" or "7 min" since `since`, measured at `now`. */
export function formatUptime(since: string, now: Date = new Date()): string {
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(since).getTime()) / 60000))
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  if (days) return `${days} d ${hours} h`
  if (hours) return `${hours} h ${mins} min`
  return `${mins} min`
}
