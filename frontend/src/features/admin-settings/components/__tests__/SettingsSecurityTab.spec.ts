import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Schemas } from '@/core/api/generated'
import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import SettingsSecurityTab from '@/features/admin-settings/components/SettingsSecurityTab.vue'

type Security = Schemas['SecuritySettingsSchema']

const get = vi.fn<(path: string) => Promise<Security>>()
const put = vi.fn<(path: string, options: { body: Security }) => Promise<Security>>()

vi.mock('@/core/api/webRequest', () => ({
  webApi: {
    get: (path: string) => get(path),
    put: (path: string, options: { body: Security }) => put(path, options),
  },
}))

const stored: Security = {
  enforce_totp: true,
  min_password_length: 12,
  session_timeout_minutes: 60,
  session_max_lifetime_days: 30,
  totp_trusted_device_days: 14,
  max_login_attempts: 5,
  lockout_duration_minutes: 15,
  enable_api_key_auth: false,
  token_max_lifetime_days: 90,
}

function input(id: string): HTMLInputElement {
  return document.body.querySelector<HTMLInputElement>(`#${id}`)!
}

function mountTab() {
  i18n.global.locale.value = 'enGB'
  return mount(SettingsSecurityTab, {
    global: { plugins: [i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
}

describe('SettingsSecurityTab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['write:settings'] } as never
  })

  it('shows every field at once, empty and disabled, and fills them when the settings arrive', async () => {
    let answer: (value: Security) => void = () => undefined
    get.mockReturnValue(new Promise((resolve) => (answer = resolve)))
    const wrapper = mountTab()
    await flushPromises()

    expect(document.body.textContent).toContain('Minimum password length')
    expect(input('sec-min_password_length').value).toBe('')
    expect(input('sec-min_password_length').disabled).toBe(true)
    expect(input('sec-enforce').checked).toBe(false)
    expect(input('sec-enforce').disabled).toBe(true)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    answer(stored)
    await flushPromises()

    expect(input('sec-min_password_length').value).toBe('12')
    expect(input('sec-min_password_length').disabled).toBe(false)
    expect(input('sec-enforce').checked).toBe(true)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })

  it('saves the loaded values', async () => {
    get.mockResolvedValue(stored)
    put.mockResolvedValue(stored)
    const wrapper = mountTab()
    await flushPromises()

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(put).toHaveBeenCalledWith('/settings/security', { body: stored })
    wrapper.unmount()
  })
})
