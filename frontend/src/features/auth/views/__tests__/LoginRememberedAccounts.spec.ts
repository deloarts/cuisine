import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { listRememberedAccounts, rememberAccount } from '@/features/auth/utils/rememberedAccounts'
import LoginView from '@/features/auth/views/LoginView.vue'

const passwordLogin = vi.fn<(...args: unknown[]) => unknown>()

vi.mock('@/features/auth/api/login', () => ({
  passwordLogin: (...args: unknown[]) => passwordLogin(...args),
  totpLogin: vi.fn<() => void>(),
  passkeyLogin: vi.fn<() => void>(),
  passkeyLoginOptions: vi.fn<() => void>(),
  enrollWithSetupToken: vi.fn<() => void>(),
  confirmWithSetupToken: vi.fn<() => void>(),
}))

const refresh = vi.fn<() => Promise<unknown>>()

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

describe('LoginView with remembered accounts', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    localStorage.clear()
    passwordLogin.mockReset()
    refresh.mockReset()
  })

  it('remembers the account after a sign-in', async () => {
    passwordLogin.mockResolvedValue({ status: 'session' })
    refresh.mockResolvedValue({ id: 'u-anna', email: 'anna@example.com', display_name: 'Anna', is_systemuser: false, avatar_id: null })
    const { wrapper } = await mountView()
    await wrapper.get('#login-email').setValue('anna@example.com')
    await wrapper.get('#login-password').setValue('secret-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(listRememberedAccounts()).toMatchObject([{ userId: 'u-anna', login: 'anna@example.com', displayName: 'Anna' }])
  })

  it('opens on the last account and asks only for its password', async () => {
    rememberAccount({ userId: 'u-anna', login: 'anna@example.com', displayName: 'Anna' })
    passwordLogin.mockResolvedValue({ status: 'session' })
    refresh.mockResolvedValue(null)
    const { wrapper, router } = await mountView()

    expect(wrapper.get('[data-testid="login-remembered-account"]').text()).toContain('Anna')
    expect(wrapper.find('#login-email').exists()).toBe(false)
    await wrapper.get('#login-chooser-password').setValue('secret-password')
    await wrapper.get('[data-testid="login-chooser"] form').trigger('submit')
    await flushPromises()

    expect(passwordLogin).toHaveBeenCalledWith('anna@example.com', 'secret-password')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('switches between saved accounts, to the empty form and back', async () => {
    rememberAccount({ userId: 'u-ben', login: 'ben@example.com', displayName: 'Ben' })
    await new Promise((resolve) => setTimeout(resolve, 2))
    rememberAccount({ userId: 'u-anna', login: 'anna@example.com', displayName: 'Anna' })
    const { wrapper } = await mountView()

    await wrapper.get('[data-testid="login-account-u-ben"]').trigger('click')
    expect(wrapper.get('[data-testid="login-remembered-account"]').text()).toContain('Ben')

    await wrapper.get('[data-testid="login-other-account"]').trigger('click')
    expect(wrapper.find('#login-email').exists()).toBe(true)

    await wrapper.get('[data-testid="login-back-to-accounts"]').trigger('click')
    expect(wrapper.get('[data-testid="login-remembered-account"]').text()).toContain('Anna')
  })

  it('forgets the account on this device', async () => {
    rememberAccount({ userId: 'u-anna', login: 'anna@example.com', displayName: 'Anna' })
    const { wrapper } = await mountView()
    await wrapper.get('[data-testid="login-forget-account"]').trigger('click')

    expect(listRememberedAccounts()).toEqual([])
    expect(wrapper.find('#login-email').exists()).toBe(true)
    expect(wrapper.find('[data-testid="login-back-to-accounts"]').exists()).toBe(false)
  })
})
