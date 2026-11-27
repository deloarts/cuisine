import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { CurrentUserResponse } from '@/core/types/user'

function user(overrides: Partial<CurrentUserResponse> = {}): CurrentUserResponse {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    full_name: 'Cook',
    nickname: null,
    show_nickname: false,
    display_name: 'Cook',
    email: 'cook@example.com',
    is_active: true,
    is_systemuser: false,
    permissions: [],
    effective_permissions: ['read:settings'],
    group_ids: [],
    language: 'enGB',
    totp_enabled: false,
    totp_mandatory: false,
    created: '2026-11-21T00:00:00Z',
    last_logged_in: null,
    theme_preset: 'Aura',
    theme_surface: 'neutral',
    theme_primary: 'cuisine',
    theme_dark_mode: false,
    share_restrictions_with_hosts: false,
    default_recipe_visibility: null,
    show_name_on_public_recipes: false,
    show_name_on_paired_instances: true,
    amount_style: 'decimals',
    recipe_show_tips: true,
    recipe_show_notes: true,
    recipe_show_cooked: true,
    recipe_show_rating: true,
    recipe_highlight_mentions: true,
    keep_screen_on: true,
    privacy_acknowledgement_pending: false,
    ...overrides,
  }
}

describe('currentUserStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('checks effective permissions', () => {
    const store = useCurrentUserStore()
    store.user = user()
    expect(store.hasPermission('read:settings')).toBe(true)
    expect(store.hasPermission('write:users')).toBe(false)
  })

  it('lets the system user do everything', () => {
    const store = useCurrentUserStore()
    store.user = user({ is_systemuser: true, effective_permissions: [] })
    expect(store.hasPermission('write:settings')).toBe(true)
  })

  it('knows when the settings wait for two-factor authentication', () => {
    const store = useCurrentUserStore()
    store.user = user({ effective_permissions: ['read:settings'], totp_enabled: false })
    expect(store.settingsNeedTotp).toBe(true)
    store.user = user({ effective_permissions: ['read:settings'], totp_enabled: true })
    expect(store.settingsNeedTotp).toBe(false)
    store.user = user({ effective_permissions: ['write:recipes'], totp_enabled: false })
    expect(store.settingsNeedTotp).toBe(false)
    store.user = user({ is_systemuser: true, effective_permissions: [], totp_enabled: false })
    expect(store.settingsNeedTotp).toBe(false)
  })

  it('marks a session that ended while signed in as expired', () => {
    const store = useCurrentUserStore()
    store.user = user()
    store.sessionExpired()
    expect(store.expired).toBe(true)
    expect(store.isSignedIn).toBe(false)
  })

  it('brings the privacy statement back after a refused request', () => {
    const store = useCurrentUserStore()
    store.requirePrivacyAcknowledgement()
    expect(store.user).toBeNull()
    store.user = user()
    store.requirePrivacyAcknowledgement()
    expect(store.user?.privacy_acknowledgement_pending).toBe(true)
  })
})
