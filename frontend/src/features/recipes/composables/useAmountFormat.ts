/**
 * Formats recipe amounts the way the signed-in user chose on the account
 * page: exact decimals by default, kitchen fractions of a litre or kilogram
 * on request. Visitors who are not signed in get the default.
 */
import { getActivePinia } from 'pinia'
import { computed } from 'vue'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { type AmountStyle, formatAmount } from '@/features/recipes/utils/scaling'

interface UnitLike {
  kind?: string | null
  code?: string | null
}

export function useAmountFormat() {
  // Components also render where no store is installed (embedded previews,
  // their tests); they read the default there.
  const currentUser = getActivePinia() ? useCurrentUserStore() : null
  const style = computed<AmountStyle>(() => currentUser?.user?.amount_style ?? 'decimals')

  function format(amount: number | null, locale: string, unit?: UnitLike | null): string {
    return formatAmount(amount, locale, unit?.kind ?? undefined, {
      style: style.value,
      unitCode: unit?.code ?? null,
    })
  }

  return { style, format }
}
