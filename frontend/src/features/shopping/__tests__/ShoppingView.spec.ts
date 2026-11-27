import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import ShoppingView from '@/features/shopping/views/ShoppingView.vue'
import { resetHousehold } from '@/shared/household/useHousehold'

const webGet = vi.fn<(path: string) => Promise<unknown>>()

vi.mock('@/core/api/webRequest', () => ({ webApi: { get: (path: string) => webGet(path) } }))

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/shopping', component: ShoppingView },
      { path: '/shopping/:id', name: 'shopping-list', component: { render: () => null } },
    ],
  })
  await router.push('/shopping')
  i18n.global.locale.value = 'enGB'
  return mount(ShoppingView, { global: { plugins: [router, i18n, OpenVue, ToastService] } })
}

describe('ShoppingView loading', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetHousehold()
  })
  afterEach(() => vi.clearAllMocks())

  it('shows skeleton cards instead of the empty state until the lists arrive', async () => {
    let answer!: (value: unknown) => void
    webGet.mockImplementation((path) => {
      if (path === '/shopping-lists') return new Promise((resolve) => (answer = resolve))
      if (path === '/households/mine') return Promise.resolve({ household: null })
      return Promise.resolve([])
    })
    const wrapper = await open()
    await flushPromises()

    expect(wrapper.get('[data-testid="shopping-skeleton"]').attributes('role')).toBe('status')
    expect(wrapper.text()).not.toContain('No shopping lists yet.')

    answer([])
    await flushPromises()
    expect(wrapper.find('[data-testid="shopping-skeleton"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('No shopping lists yet.')
  })
})
