/**
 * Binds a filter spec to the current route's query: the filters start from
 * the URL, every change replaces the query (no new history entry per
 * keystroke), and navigating back or forward restores the filters. Query
 * keys outside the spec are kept.
 */
import { computed, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { activeCount, emptyValues, parseQuery, toQuery, type UrlFilterSpec, type UrlFilterValues } from './urlFilters'

export function useUrlFilters<S extends UrlFilterSpec>(spec: S) {
  const route = useRoute()
  const router = useRouter()
  const filters = reactive(parseQuery(spec, route.query)) as UrlFilterValues<S>

  const serialized = computed(() => JSON.stringify(toQuery(spec, filters)))

  watch(serialized, () => {
    const others = Object.fromEntries(Object.entries(route.query).filter(([key]) => !(key in spec)))
    void router.replace({ query: { ...others, ...toQuery(spec, filters) } })
  })

  watch(
    () => route.query,
    (query) => {
      const next = parseQuery(spec, query)
      if (JSON.stringify(toQuery(spec, next)) !== serialized.value) Object.assign(filters, next)
    },
  )

  const active = computed(() => activeCount(spec, filters))

  function clear() {
    Object.assign(filters, emptyValues(spec))
  }

  return { filters, active, clear }
}
