/**
 * Text matching for tables that filter in the browser: case and diacritics
 * do not count, so "erdapfel" finds "Erdäpfel", and every word of the query
 * must appear in one of the values.
 */

export function normaliseText(value: string): string {
  return value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

export function matchesText(query: string | null | undefined, ...values: (string | null | undefined)[]): boolean {
  if (!query?.trim()) return true
  const haystack = normaliseText(values.filter(Boolean).join(' '))
  return normaliseText(query)
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word))
}
