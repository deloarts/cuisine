/**
 * The app's navigation entries, shared by the sidebar and the phone's bottom
 * nav so both always offer the same places with the same permissions.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { ADMIN_PERMISSIONS } from '@/features/admin-settings/adminTabs'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

export interface NavEntry {
  to: string
  icon: string
  label: string
  /** Any one of these opens the entry; without, every signed-in user sees it. */
  permissions?: string[]
  /** Active only on the exact path, for the home page. */
  exact?: boolean
}

export function useNavigation() {
  const { t } = useI18n()
  const currentUser = useCurrentUserStore()

  const visible = (entries: NavEntry[]) =>
    entries.filter(
      (entry) => !entry.permissions || entry.permissions.some((p) => currentUser.hasPermission(p)),
    )

  // The everyday places, in the order a meal comes together.
  const main = computed(() =>
    visible([
      { to: '/', icon: 'mdi-home-outline', label: t('nav.home'), exact: true },
      { to: '/recipes', icon: 'mdi-book-open-page-variant-outline', label: t('nav.recipes') },
      { to: '/meal-plan', icon: 'mdi-calendar-week-outline', label: t('nav.mealPlan') },
      { to: '/shopping', icon: 'mdi-cart-outline', label: t('nav.shopping') },
      { to: '/cooked', icon: 'mdi-calendar-heart', label: t('nav.cooked') },
      { to: '/household', icon: 'mdi-home-heart', label: t('nav.household') },
    ]),
  )

  // The kitchen: the cook's own equipment and the catalogue behind the recipes.
  const kitchen = computed(() =>
    visible([
      { to: '/kitchen', icon: 'mdi-stove', label: t('nav.myKitchen') },
      { to: '/ingredients', icon: 'mdi-carrot', label: t('nav.ingredients') },
      { to: '/resources', icon: 'mdi-tag-multiple-outline', label: t('nav.resources') },
    ]),
  )

  // The admin area, behind the one icon at the sidebar's foot. Any permission
  // that opens one of its tabs shows it.
  const admin = computed<NavEntry | null>(() =>
    ADMIN_PERMISSIONS.some((p) => currentUser.hasPermission(p))
      ? { to: '/admin', icon: 'mdi-cog-outline', label: t('nav.admin'), permissions: ADMIN_PERMISSIONS }
      : null,
  )

  const account = computed<NavEntry>(() => ({
    to: '/account',
    icon: 'mdi-account-cog-outline',
    label: t('nav.account'),
  }))

  // The phone's bottom nav: the four places used at the stove and in the
  // shop. Everything else sits behind More.
  const bottom = computed(() => main.value.slice(0, 4))

  return { main, kitchen, admin, account, bottom }
}
