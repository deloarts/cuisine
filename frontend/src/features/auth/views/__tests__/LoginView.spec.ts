import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'

import LoginView from '@/features/auth/views/LoginView.vue'
import { i18n } from '@/core/i18n'

const passwordLogin = vi.fn<(...args: unknown[]) => unknown>()
const totpLogin = vi.fn<(...args: unknown[]) => unknown>()

vi.mock('@/features/auth/api/login', () => ({
  passwordLogin: (...args: unknown[]) => passwordLogin(...args),
  totpLogin: (...args: unknown[]) => totpLogin(...args),
  passkeyLogin: vi.fn<() => void>(),
  passkeyLoginOptions: vi.fn<() => void>(),
  enrollWithSetupToken: vi.fn<() => void>(),
  confirmWithSetupToken: vi.fn<() => void>(),
}))

const refresh = vi.fn<() => Promise<unknown>>().mockResolvedValue(null)

vi.mock('@/core/stores/currentUserStore', () => ({
  useCurrentUserStore: () => ({ refresh: () => refresh() }),
}))

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/', component: { template: '<div>home</div>' } },
      { path: '/admin/:tab?', name: 'admin', component: { template: '<div>admin</div>' } },
    ],
  })
  await router.push('/login')
  const wrapper = mount(LoginView, { global: { plugins: [router, i18n, OpenVue] } })
  return { wrapper, router }
}

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('signs in with a password and leaves the login page', async () => {
    passwordLogin.mockResolvedValue({ status: 'session' })
    const { wrapper, router } = await mountView()

    await wrapper.find('#login-email').setValue('cook@example.com')
    await wrapper.find('#login-password').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(passwordLogin).toHaveBeenCalledWith('cook@example.com', 'secret-password')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('sends the system account to the admin area', async () => {
    passwordLogin.mockResolvedValue({ status: 'session' })
    refresh.mockResolvedValueOnce({ is_systemuser: true })
    const { wrapper, router } = await mountView()
    await router.replace('/login?redirect=/recipes')

    await wrapper.find('#login-email').setValue('system')
    await wrapper.find('#login-password').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(passwordLogin).toHaveBeenCalledWith('system', 'secret-password')
    expect(router.currentRoute.value.name).toBe('admin')
  })

  it('asks for the code when two-factor authentication is on', async () => {
    passwordLogin.mockResolvedValue({
      status: 'totp_required',
      partial_token: 'partial',
      trusted_device_days: 30,
    })
    const { wrapper } = await mountView()

    await wrapper.find('#login-email').setValue('cook@example.com')
    await wrapper.find('#login-password').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('six-digit code')
    expect(wrapper.text()).toContain('Trust this device for 30 days')
  })

  it('shows the backend message for wrong credentials', async () => {
    const { AxiosError, AxiosHeaders } = await import('axios')
    const headers = new AxiosHeaders()
    passwordLogin.mockRejectedValue(
      new AxiosError('x', 'ERR', { headers }, null, {
        status: 401,
        data: { detail: 'Invalid e-mail address or password.' },
        statusText: '',
        headers,
        config: { headers },
      }),
    )
    const { wrapper } = await mountView()

    await wrapper.find('#login-email').setValue('cook@example.com')
    await wrapper.find('#login-password').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Invalid e-mail address or password.')
  })
})
