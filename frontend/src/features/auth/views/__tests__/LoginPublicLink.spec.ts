import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Schemas } from '@/core/api/generated'
import { i18n } from '@/core/i18n'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import LoginView from '@/features/auth/views/LoginView.vue'

vi.mock('@/features/auth/api/login', () => ({
  passwordLogin: vi.fn<() => void>(),
  totpLogin: vi.fn<() => void>(),
  passkeyLogin: vi.fn<() => void>(),
  passkeyLoginOptions: vi.fn<() => void>(),
  enrollWithSetupToken: vi.fn<() => void>(),
  confirmWithSetupToken: vi.fn<() => void>(),
}))

vi.mock('@/core/stores/currentUserStore', () => ({
  useCurrentUserStore: () => ({ refresh: () => Promise.resolve(null) }),
}))

async function mountWith(allowed: boolean) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      { path: '/public/recipes', name: 'public-recipes', component: { template: '<div>public</div>' } },
    ],
  })
  await router.push('/login')
  usePublicInfoStore().info = {
    instance_name: 'Cuisine',
    allow_public_recipes: allowed,
    index_public_recipes: false,
  } as Schemas['PublicInfoResponse']
  const wrapper = mount(LoginView, { global: { plugins: [router, i18n, OpenVue] } })
  await flushPromises()
  return wrapper
}

describe('LoginView public recipes link', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('links to the public recipes while they are allowed', async () => {
    const wrapper = await mountWith(true)
    const link = wrapper.find('[data-testid="login-public-recipes"]')
    expect(link.text()).toBe('Browse public recipes')
    expect(link.attributes('href')).toBe('/public/recipes')
  })

  it('shows no link while public recipes are not allowed', async () => {
    const wrapper = await mountWith(false)
    expect(wrapper.find('[data-testid="login-public-recipes"]').exists()).toBe(false)
  })
})
