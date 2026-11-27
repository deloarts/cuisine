import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick, ref, type Component } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import ResourceTable from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable, type ResourceTable as TableState } from '@/shared/composables/useResourceTable'
import { i18n } from '@/core/i18n'

const spec = { q: 'string', kind: 'string' } as const
const rows = Array.from({ length: 30 }, (_, i) => ({ id: String(i), name: `Item ${i}` }))

async function mountTable(path = '/things') {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/things', component: { render: () => null } }],
  })
  await router.push(path)
  i18n.global.locale.value = 'enGB'
  const reload = vi.fn<() => void>()
  let table!: TableState<typeof spec>
  const wrapper = mount(
    {
      setup() {
        table = useResourceTable('things', spec, reload, 0)
        return () =>
          h(ResourceTable as Component, {
            state: table,
            value: rows.filter((r) => matchesText(table.filters.q, r.name)),
            columns: [{ field: 'name', header: 'Name', filter: true }],
            fill: false,
          })
      },
    },
    { global: { plugins: [router, i18n, OpenVue] } },
  )
  await flushPromises()
  return { wrapper, router, reload, table: () => table }
}

describe('ResourceTable', () => {
  afterEach(() => localStorage.clear())

  it('starts from the URL and writes filter changes back to it', async () => {
    const { router, table, reload, wrapper } = await mountTable('/things?q=item%202&other=1')
    expect(table().filters.q).toBe('item 2')
    expect(table().active.value).toBe(1)

    table().first.value = 25
    table().filters.kind = 'mass'
    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 5))
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ q: 'item 2', kind: 'mass', other: '1' })
    expect(table().first.value).toBe(0)
    expect(reload).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('clears every filter from the controls bar', async () => {
    const { router, wrapper } = await mountTable('/things?q=x&kind=mass')
    const clear = wrapper.findAll('button').find((b) => b.text().includes('Clear filters (2)'))
    expect(clear).toBeDefined()
    await clear!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
    wrapper.unmount()
  })

  it('remembers the rows per page per table and goes back to the first page on a resize', async () => {
    const { table, reload, wrapper } = await mountTable()
    table().onPage({ first: 25, rows: 25 })
    expect(table().first.value).toBe(25)
    table().onPage({ first: 25, rows: 50 })
    expect(table().first.value).toBe(0)
    expect(table().rows.value).toBe(50)
    expect(reload).toHaveBeenCalledTimes(2)
    await nextTick()
    expect(localStorage.getItem('tableRows:things')).toBe('50')
    wrapper.unmount()
  })

  it('numbers the rows across pages and sorts by the first column by default', async () => {
    const shuffled = [
      { id: 'b', name: 'Banane' },
      { id: 'c', name: 'Curry' },
      { id: 'a', name: 'Apfel' },
    ]
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
    await router.push('/')
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('sorted', {})
          return () => h(ResourceTable as Component, { state: table, value: shuffled, columns: [{ field: 'name', header: 'Name' }], fill: false })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] } },
    )
    await flushPromises()
    const cells = wrapper.findAll('tbody tr').map((row) => row.findAll('td').map((td) => td.text()))
    expect(cells).toEqual([
      ['1', 'Apfel'],
      ['2', 'Banane'],
      ['3', 'Curry'],
    ])
    wrapper.unmount()
  })

  it('emits a clicked row and offers the row menu', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
    await router.push('/')
    const onRowClick = vi.fn<(row: { id: string; name: string }) => void>()
    const command = vi.fn<() => void>()
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('clicks', {})
          return () =>
            h(ResourceTable as Component, {
              state: table,
              value: [{ id: '1', name: 'Apfel' }],
              columns: [{ field: 'name', header: 'Name' }],
              fill: false,
              clickable: true,
              menu: () => [{ label: 'Delete', command }],
              onRowClick,
            })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] }, attachTo: document.body },
    )
    await flushPromises()
    await wrapper.find('tbody tr td:nth-child(2)').trigger('click')
    expect(onRowClick).toHaveBeenCalledWith({ id: '1', name: 'Apfel' })

    // The phone's trailing menu button opens the menu without clicking the row.
    await wrapper.find('button[aria-label="Row actions"]').trigger('click')
    await flushPromises()
    expect(onRowClick).toHaveBeenCalledTimes(1)
    expect(document.body.textContent).toContain('Delete')
    wrapper.unmount()
  })

  it('moves a row with the phone buttons of a reorderable table', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
    await router.push('/')
    const onReorder = vi.fn<(rows: { id: string; name: string }[]) => void>()
    const ordered = [
      { id: 'a', name: 'Obst' },
      { id: 'b', name: 'Gemüse' },
      { id: 'c', name: 'Milch' },
    ]
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('moves', {})
          return () =>
            h(ResourceTable as Component, {
              state: table,
              value: ordered,
              columns: [{ field: 'name', header: 'Name' }],
              fill: false,
              reorderable: true,
              onReorder,
            })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] } },
    )
    await flushPromises()
    // The rows keep their given order instead of sorting by name.
    expect(wrapper.findAll('tbody tr').map((row) => row.findAll('td')[1]!.text())).toEqual(['Obst', 'Gemüse', 'Milch'])
    const up = wrapper.findAll('button[aria-label="Move up"]')
    const down = wrapper.findAll('button[aria-label="Move down"]')
    expect(up[0]!.attributes('disabled')).toBeDefined()
    expect(down[2]!.attributes('disabled')).toBeDefined()

    await down[0]!.trigger('click')
    expect(onReorder).toHaveBeenCalledWith([ordered[1], ordered[0], ordered[2]])
    wrapper.unmount()
  })

  it('keeps pinned rows above the sorted ones with a pin instead of a number', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] })
    await router.push('/')
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('pins', {})
          return () =>
            h(ResourceTable as Component, {
              state: table,
              value: [
                { id: 'b', name: 'Banane' },
                { id: 'a', name: 'Apfel' },
              ],
              pinned: [{ id: 'z', name: 'Zitrone' }],
              columns: [{ field: 'name', header: 'Name' }],
              fill: false,
            })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] } },
    )
    await flushPromises()
    const names = wrapper.findAll('tbody tr').map((row) => row.findAll('td')[1]!.text())
    expect(names).toEqual(['Zitrone', 'Apfel', 'Banane'])
    expect(wrapper.find('tbody tr [aria-label="Waiting to be checked"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('shows only the lead column on a phone', async () => {
    const { wrapper } = await mountTable()
    expect(wrapper.text()).toContain('Item 0')
    expect(wrapper.findAll('tbody tr')).toHaveLength(25)
    wrapper.unmount()
  })
  it('shows skeleton rows while it loads without rows, and keeps rows it already shows', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/things', component: { render: () => null } }],
    })
    await router.push('/things')
    i18n.global.locale.value = 'enGB'
    const shown = ref<typeof rows>([])
    const loading = ref(true)
    const wrapper = mount(
      {
        setup() {
          const table = useResourceTable('loading-things', spec, undefined, 0)
          return () =>
            h(ResourceTable as Component, {
              state: table,
              value: shown.value,
              loading: loading.value,
              columns: [{ field: 'name', header: 'Name' }],
              emptyMessage: 'Nothing found',
              fill: false,
            })
        },
      },
      { global: { plugins: [router, i18n, OpenVue] } },
    )
    await flushPromises()
    expect(wrapper.find('[data-testid="table-skeleton"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Nothing found')

    shown.value = rows.slice(0, 3)
    await flushPromises()
    expect(wrapper.find('[data-testid="table-skeleton"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Item 2')

    shown.value = []
    loading.value = false
    await flushPromises()
    expect(wrapper.find('[data-testid="table-skeleton"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Nothing found')
    wrapper.unmount()
  })
})

describe('matchesText', () => {
  it('ignores case and diacritics and needs every word', () => {
    expect(matchesText('erdapfel', 'Erdäpfel')).toBe(true)
    expect(matchesText('rote zwiebel', 'Zwiebel, rot', 'Rote Zwiebel')).toBe(true)
    expect(matchesText('lauch', 'Zwiebel')).toBe(false)
    expect(matchesText('', 'anything')).toBe(true)
  })
})
