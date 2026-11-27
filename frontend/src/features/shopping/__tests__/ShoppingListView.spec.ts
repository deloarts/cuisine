import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import Tooltip from 'openvue/tooltip'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Schemas } from '@/core/api/generated'
import { i18n } from '@/core/i18n'
import ShoppingListView from '@/features/shopping/views/ShoppingListView.vue'
import { resetHousehold } from '@/shared/household/useHousehold'

type Item = Schemas['ShoppingItemResponse']
type Ref = Schemas['SubRecipeRef']

const webGet = vi.fn<(path: string) => Promise<unknown>>()
const webPatch = vi.fn<(path: string) => Promise<unknown>>()

vi.mock('@/core/api/webRequest', () => ({
  webApi: { get: (path: string) => webGet(path), patch: (path: string) => webPatch(path) },
}))
vi.mock('@/features/shopping/liveEvents', () => ({ useShoppingListEvents: () => ({ connected: ref(true) }) }))

function recipe(title: string): Ref {
  return { id: `r-${title}`, title, accessible: true, total_minutes: null, cover_image_id: null }
}

const hidden: Ref = { id: null, title: null, accessible: false, total_minutes: null, cover_image_id: null }
const grams = { id: 'g', code: 'g', name: 'gram', plural_name: 'grams', abbreviation: 'g', kind: 'mass' }

function item(name: string, extra: Partial<Item> = {}): Item {
  return {
    id: name,
    ingredient_id: `i-${name}`,
    name,
    text: '',
    amount: null,
    unit: null,
    category: null,
    family_id: null,
    checked: false,
    checked_by: null,
    checked_at: null,
    recipe: null,
    recipes: [],
    sub_recipe_path: [],
    has_warning: false,
    ...extra,
  }
}

function list(items: Item[]) {
  return {
    id: 'list-1',
    name: 'Market',
    is_owner: true,
    owner: null,
    members: [],
    open_count: items.length,
    checked_count: 0,
    changed: '2026-11-25T10:00:00Z',
    mode: 'normal',
    keep: false,
    last_activity_at: '2026-11-25T10:00:00Z',
    deletes_on: null,
    bought_window_hours: 24,
    items,
  }
}

async function open(items: Item[]) {
  webGet.mockImplementation((path) => {
    if (path === '/shopping-lists/{list_id}') return Promise.resolve(list(items))
    if (path === '/households/mine') return Promise.resolve({ household: null })
    return Promise.resolve([])
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/shopping', name: 'shopping', component: { render: () => null } },
      { path: '/shopping/:id', name: 'shopping-list', component: ShoppingListView },
    ],
  })
  await router.push('/shopping/list-1')
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(ShoppingListView, {
    global: {
      plugins: [router, i18n, OpenVue, ToastService, ConfirmationService],
      directives: { tooltip: Tooltip },
    },
  })
  await flushPromises()
  return wrapper
}

describe('ShoppingListView items', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetHousehold()
  })
  afterEach(() => vi.clearAllMocks())

  it('names every recipe an item is for', async () => {
    const wrapper = await open([item('Flour', { recipes: [recipe('Coq au vin'), recipe('Red cabbage')] })])
    expect(wrapper.get('[data-testid="item-source"]').text()).toBe('for Coq au vin, Red cabbage')
  })

  it('names two recipes and counts the rest when there are many', async () => {
    const many = ['Bread', 'Pizza', 'Cake', 'Pancakes'].map(recipe)
    const wrapper = await open([item('Flour', { recipes: many })])
    expect(wrapper.get('[data-testid="item-source"]').text()).toBe('for Bread, Pizza +2')
  })

  it('shows the placeholder for each recipe the viewer cannot see', async () => {
    const wrapper = await open([item('Flour', { recipes: [hidden, recipe('Bread'), hidden] })])
    expect(wrapper.get('[data-testid="item-source"]').text()).toBe(
      "for a recipe you don't have access to, Bread, a recipe you don't have access to",
    )
  })

  it('puts the amount and unit in bold on the name row', async () => {
    const wrapper = await open([item('Flour', { amount: 500, unit: grams })])
    const name = wrapper.get('.item-name')
    expect(name.get('[data-testid="item-amount"]').text()).toBe('500 g')
    expect(name.text()).toContain('Flour')
    expect(wrapper.find('[data-testid="item-source"]').exists()).toBe(false)
    expect(wrapper.find('.item-meta').exists()).toBe(false)
  })

  it('keeps an item ticked while the list is open in its place until the list opens again', async () => {
    const wrapper = await open([item('Milk'), item('Flour', { checked: true })])
    const sections = () => wrapper.findAll('.group').map((g) => g.findAll('.item-name').map((n) => n.text()))
    expect(sections()).toEqual([['Milk'], ['Flour']])

    webPatch.mockResolvedValue(list([item('Milk', { checked: true }), item('Flour', { checked: true })]))
    await wrapper.findAll('.item-toggle')[0]!.trigger('click')
    await flushPromises()
    expect(sections()).toEqual([['Milk'], ['Flour']])
    expect(wrapper.findAll('.item')[0]!.classes()).toContain('item--checked')

    wrapper.unmount()
    const again = await open([item('Milk', { checked: true }), item('Flour', { checked: true })])
    expect(again.findAll('.group').map((g) => g.findAll('.item-name').map((n) => n.text()))).toEqual([['Flour', 'Milk']])
  })
})
