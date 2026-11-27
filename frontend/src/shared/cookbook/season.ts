/**
 * Season months of an ingredient, 1 (January) to 12 (December). An empty
 * list means the ingredient is not seasonal. The table shows the months as
 * ranges, and a range may run over the turn of the year (November to
 * February).
 */

export const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const

/** The months with `month` switched on or off, sorted and without duplicates. */
export function toggleMonth(months: readonly number[], month: number): number[] {
  const set = new Set(months)
  if (set.has(month)) set.delete(month)
  else set.add(month)
  return [...set].filter((m) => m >= 1 && m <= 12).sort((a, b) => a - b)
}

/**
 * The months as runs of consecutive months, each `[first, last]`. A run that
 * ends in December and one that starts in January join into one over the
 * turn of the year; all twelve months make a single run from January.
 */
export function monthRanges(months: readonly number[]): [number, number][] {
  const sorted = [...new Set(months)].filter((m) => m >= 1 && m <= 12).sort((a, b) => a - b)
  if (!sorted.length) return []
  if (sorted.length === 12) return [[1, 12]]
  const runs: [number, number][] = []
  for (const month of sorted) {
    const last = runs[runs.length - 1]
    if (last && last[1] === month - 1) last[1] = month
    else runs.push([month, month])
  }
  const first = runs[0]!
  const end = runs[runs.length - 1]!
  if (runs.length > 1 && first[0] === 1 && end[1] === 12) {
    runs.shift()
    end[1] = first[1]
  }
  return runs
}

/** The ranges as text, such as "Apr–Jun, Nov–Feb", with `label` naming a month. */
export function formatSeason(months: readonly number[], label: (month: number) => string): string {
  return monthRanges(months)
    .map(([a, b]) => (a === b ? label(a) : `${label(a)}–${label(b)}`))
    .join(', ')
}

/** The short name of a month (1 to 12) in a BCP 47 locale, such as "Mar" or "März". */
export function monthName(month: number, locale: string, width: 'short' | 'long' = 'short'): string {
  return new Intl.DateTimeFormat(locale, { month: width, timeZone: 'UTC' }).format(
    new Date(Date.UTC(2000, month - 1, 1)),
  )
}
