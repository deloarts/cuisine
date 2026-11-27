import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { CurrentUserResponse } from '@/core/types/user'
import TotpSection from '@/features/account/components/TotpSection.vue'

const enrollTotp = vi.fn<(password: string) => Promise<unknown>>()

vi.mock('@/features/account/api/security', () => ({
  enrollTotp: (password: string) => enrollTotp(password),
  confirmTotp: vi.fn<() => Promise<void>>(),
  disableTotp: vi.fn<() => Promise<void>>(),
}))
vi.mock('@/features/auth/components/TotpQrCode.vue', () => ({ default: { template: '<div />' } }))

describe('TotpSection enrolment', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    useCurrentUserStore().user = { id: 'me', totp_enabled: false, is_systemuser: false } as CurrentUserResponse
    enrollTotp.mockResolvedValue({ secret: 'ABC', provisioning_uri: 'otpauth://totp/x' })
  })

  it('asks for the current password before it starts enrolling', async () => {
    const wrapper = mount(TotpSection, { global: { plugins: [i18n, OpenVue, ToastService] } })
    await wrapper.find('button').trigger('click')
    expect(enrollTotp).not.toHaveBeenCalled()

    await wrapper.find('#totp-enrol-password').setValue('secret-pw')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(enrollTotp).toHaveBeenCalledWith('secret-pw')
    expect(wrapper.text()).toContain('ABC')
  })
})
