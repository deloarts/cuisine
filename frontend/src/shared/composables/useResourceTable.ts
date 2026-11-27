/**
 * The state of one management table: its filters in the URL, the rows per
 * page remembered on this device, and the page it shows. A change of the
 * filters or of the page size goes back to the first page and asks the
 * table's owner to load again; paging asks too. Hand the result to
 * `ResourceTable` as its `state`.
 *
 * `reload` is optional: a table that holds every row in the browser filters,
 * sorts and pages itself and needs no callback. A lazy table reads
 * `sortField` and `sortOrder` when it loads.
 */
import { ref, type ComputedRef, type Ref } from 'vue'
import { watchDebounced } from '@vueuse/core'

import { useTableRows } from './useTableRows'
import { useUrlFilters } from './useUrlFilters'
import type { UrlFilterSpec, UrlFilterValues } from './urlFilters'

export interface ResourceTableState {
  rows: Ref<number>
  rowOptions: number[]
  first: Ref<number>
  active: ComputedRef<number>
  /** The sorted column's field; `ResourceTable` sets the default on mount. */
  sortField: Ref<string | undefined>
  sortOrder: Ref<1 | -1>
  clear: () => void
  onPage: (event: { first: number; rows: number }) => void
  onSort: (event: { sortField: string | undefined; sortOrder: 1 | -1 }) => void
}

export interface ResourceTable<S extends UrlFilterSpec> extends ResourceTableState {
  filters: UrlFilterValues<S>
}

export function useResourceTable<S extends UrlFilterSpec>(
  tableKey: string,
  spec: S,
  reload?: () => unknown,
  debounce = 300,
): ResourceTable<S> {
  const { filters, active, clear } = useUrlFilters(spec)
  const { rows, options } = useTableRows(tableKey)
  const first = ref(0)

  const run = () => {
    if (reload) void Promise.resolve(reload()).catch(() => undefined)
  }

  watchDebounced(
    () => JSON.stringify(filters),
    () => {
      first.value = 0
      run()
    },
    { debounce },
  )

  function onPage(event: { first: number; rows: number }) {
    const resized = event.rows !== rows.value
    rows.value = event.rows
    first.value = resized ? 0 : event.first
    run()
  }

  const sortField = ref<string | undefined>()
  const sortOrder = ref<1 | -1>(1)

  // A lazy table sorts on the server, so a new order starts again at the
  // first page and asks the owner to load.
  function onSort(event: { sortField: string | undefined; sortOrder: 1 | -1 }) {
    sortField.value = event.sortField
    sortOrder.value = event.sortOrder
    first.value = 0
    run()
  }

  return { filters, active, clear, rows, rowOptions: options, first, sortField, sortOrder, onPage, onSort }
}
