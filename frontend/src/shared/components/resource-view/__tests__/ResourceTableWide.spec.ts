import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { describe, expect, it, vi } from 'vitest'
import { h, ref, type Component } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import ResourceTable from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { i18n } from '@/core/i18n'

vi.mock('@/shared/composables/useWideScreen', () => ({ useWideScreen: () => ref(true) }))

describe('ResourceTable on a wide screen', () => {
  it('offers the row actions through a focusable button, also from the keyboard', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
    await router.push('/')
    i18n.global.locale.value = 'enGB'
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('wideMenu', {})
          return () =>
            h(ResourceTable as Component, {
              state: table,
              value: [
                { id: '1', name: 'Apfel' },
                { id: '2', name: 'Birne' },
              ],
              columns: [{ field: 'name', header: 'Name' }],
              fill: false,
              menu: (row: { id: string }) => (row.id === '1' ? [{ label: 'Delete' }] : []),
            })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] }, attachTo: document.body },
    )
    await flushPromises()

    const buttons = wrapper.findAll('button[aria-label="Row actions"]')
    expect(buttons).toHaveLength(2)
    expect(buttons[0]!.attributes('aria-haspopup')).toBe('menu')

    // A keyboard click has no pointer position (detail 0) and still opens the menu.
    buttons[0]!.element.dispatchEvent(new MouseEvent('click', { bubbles: true, detail: 0 }))
    await flushPromises()
    expect(document.body.textContent).toContain('Delete')
    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
