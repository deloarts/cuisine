import { computed, onScopeDispose, ref, watch } from 'vue'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'

/**
 * Drives the header countdown to `currentUserStore.sessionExpiresAt`, which
 * only the system account has: its session ends 15 minutes after sign-in.
 *
 * The remaining time is recomputed from the wall clock on every tick rather
 * than counted down, so a tab that slept catches up to the real time. The
 * one second interval only runs while an expiry is set. When it reaches
 * zero it calls `sessionExpired()` once, the same path a 401 takes, so the
 * user is sent to sign in without waiting for the next failed request.
 */
export function useSessionCountdown() {
  const userStore = useCurrentUserStore()

  const now = ref(Date.now())
  let intervalId: ReturnType<typeof setInterval> | undefined
  let expiredNotified = false

  function stopInterval() {
    if (intervalId === undefined) return
    clearInterval(intervalId)
    intervalId = undefined
  }

  function startInterval() {
    if (intervalId !== undefined) return
    now.value = Date.now()
    intervalId = setInterval(() => {
      now.value = Date.now()
    }, 1000)
  }

  watch(
    () => userStore.sessionExpiresAt,
    (expiresAt) => {
      expiredNotified = false
      if (expiresAt === null) {
        stopInterval()
        return
      }
      startInterval()
    },
    { immediate: true },
  )

  const remainingSeconds = computed(() => {
    const expiresAt = userStore.sessionExpiresAt
    if (expiresAt === null) return 0
    return Math.max(0, Math.ceil((expiresAt - now.value) / 1000))
  })

  watch(remainingSeconds, (seconds) => {
    if (seconds !== 0 || userStore.sessionExpiresAt === null || expiredNotified) return
    expiredNotified = true
    userStore.sessionExpired()
  })

  const isActive = computed(() => userStore.sessionExpiresAt !== null)
  const isWarning = computed(() => isActive.value && remainingSeconds.value < 60)

  const label = computed(() => {
    const total = remainingSeconds.value
    const minutes = Math.floor(total / 60)
    const seconds = total % 60
    return `${minutes}:${String(seconds).padStart(2, '0')}`
  })

  onScopeDispose(() => {
    stopInterval()
  })

  return { remainingSeconds, label, isActive, isWarning }
}
