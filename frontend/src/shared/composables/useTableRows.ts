/**
 * The rows-per-page choice of one table, remembered on this device so a
 * user who prefers long pages keeps them across visits.
 */
import { ref, watch } from 'vue'

import { safeStorage } from '@/core/utils/safeStorage'

export const TABLE_ROWS_PER_PAGE_OPTIONS = [10, 25, 50, 100]
export const TABLE_DEFAULT_ROWS = 25

export function useTableRows(tableKey: string) {
  const storageKey = `tableRows:${tableKey}`
  const stored = Number(safeStorage.get(storageKey))
  const rows = ref(TABLE_ROWS_PER_PAGE_OPTIONS.includes(stored) ? stored : TABLE_DEFAULT_ROWS)
  watch(rows, (value) => safeStorage.set(storageKey, String(value)))
  return { rows, options: TABLE_ROWS_PER_PAGE_OPTIONS }
}
