import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmDialog from 'openvue/confirmdialog'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import Tooltip from 'openvue/tooltip'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import ResourceTable from '@/shared/components/resource-view/ResourceTable.vue'
import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import routes from '@/features/resources/routes'
import ResourcesView from '@/features/resources/views/ResourcesView.vue'

const get = vi.fn<(path: string) => Promise<unknown>>()
const put = vi.fn<(path: string, options: unknown) => Promise<unknown>>()
const post = vi.fn<(path: string, options: unknown) => Promise<unknown>>()
const remove = vi.fn<(path: string, options: unknown) => Promise<unknown>>()

vi.mock('@/core/api/webRequest', () => ({
  webApi: {
    get: (path: string) => get(path),
    put: (path: string, options: unknown) => put(path, options),
    post: (path: string, options: unknown) => post(path, options),
    delete: (path: string, options: unknown) => remove(path, options),
  },
}))

const tags = [
  { id: 't1', seeded: false, kind: 'occasion', color: null, name: 'Birthday', translations: { 'en-GB': { name: 'Birthday' } } },
  { id: 't2', seeded: false, kind: 'meal', color: null, name: 'Supper', translations: { 'en-GB': { name: 'Supper' } } },
  { id: 't3', seeded: false, kind: 'cuisine', color: null, name: 'Austrian', translations: { 'en-GB': { name: 'Austrian' } } },
]
const units = [
  {
    id: 'u1',
    seeded: true,
    code: 'g',
    kind: 'mass',
    to_base: 1,
    sort_order: 10,
    name: 'gram',
    plural_name: 'grams',
    abbreviation: 'g',
    translations: {},
  },
]
const categories = [
  { id: 'c1', seeded: false, sort_order: 10, name: 'Vegetables', translations: { 'en-GB': { name: 'Vegetables' } } },
  { id: 'c2', seeded: false, sort_order: 20, name: 'Dairy', translations: { 'en-GB': { name: 'Dairy' } } },
  { id: 'c3', seeded: false, sort_order: 30, name: 'Bakery', translations: { 'en-GB': { name: 'Bakery' } } },
]
const families = [{ id: 'f1', seeded: false, name: 'Tomatoes', translations: { 'de-AT': { name: 'Paradeiser' } } }]
const equipment = [
  {
    id: 'e1',
    seeded: true,
    kind: 'cookware',
    basic: true,
    status: 'active',
    icon: null,
    name: 'Pot',
    translations: { 'en-GB': { name: 'Pot' } },
    aliases: { 'en-GB': ['Saucepan'] },
  },
]

const usage = {
  tags: [
    { id: 't1', usage_count: 0 },
    { id: 't2', usage_count: 5 },
    { id: 't3', usage_count: 2 },
  ],
  units: [{ id: 'u1', usage_count: 7 }],
  categories: [
    { id: 'c1', usage_count: 3 },
    { id: 'c2', usage_count: 0 },
    { id: 'c3', usage_count: 1 },
  ],
  families: [{ id: 'f1', usage_count: 4 }],
  equipment: [{ id: 'e1', usage_count: 2 }],
}

const responses: Record<string, unknown> = {
  '/resources/usage': usage,
  '/tags': tags,
  '/units': units,
  '/ingredient-categories': categories,
  '/ingredient-families': families,
  '/equipment': equipment,
}

const originalMatchMedia = window.matchMedia

function wideScreen() {
  vi.stubGlobal(
    'matchMedia',
    vi.fn<(query: string) => unknown>().mockImplementation((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn<() => void>(),
      removeListener: vi.fn<() => void>(),
      addEventListener: vi.fn<() => void>(),
      removeEventListener: vi.fn<() => void>(),
      dispatchEvent: vi.fn<() => void>(),
    })),
  )
}

async function open(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  i18n.global.locale.value = 'enGB'
  // The app shell hosts the confirmation dialog the delete actions ask through.
  const host = defineComponent({ render: () => [h(ConfirmDialog), h(ResourcesView)] })
  const wrapper = mount(host, {
    global: {
      plugins: [router, i18n, OpenVue, ToastService, ConfirmationService],
      directives: { tooltip: Tooltip },
    },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

function button(label: string): HTMLButtonElement | undefined {
  return [...document.body.querySelectorAll<HTMLButtonElement>('button')].find(
    (b) => b.textContent?.trim() === label || b.getAttribute('aria-label') === label,
  )
}

function dialogTitle(): string {
  const id = document.body.querySelector('[role="dialog"]')?.getAttribute('aria-labelledby')
  return (id && document.getElementById(id)?.textContent) || ''
}

async function rowMenu(name: string): Promise<HTMLElement> {
  row(name).dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }))
  await flushPromises()
  return document.body.querySelector<HTMLElement>('[role="menubar"]')!
}

function menuItem(menu: HTMLElement, label: string): HTMLElement | null {
  return menu.querySelector<HTMLElement>(`[role="menuitem"][aria-label="${label}"]`)
}

function dialogText(): string {
  return [...document.body.querySelectorAll('[role="dialog"], [role="alertdialog"]')].map((d) => d.textContent).join(' ')
}

function row(name: string): HTMLTableRowElement {
  return [...document.body.querySelectorAll<HTMLTableRowElement>('tbody tr')].find((tr) =>
    tr.textContent?.includes(name),
  )!
}

function rowNames(): string[] {
  return [...document.body.querySelectorAll<HTMLTableRowElement>('tbody tr')].map((tr) => tr.textContent ?? '')
}

describe('ResourcesView', () => {
  let mounted: VueWrapper | null = null

  beforeEach(() => {
    wideScreen()
    setActivePinia(createPinia())
    useCurrentUserStore().user = {
      id: 'me',
      is_systemuser: false,
      effective_permissions: ['read:resources', 'write:resources'],
    } as never
    get.mockImplementation((path) => Promise.resolve(responses[path] ?? []))
    put.mockResolvedValue({})
    post.mockResolvedValue({})
    remove.mockResolvedValue(undefined)
  })

  afterEach(() => {
    mounted?.unmount()
    mounted = null
    vi.stubGlobal('matchMedia', originalMatchMedia)
    localStorage.clear()
    document.body.innerHTML = ''
  })

  it.each([
    ['tags', 'New tag'],
    ['units', 'New unit'],
    ['categories', 'New category'],
    ['families', 'New family'],
    ['equipment', 'New equipment'],
  ])('creates an item of the %s tab from the page header', async (tab, label) => {
    const { wrapper } = await open(`/resources/${tab}`)
    mounted = wrapper
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    button(label)!.click()
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()
    expect(dialogTitle()).toBe(label)
  })

  it('keeps the tab list inside the table card and the active tab in the URL', async () => {
    const { wrapper, router } = await open('/resources/tags')
    mounted = wrapper
    const tab = [...document.body.querySelectorAll<HTMLElement>('[role="tab"]')].find(
      (el) => el.textContent?.trim() === 'Units',
    )!
    expect(tab.closest('table')).toBeNull()
    tab.click()
    await flushPromises()
    expect(router.currentRoute.value.params.tab).toBe('units')
    expect(button('New unit')).toBeDefined()
  })

  it('offers no create button, row menu or row click without the write right', async () => {
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['read:resources'] } as never
    const { wrapper } = await open('/resources/tags')
    mounted = wrapper
    expect(button('New tag')).toBeUndefined()
    row('Supper').querySelector('td')!.click()
    row('Supper').dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }))
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(document.body.querySelector('[role="menubar"]')).toBeNull()
  })

  it('sorts tags by name and numbers the rows', async () => {
    const { wrapper } = await open('/resources/tags')
    mounted = wrapper
    const names = rowNames()
    expect(names[0]).toMatch(/^1\s*Austrian/)
    expect(names[1]).toMatch(/^2\s*Birthday/)
    expect(names[2]).toMatch(/^3\s*Supper/)
  })

  it('opens the edit dialog when a row is clicked', async () => {
    const { wrapper } = await open('/resources/tags')
    mounted = wrapper
    row('Supper').querySelectorAll('td')[1]!.click()
    await flushPromises()
    expect(dialogTitle()).toBe('Edit tag')
    expect(document.body.querySelector<HTMLInputElement>('#tag-en-GB-name')?.value).toBe('Supper')
  })

  it('deletes a family through the row menu after confirming', async () => {
    const { wrapper } = await open('/resources/families')
    mounted = wrapper
    const menu = await rowMenu('Tomatoes')
    expect(menuItem(menu, 'Edit')).not.toBeNull()
    menuItem(menu, 'Delete')!.querySelector('a')!.click()
    await flushPromises()
    expect(dialogText()).toContain('Delete the family "Tomatoes"?')
    button('Delete')!.click()
    await flushPromises()
    expect(remove).toHaveBeenCalledWith('/ingredient-families/{family_id}', { path: { family_id: 'f1' } })
  })

  it('shows families without the column of other languages', async () => {
    const { wrapper } = await open('/resources/families')
    mounted = wrapper
    expect(document.body.querySelector('thead')?.textContent).not.toContain('Other languages')
    expect(row('Tomatoes').textContent).not.toContain('Paradeiser')
  })

  it('hides delete in the menu of a seeded equipment item but offers the merge', async () => {
    const { wrapper } = await open('/resources/equipment')
    mounted = wrapper
    const menu = await rowMenu('Pot')
    expect(menuItem(menu, 'Merge into…')).not.toBeNull()
    expect(menuItem(menu, 'Edit')).not.toBeNull()
    expect(menuItem(menu, 'Delete')).toBeNull()
  })

  it('saves a dragged category order as 10, 20, 30 and reloads once', async () => {
    const { wrapper } = await open('/resources/categories')
    mounted = wrapper
    // Each row reads its number, the name and the usage count.
    expect(rowNames().map((r) => r.replace(/^\d+\s*/, '').replace(/\d+$/, ''))).toEqual(['Vegetables', 'Dairy', 'Bakery'])
    get.mockClear()

    const [vegetables, dairy, bakery] = categories
    wrapper.findComponent(ResourceTable).vm.$emit('reorder', [bakery, vegetables, dairy])
    await flushPromises()

    expect(put).toHaveBeenCalledTimes(3)
    expect(put).toHaveBeenCalledWith('/ingredient-categories/{category_id}', {
      path: { category_id: 'c3' },
      body: { sort_order: 10, translations: { 'en-GB': { name: 'Bakery' } } },
    })
    expect(put).toHaveBeenCalledWith('/ingredient-categories/{category_id}', {
      path: { category_id: 'c1' },
      body: { sort_order: 20, translations: { 'en-GB': { name: 'Vegetables' } } },
    })
    expect(put).toHaveBeenCalledWith('/ingredient-categories/{category_id}', {
      path: { category_id: 'c2' },
      body: { sort_order: 30, translations: { 'en-GB': { name: 'Dairy' } } },
    })
    expect(get.mock.calls.filter(([path]) => path === '/ingredient-categories')).toHaveLength(1)
  })

  it('writes only the categories whose position changed', async () => {
    const { wrapper } = await open('/resources/categories')
    mounted = wrapper
    const [vegetables, dairy, bakery] = categories
    wrapper.findComponent(ResourceTable).vm.$emit('reorder', [vegetables, bakery, dairy])
    await flushPromises()
    expect(put).toHaveBeenCalledTimes(2)
    expect(put.mock.calls.map(([, options]) => (options as { path: { category_id: string } }).path.category_id)).toEqual([
      'c3',
      'c2',
    ])
  })

  it('does not offer reordering while the categories are filtered', async () => {
    const { wrapper } = await open('/resources/categories?q=dai')
    mounted = wrapper
    expect((wrapper.findComponent(ResourceTable).props() as unknown as { reorderable: boolean }).reorderable).toBe(false)
    expect(document.body.textContent).toContain('Clear the filter to change the order.')
  })
  it.each([
    ['tags', 'Supper', '5'],
    ['units', 'gram', '7'],
    ['categories', 'Vegetables', '3'],
    ['families', 'Tomatoes', '4'],
    ['equipment', 'Pot', '2'],
  ])('shows how often each item of the %s tab is used', async (tab, name, count) => {
    const { wrapper } = await open(`/resources/${tab}`)
    mounted = wrapper
    expect(document.body.querySelector('thead')?.textContent).toContain('Used')
    const cells = [...row(name).querySelectorAll('td')].map((td) => td.textContent?.trim())
    expect(cells).toContain(count)
  })

  it('filters the tags by a usage range kept in the URL', async () => {
    const { wrapper } = await open('/resources/tags?usageMin=1&usageMax=3')
    mounted = wrapper
    expect(rowNames().map((r) => r.replace(/^\d+\s*/, ''))).toEqual([expect.stringMatching(/^Austrian/)])
  })

  it('sorts the tags by usage when the column header is clicked', async () => {
    const { wrapper } = await open('/resources/tags')
    mounted = wrapper
    const header = [...document.body.querySelectorAll<HTMLElement>('thead th')].find((th) =>
      th.textContent?.includes('Used'),
    )!
    header.click()
    await flushPromises()
    expect(rowNames().map((r) => r.replace(/^\d+\s*/, '').slice(0, 5))).toEqual(['Birth', 'Austr', 'Suppe'])
  })

  it('loads the usage counts again after a change', async () => {
    const { wrapper } = await open('/resources/families')
    mounted = wrapper
    get.mockClear()
    const menu = await rowMenu('Tomatoes')
    menuItem(menu, 'Delete')!.querySelector('a')!.click()
    await flushPromises()
    button('Delete')!.click()
    await flushPromises()
    expect(get).toHaveBeenCalledWith('/resources/usage')
  })
})
