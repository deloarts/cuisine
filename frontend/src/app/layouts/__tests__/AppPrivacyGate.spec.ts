import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { AxiosError, AxiosHeaders } from 'axios'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ConfirmDialog from 'openvue/confirmdialog'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import AppPrivacyGate from '@/app/layouts/AppPrivacyGate.vue'
import type { LegalPage } from '@/shared/api/legal'
import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { CurrentUserResponse } from '@/core/types/user'

const getLegalPage = vi.fn<(kind: string, locale: string) => Promise<LegalPage>>()
const acknowledgePrivacy = vi.fn<(version: number) => Promise<void>>()
const declinePrivacy = vi.fn<() => Promise<void>>()

vi.mock('@/shared/api/legal', () => ({
  getLegalPage: (kind: string, locale: string) => getLegalPage(kind, locale),
  acknowledgePrivacy: (version: number) => acknowledgePrivacy(version),
  declinePrivacy: () => declinePrivacy(),
}))

function statement(version: number): LegalPage {
  return { kind: 'privacy', version, locale: 'en-GB', body: `# Statement ${version}`, published_at: '2026-11-21T00:00:00Z' }
}

function stale(): AxiosError {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('x', 'ERR', config, null, {
    status: 409,
    statusText: '',
    headers: {},
    config,
    data: { code: 'StalePrivacyVersionError' },
  })
}

async function mountGate(privacyMode = { mode: 'instance', default_visibility: 'instance' }) {
  const store = useCurrentUserStore()
  store.user = {
    email: 'cook@example.com',
    privacy_acknowledgement_pending: true,
    privacy_acknowledged_version: null,
    privacy_mode: privacyMode,
  } as CurrentUserResponse
  const refresh = vi.spyOn(store, 'refresh').mockResolvedValue(null)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  // The decline asks through the app's confirm dialog, which App.vue renders.
  const shell = { components: { AppPrivacyGate, ConfirmDialog }, template: '<ConfirmDialog /><AppPrivacyGate />' }
  mounted.push(mount(shell, {
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
    attachTo: document.body,
  }))
  await flushPromises()
  return { store, refresh, router }
}

const mounted: VueWrapper[] = []

const button = (label: string) =>
  [...document.body.querySelectorAll('button')].find((b) => b.textContent?.trim() === label)

describe('AppPrivacyGate', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  afterEach(() => {
    for (const wrapper of mounted.splice(0)) wrapper.unmount()
  })

  it('names the privacy mode in plain words as the administrator decision', async () => {
    getLegalPage.mockResolvedValue(statement(1))
    await mountGate({ mode: 'user_choice', default_visibility: 'household' })
    const text = document.body.textContent ?? ''
    expect(getLegalPage).toHaveBeenCalledWith('privacy', 'en-GB')
    expect(text).toContain('You decide.')
    expect(text).toContain('New recipes start as: My household.')
    expect(text).toContain('The administrator of this cookbook made this decision')
    expect(text).toContain('Statement 1')
  })

  it('acknowledges the version it showed and reads the user again', async () => {
    getLegalPage.mockResolvedValue(statement(3))
    acknowledgePrivacy.mockResolvedValue()
    const { refresh } = await mountGate()
    button('Accept and continue')!.click()
    await flushPromises()
    expect(acknowledgePrivacy).toHaveBeenCalledWith(3)
    expect(refresh).toHaveBeenCalled()
  })

  it('loads the new statement when a newer version replaced the shown one', async () => {
    getLegalPage.mockResolvedValueOnce(statement(1)).mockResolvedValueOnce(statement(2))
    acknowledgePrivacy.mockRejectedValue(stale())
    const { refresh } = await mountGate()
    button('Accept and continue')!.click()
    await flushPromises()
    expect(getLegalPage).toHaveBeenCalledTimes(2)
    expect(refresh).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Statement 2')
  })

  it('signs out after the decline is confirmed', async () => {
    getLegalPage.mockResolvedValue(statement(1))
    declinePrivacy.mockResolvedValue()
    const { store, router } = await mountGate()
    button('Decline and sign out')!.click()
    await flushPromises()
    expect(declinePrivacy).not.toHaveBeenCalled()
    const confirmation = document.body.querySelector('[role="alertdialog"]')!
    const accept = [...confirmation.querySelectorAll('button')].find(
      (b) => b.textContent?.trim() === 'Decline and sign out',
    )
    accept!.click()
    await flushPromises()
    expect(declinePrivacy).toHaveBeenCalled()
    expect(store.user).toBeNull()
    expect(router.currentRoute.value.name).toBe('login')
  })
})
