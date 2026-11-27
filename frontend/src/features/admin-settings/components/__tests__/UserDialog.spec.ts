import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmDialog from 'openvue/confirmdialog'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { i18n } from '@/core/i18n'
import type { UserResponse } from '@/core/types/user'
import UserDialog from '@/features/admin-settings/components/UserDialog.vue'

const api = vi.hoisted(() => ({
  update: vi.fn(),
  create: vi.fn(),
  uploadAvatar: vi.fn(),
  removeAvatar: vi.fn(),
  resetTotp: vi.fn(),
}))

vi.mock('@/features/admin-settings/api/users', () => ({ usersApi: api }))

function user(extra: Partial<UserResponse> = {}): UserResponse {
  return {
    id: 'anna',
    full_name: 'Anna Berger',
    nickname: null,
    show_nickname: false,
    display_name: 'Anna Berger',
    email: 'anna@example.com',
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

async function open(edited: UserResponse | null) {
  i18n.global.locale.value = 'enGB'
  const saved = vi.fn()
  const wrapper = mount(
    defineComponent({
      setup() {
        const visible = ref(false)
        return () => [
          h(ConfirmDialog),
          h(UserDialog, {
            visible: visible.value,
            'onUpdate:visible': (v: boolean) => (visible.value = v),
            user: edited,
            groups: [],
            onSaved: saved,
          }),
          h('button', { id: 'open', onClick: () => (visible.value = true) }),
        ]
      },
    }),
    {
      global: { plugins: [i18n, OpenVue, ToastService, ConfirmationService] },
      attachTo: document.body,
    },
  )
  await wrapper.find('#open').trigger('click')
  await flushPromises()
  return { wrapper, saved }
}

const byTestId = (id: string) => document.body.querySelector<HTMLElement>(`[data-testid="${id}"]`)

describe('UserDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    Object.values(api).forEach((fn) => fn.mockReset())
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('saves the nickname and the choice to show it with the other fields', async () => {
    api.update.mockResolvedValue(user())
    const { wrapper } = await open(user())
    const nickname = document.body.querySelector<HTMLInputElement>('#user-nickname')!
    nickname.value = 'Bubu'
    nickname.dispatchEvent(new Event('input'))
    document.body.querySelector<HTMLInputElement>('#user-show-nickname')!.click()
    await flushPromises()
    document.body.querySelector<HTMLFormElement>('#user-form')!.requestSubmit()
    await flushPromises()

    expect(api.update).toHaveBeenCalledWith('anna', expect.objectContaining({ nickname: 'Bubu', show_nickname: true }))
    wrapper.unmount()
  })

  it('uploads and removes the picture at once, without saving the form', async () => {
    api.uploadAvatar.mockResolvedValue(user({ avatar_id: 'pic' }))
    api.removeAvatar.mockResolvedValue(user())
    const { wrapper, saved } = await open(user())
    expect(byTestId('user-avatar-remove')).toBeNull()

    const input = byTestId('user-avatar-input') as HTMLInputElement
    const file = new File(['x'], 'anna.png', { type: 'image/png' })
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    input.dispatchEvent(new Event('change'))
    await flushPromises()
    expect(api.uploadAvatar).toHaveBeenCalledWith('anna', file)
    expect(saved).toHaveBeenCalledTimes(1)

    byTestId('user-avatar-remove')!.click()
    await flushPromises()
    expect(api.removeAvatar).toHaveBeenCalledWith('anna')
    expect(byTestId('user-avatar-remove')).toBeNull()
    expect(api.update).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('resets two-factor authentication after confirmation', async () => {
    api.resetTotp.mockResolvedValue(user())
    const { wrapper } = await open(user({ totp_enabled: true }))
    byTestId('user-reset-totp')!.click()
    await flushPromises()
    expect(api.resetTotp).not.toHaveBeenCalled()

    const yes = [...document.body.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent?.trim() === 'Yes')
    yes!.click()
    await flushPromises()
    expect(api.resetTotp).toHaveBeenCalledWith('anna')
    expect(byTestId('user-reset-totp')).toBeNull()
    expect(byTestId('user-two-factor')!.textContent).toContain('Not set up.')
    wrapper.unmount()
  })

  it('offers no reset for the system user and no picture for a new account', async () => {
    const first = await open(user({ is_systemuser: true, totp_enabled: true }))
    expect(byTestId('user-reset-totp')).toBeNull()
    expect(byTestId('user-two-factor')!.textContent).toContain('admin reset-totp system')
    first.wrapper.unmount()
    document.body.innerHTML = ''

    const second = await open(null)
    expect(byTestId('user-avatar-upload')).toBeNull()
    expect(byTestId('user-two-factor')).toBeNull()
    second.wrapper.unmount()
  })
})
