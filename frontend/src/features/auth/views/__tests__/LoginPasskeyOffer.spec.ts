import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { listRememberedAccounts, rememberAccount } from '@/features/auth/utils/rememberedAccounts'
import LoginView from '@/features/auth/views/LoginView.vue'

const passwordLogin = vi.fn<(...args: unknown[]) => unknown>()
const setUp = vi.fn<(...args: unknown[]) => Promise<unknown>>()
const refresh = vi.fn<() => Promise<unknown>>()

vi.mock('@/features/auth/api/login', () => ({
  passwordLogin: (...args: unknown[]) => passwordLogin(...args),
  totpLogin: vi.fn<() => void>(),
  passkeyLogin: vi.fn<() => void>(),
  passkeyLoginOptions: vi.fn<() => void>(),
  enrollWithSetupToken: vi.fn<() => void>(),
  confirmWithSetupToken: vi.fn<() => void>(),
}))

vi.mock('@/features/auth/utils/webauthn', () => ({
  getPasskey: vi.fn<() => void>(),
  passkeyPromptDismissed: (err: unknown) => err instanceof DOMException && err.name === 'NotAllowedError',
  passkeysSupported: () => true,
  platformAuthenticatorAvailable: () => Promise.resolve(true),
  platformAuthenticatorKind: () => 'generic',
}))

vi.mock('@/features/auth/utils/passkeySetup', () => ({
  setUpPasskeyOnThisDevice: (...args: unknown[]) => setUp(...args),
}))

vi.mock('@/core/stores/currentUserStore', () => ({
  useCurrentUserStore: () => ({ refresh: () => refresh() }),
}))

const anna = { id: 'u-anna', email: 'anna@example.com', display_name: 'Anna', is_systemuser: false, avatar_id: null }

async function signInWithPassword() {
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
  // A remembered account with a passkey opens on its passkey button; the
  // password goes through the plain form.
  if (wrapper.find('[data-testid="login-chooser-sign-in"]').exists()) {
    await wrapper.get('[data-testid="login-other-account"]').trigger('click')
  }
  if (wrapper.find('#login-email').exists()) await wrapper.get('#login-email').setValue(anna.email)
  const field = wrapper.find('#login-password').exists() ? '#login-password' : '#login-chooser-password'
  await wrapper.get(field).setValue('secret-password')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  return { wrapper, router }
}

describe('LoginView passkey offer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    localStorage.clear()
    passwordLogin.mockReset().mockResolvedValue({ status: 'session' })
    refresh.mockReset().mockResolvedValue(anna)
    setUp.mockReset()
  })

  it('offers a passkey after a password sign-in and sets it up', async () => {
    setUp.mockResolvedValue({ id: 'pk-1' })
    const { wrapper, router } = await signInWithPassword()
    expect(wrapper.find('[data-testid="login-passkey-offer"]').exists()).toBe(true)
    expect(router.currentRoute.value.path).toBe('/login')

    await wrapper.get('[data-testid="login-passkey-accept"]').trigger('click')
    await flushPromises()
    expect(setUp).toHaveBeenCalledWith('u-anna', 'This device')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('stays on the offer when the prompt is dismissed', async () => {
    setUp.mockRejectedValue(new DOMException('dismissed', 'NotAllowedError'))
    const { wrapper, router } = await signInWithPassword()
    await wrapper.get('[data-testid="login-passkey-accept"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('The passkey was not set up.')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('remembers "Not now" and does not ask again', async () => {
    const first = await signInWithPassword()
    await first.wrapper.get('[data-testid="login-passkey-decline"]').trigger('click')
    await flushPromises()
    expect(first.router.currentRoute.value.path).toBe('/')
    expect(listRememberedAccounts()[0]).toMatchObject({ passkeyDeclined: true })

    const again = await signInWithPassword()
    expect(again.wrapper.find('[data-testid="login-passkey-offer"]').exists()).toBe(false)
    expect(again.router.currentRoute.value.path).toBe('/')
  })

  it('does not offer one to an account with a passkey on this device', async () => {
    rememberAccount({ userId: 'u-anna', login: anna.email, displayName: 'Anna', credentialId: 'cred-1' })
    const { wrapper, router } = await signInWithPassword()
    expect(wrapper.find('[data-testid="login-passkey-offer"]').exists()).toBe(false)
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('never offers one to the system account', async () => {
    refresh.mockResolvedValue({ ...anna, id: 'u-sys', is_systemuser: true })
    const { wrapper, router } = await signInWithPassword()
    expect(wrapper.find('[data-testid="login-passkey-offer"]').exists()).toBe(false)
    expect(router.currentRoute.value.name).toBe('admin')
  })
})
