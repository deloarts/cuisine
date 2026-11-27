/**
 * Whether the screen is at least the small breakpoint `$bp-sm` (48rem),
 * where management tables gain their columns and filter row. Below it they
 * fall back to one stacked column.
 */
import { useMediaQuery } from '@vueuse/core'

export function useWideScreen() {
  return useMediaQuery('(min-width: 48rem)')
}

/**
 * Whether the screen is at least the large breakpoint `$bp-lg` (70rem),
 * where the meal plan lays its week out as seven columns and has room for
 * more beside it.
 */
export function useLargeScreen() {
  return useMediaQuery('(min-width: 70rem)')
}
