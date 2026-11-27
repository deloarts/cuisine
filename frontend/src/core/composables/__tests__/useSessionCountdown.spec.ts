import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick } from 'vue'

import { useSessionCountdown } from '@/core/composables/useSessionCountdown'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

describe('useSessionCountdown', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-22T12:00:00Z'))
  })

  afterEach(() => vi.useRealTimers())

  it('stays hidden without a session end', () => {
    const scope = effectScope()
    const countdown = scope.run(() => useSessionCountdown())!
    expect(countdown.isActive.value).toBe(false)
    scope.stop()
  })

  it('counts down, warns in the last minute and ends the session at zero', async () => {
    const store = useCurrentUserStore()
    const sessionExpired = vi.spyOn(store, 'sessionExpired')
    store.sessionExpiresAt = Date.now() + 15 * 60 * 1000

    const scope = effectScope()
    const countdown = scope.run(() => useSessionCountdown())!
    expect(countdown.label.value).toBe('15:00')
    expect(countdown.isWarning.value).toBe(false)

    vi.advanceTimersByTime(14 * 60 * 1000 + 30 * 1000)
    await nextTick()
    expect(countdown.label.value).toBe('0:30')
    expect(countdown.isWarning.value).toBe(true)

    vi.advanceTimersByTime(30 * 1000)
    await nextTick()
    expect(countdown.remainingSeconds.value).toBe(0)
    expect(sessionExpired).toHaveBeenCalledTimes(1)
    scope.stop()
  })
})
