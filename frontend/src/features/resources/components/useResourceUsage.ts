/**
 * How often each resource is used, for the "Used" column of the resource
 * tabs. The counts load only on the resources page, apart from the shared
 * resource cache, so the pickers elsewhere never pay for them. Tags, units
 * and equipment count the recipes the viewer may see that use them, each
 * recipe once; categories and families count the ingredients in them.
 *
 * Each tab filters the column by a range kept in the URL (`USAGE_FILTERS`)
 * and sorts it by the count.
 */
import { computed, ref, type WritableComputedRef } from 'vue'

import type { NumberRange } from '@/shared/components/table-filters/NumberRangeRowFilter.vue'
import { resourceUsage, type ResourceUsageResponse } from '@/features/resources/api/resources'

export type UsageKind = keyof ResourceUsageResponse

export const USAGE_FILTERS = { usageMin: 'number', usageMax: 'number' } as const

interface UsageRange {
  usageMin: number | null
  usageMax: number | null
}

const counts = ref<Partial<Record<UsageKind, Map<string, number>>>>({})

export function useResourceUsage() {
  async function reload(): Promise<void> {
    const usage = await resourceUsage()
    counts.value = Object.fromEntries(
      Object.entries(usage).map(([kind, entries]) => [kind, new Map(entries.map((e) => [e.id, e.usage_count]))]),
    )
  }

  function count(kind: UsageKind, id: string): number {
    return counts.value[kind]?.get(id) ?? 0
  }

  return { count, reload }
}

/** Whether a count lies in the range the filters hold, both ends included. */
export function inUsageRange(count: number, filters: UsageRange): boolean {
  if (filters.usageMin !== null && count < filters.usageMin) return false
  if (filters.usageMax !== null && count > filters.usageMax) return false
  return true
}

/** The filters' two bounds as the one value `NumberRangeFilter` binds. */
export function usageRangeModel(filters: UsageRange): WritableComputedRef<NumberRange> {
  return computed<NumberRange>({
    get: (): NumberRange =>
      filters.usageMin === null && filters.usageMax === null ? null : [filters.usageMin, filters.usageMax],
    set: (value: NumberRange) => {
      filters.usageMin = value?.[0] ?? null
      filters.usageMax = value?.[1] ?? null
    },
  })
}
