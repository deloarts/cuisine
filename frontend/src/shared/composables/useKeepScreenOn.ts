import { onBeforeUnmount, watch } from 'vue'
import { useWakeLock } from '@vueuse/core'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'

/**
 * Keeps the screen from turning off while the calling page is open, so a
 * phone propped up in the kitchen or carried through the shop stays readable.
 * It follows the reader's `keep_screen_on` account setting and lets go when
 * the page closes. The browser drops the lock while the tab is hidden and
 * VueUse asks again once it is visible; where the Screen Wake Lock API is
 * missing (or the page is not served over HTTPS) nothing happens.
 */
export function useKeepScreenOn(): void {
  const currentUser = useCurrentUserStore()
  const lock = useWakeLock()

  function release() {
    void lock.release().catch(() => undefined)
  }

  watch(
    () => currentUser.user?.keep_screen_on ?? true,
    (on) => {
      if (!lock.isSupported.value) return
      if (on) void lock.request('screen').catch(() => undefined)
      else release()
    },
    { immediate: true },
  )

  onBeforeUnmount(release)
}
