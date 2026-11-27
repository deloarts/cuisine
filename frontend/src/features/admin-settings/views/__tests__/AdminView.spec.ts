import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { AdminTab } from '@/features/admin-settings/adminTabs'
import AdminView from '@/features/admin-settings/views/AdminView.vue'

const preload = vi.fn<(tabs: AdminTab[]) => void>()

const section = (key: string, text: string) => ({
  key,
  permissions: [],
  component: { render: () => h('p', text) },
})
const tabs: AdminTab[] = [
  { value: 'host', icon: 'mdi-server-network', sections: [section('host', 'Host readings')] },
  { value: 'general', icon: 'mdi-tune-variant', sections: [section('general', 'General fields')] },
]

vi.mock('@/features/admin-settings/adminTabs', () => ({
  visibleTabs: () => tabs,
  preloadSections: (given: AdminTab[]) => preload(given),
}))

async function open(path: string, pageBar: boolean) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/admin/:tab?', name: 'admin', component: AdminView }],
  })
  await router.push(path)
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(
    { render: () => h('div', [h('div', { id: 'page-bar' }), h('main', [h(AdminView)])]) },
    {
      global: { plugins: [router, i18n, OpenVue], provide: pageBar ? { pageBar: true } : {} },
      attachTo: document.body,
    },
  )
  await flushPromises()
  return { wrapper, router }
}

describe('AdminView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('puts the tab bar into the page bar, outside the page, and the sections into the page', async () => {
    const { wrapper } = await open('/admin/general', true)
    const bar = document.getElementById('page-bar')!
    expect(bar.querySelector('[role="tablist"]')?.textContent).toContain('Host')
    expect(document.querySelector('main [role="tablist"]')).toBeNull()
    expect(document.querySelector('main')?.textContent).toContain('General fields')
    wrapper.unmount()
  })

  it('keeps the tab bar in place without a page bar', async () => {
    const { wrapper } = await open('/admin/host', false)
    expect(document.getElementById('page-bar')?.children).toHaveLength(0)
    expect(document.querySelector('main [role="tablist"]')).not.toBeNull()
    wrapper.unmount()
  })

  it('fetches the sections of every visible tab when it opens and switches tabs through the URL', async () => {
    const { wrapper, router } = await open('/admin/host', true)
    expect(preload).toHaveBeenCalledWith(tabs)
    expect(document.querySelector('main')?.textContent).toContain('Host readings')

    const general = [...document.querySelectorAll<HTMLElement>('[role="tab"]')].find((tab) =>
      tab.textContent?.includes('General'),
    )!
    general.click()
    await flushPromises()
    expect(router.currentRoute.value.params.tab).toBe('general')
    expect(document.querySelector('main')?.textContent).toContain('General fields')
    wrapper.unmount()
  })
})
