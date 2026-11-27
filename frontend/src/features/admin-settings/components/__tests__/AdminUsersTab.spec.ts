import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { UserResponse } from '@/core/types/user'
import AdminUsersTab from '@/features/admin-settings/components/AdminUsersTab.vue'

const get = vi.fn<(path: string) => Promise<unknown>>()

vi.mock('@/core/api/webRequest', () => ({
  webApi: { get: (path: string) => get(path) },
}))

function user(id: string, name: string, extra: Partial<UserResponse> = {}): UserResponse {
  return {
    id,
    full_name: name,
    nickname: null,
    show_nickname: false,
    display_name: name,
    email: '',
    is_active: true,
    is_systemuser: false,
    permissions: [],
    effective_permissions: [],
    group_ids: [],
    language: 'enGB',
    totp_enabled: false,
    totp_mandatory: false,
    created: '2026-01-01T00:00:00Z',
    last_logged_in: null,
    ...extra,
  }
}

const users = [
  user('system', 'System', { is_systemuser: true, totp_enabled: true }),
  user('anna', 'Anna Berger', { totp_enabled: true }),
]

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/admin/:tab?', component: { render: () => null } }],
  })
  await router.push('/admin/users')
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(AdminUsersTab, {
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

function row(text: string): HTMLTableRowElement {
  return [...document.body.querySelectorAll('tr')].find((tr) => tr.textContent?.includes(text))!
}

// On the narrow test screen a button at the end of the row opens its menu.
async function menuLabels(text: string): Promise<string[]> {
  row(text).querySelector<HTMLButtonElement>('button[aria-label="Row actions"]')!.click()
  await flushPromises()
  return [...document.body.querySelectorAll('[role="menuitem"]')].map((item) => item.getAttribute('aria-label') ?? '')
}

describe('AdminUsersTab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['write:users'] } as never
    get.mockImplementation((path) => Promise.resolve(path === '/users' ? users : []))
  })
  afterEach(() => {
    document.body.innerHTML = ''
    localStorage.clear()
  })

  it('offers the row actions in a menu that leaves out what does not apply', async () => {
    const wrapper = await open()
    expect(await menuLabels('Anna Berger')).toEqual([
      'Edit',
      'Reset two-factor authentication',
      'Sign out everywhere',
      'Delete',
    ])
    wrapper.unmount()
  })

  it('keeps the system user from being deleted or losing its second factor', async () => {
    const wrapper = await open()
    expect(await menuLabels('System')).toEqual(['Edit', 'Sign out everywhere'])
    wrapper.unmount()
  })

  it('opens the edit dialog on a row click and the create dialog from the section header', async () => {
    const wrapper = await open()
    row('Anna Berger').querySelector('td')!.click()
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')?.textContent).toContain('Edit user')
    wrapper.unmount()

    const again = await open()
    ;[...document.body.querySelectorAll('button')].find((b) => b.textContent?.includes('New user'))!.click()
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')?.textContent).toContain('New user')
    again.unmount()
  })
})
