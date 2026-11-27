import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SYSTEM_USER_WARNING_SESSION_KEY, useCurrentUserStore } from '@/core/stores/currentUserStore'

const get = vi.fn<(path: string) => Promise<unknown>>()

vi.mock('@/core/api/webRequest', () => ({
  webApi: { get: (path: string) => get(path) },
}))

function me(isSystemUser: boolean) {
  return {
    email: isSystemUser ? 'admin@example.com' : 'cook@example.com',
    is_systemuser: isSystemUser,
    language: 'enGB',
    theme_preset: 'Aura',
    theme_surface: 'neutral',
    theme_primary: 'cuisine',
    theme_dark_mode: false,
  }
}

function answer(isSystemUser: boolean, session: { expires_at: string | null; server_time: string }) {
  get.mockImplementation((path: string) =>
    Promise.resolve(path === '/users/me' ? me(isSystemUser) : session),
  )
}

describe('currentUserStore for the system account', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-22T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
    get.mockReset()
  })

  it('reads the session end corrected for clock skew and asks for the warning', async () => {
    // The server's clock runs a minute ahead of the browser's.
    answer(true, { expires_at: '2026-11-22T12:16:00Z', server_time: '2026-11-22T12:01:00Z' })
    const store = useCurrentUserStore()
    await store.refresh()

    expect(store.sessionExpiresAt).toBe(Date.parse('2026-11-22T12:15:00Z'))
    expect(store.systemUserWarningPending).toBe(true)
  })

  it('shows the warning once per tab until the session ends', async () => {
    answer(true, { expires_at: '2026-11-22T12:15:00Z', server_time: '2026-11-22T12:00:00Z' })
    const store = useCurrentUserStore()
    await store.refresh()
    store.acknowledgeSystemUserWarning()
    expect(sessionStorage.getItem(SYSTEM_USER_WARNING_SESSION_KEY)).not.toBeNull()

    await store.refresh()
    expect(store.systemUserWarningPending).toBe(false)

    store.sessionExpired()
    expect(store.sessionExpiresAt).toBeNull()
    expect(sessionStorage.getItem(SYSTEM_USER_WARNING_SESSION_KEY)).toBeNull()
  })

  it('leaves ordinary accounts without countdown or warning', async () => {
    answer(false, { expires_at: '2026-12-22T12:00:00Z', server_time: '2026-11-22T12:00:00Z' })
    const store = useCurrentUserStore()
    await store.refresh()

    expect(store.sessionExpiresAt).toBeNull()
    expect(store.systemUserWarningPending).toBe(false)
    expect(get).not.toHaveBeenCalledWith('/users/me/sessions/current')
  })
})
