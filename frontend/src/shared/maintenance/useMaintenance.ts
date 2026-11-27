/**
 * Whether the instance is in maintenance mode, read from the public instance
 * info in the user's language. The shell's banner shows it; the admin's
 * maintenance section calls `refresh()` after a change so the banner follows
 * at once instead of on the next poll.
 */
import { ref } from 'vue'

import { publicApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'

export type PublicMaintenance = Schemas['PublicMaintenanceResponse']
type ContentLocale = Schemas['ContentLocale']

const state = ref<PublicMaintenance | null>(null)
let lastLocale: ContentLocale = 'de-AT'

async function refresh(locale: ContentLocale = lastLocale): Promise<void> {
  lastLocale = locale
  try {
    const info = (await publicApi.get<Schemas['PublicInfoResponse']>('/info', { params: { locale } })).data
    state.value = info.maintenance
  } catch {
    // An unreachable backend says nothing about maintenance; keep what we knew.
  }
}

export function useMaintenance() {
  return { maintenance: state, refresh }
}
