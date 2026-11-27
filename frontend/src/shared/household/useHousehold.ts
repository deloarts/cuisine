/**
 * The signed-in user's household, loaded once and shared by every page that
 * shows it: the household page itself, the meal plan (which offers the
 * household's plan next to the personal one) and the shopping lists (which
 * mark the household's default list). A page that changes the membership hands the
 * new state to `set()`, so the others follow without a second request.
 */
import { computed, ref } from 'vue'

import type { Schemas } from '@/core/api/generated'
import { onSignOut, useCurrentUserStore } from '@/core/stores/currentUserStore'
import { getMyHousehold } from '@/shared/api/household'

export type HouseholdResponse = Schemas['HouseholdResponse']

const household = ref<HouseholdResponse | null>(null)
const loaded = ref(false)
let pending: Promise<HouseholdResponse | null> | null = null
// The user the cache belongs to, so signing in as someone else in the same
// tab never shows the previous person's household.
let loadedFor: string | null = null

async function fetchMine(): Promise<HouseholdResponse | null> {
  const { household: mine } = await getMyHousehold()
  household.value = mine
  loaded.value = true
  return mine
}

export function useHousehold() {
  const currentUser = useCurrentUserStore()

  /** Reads the household once; later calls share the first answer. */
  function load(): Promise<HouseholdResponse | null> {
    const userId = currentUser.user?.id ?? null
    if (userId !== loadedFor) resetHousehold()
    loadedFor = userId
    if (pending) return pending
    pending = fetchMine().catch((err: unknown) => {
      pending = null
      throw err
    })
    return pending
  }

  function reload(): Promise<HouseholdResponse | null> {
    pending = null
    return load()
  }

  function set(next: HouseholdResponse | null) {
    household.value = next
    loaded.value = true
    pending = Promise.resolve(next)
  }

  const shoppingListId = computed(() => household.value?.shopping_list_id ?? null)

  return { household, loaded, shoppingListId, load, reload, set }
}

/** Forgets the cached household, for sign-out and tests. */
export function resetHousehold() {
  household.value = null
  loaded.value = false
  pending = null
  loadedFor = null
}

onSignOut(resetHousehold)
