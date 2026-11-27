import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { computed } from 'vue'

import type { HomeResponse, ShoppingListSummary } from '@/features/home/api/home'
import HomeView from '@/features/home/views/HomeView.vue'

const getHome = vi.fn<() => Promise<HomeResponse>>()
const getShoppingLists = vi.fn<() => Promise<ShoppingListSummary[]>>()

vi.mock('@/features/home/api/home', () => ({
  getHome: () => getHome(),
  getShoppingLists: () => getShoppingLists(),
  setFavourite: () => Promise.resolve(),
}))

vi.mock('@/shared/household/useHousehold', () => ({
  useHousehold: () => ({
    shoppingListId: computed(() => 'l2'),
    load: () => Promise.resolve(null),
  }),
}))

const recipe = {
  id: 'r1',
  title: 'Gulasch',
  difficulty: 'easy',
  status: 'published',
  tags: [],
  diets: [],
  is_favourite: false,
  rating_average: null,
  rating_count: 0,
  variation_count: 0,
  total_minutes: null,
  description_text: null,
  cover_image_id: null,
} as unknown as HomeResponse['newest'][number]

const home = {
  recently_cooked: [],
  favourites: [],
  in_season: [],
  newest: [recipe],
} as unknown as HomeResponse

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: HomeView },
      { path: '/recipes', name: 'recipes', component: { render: () => null } },
      { path: '/recipes/:id', name: 'recipe', component: { render: () => null } },
      { path: '/meal-plan', name: 'meal-plan', component: { render: () => null } },
      { path: '/cooked', name: 'cooked', component: { render: () => null } },
      { path: '/shopping', name: 'shopping', component: { render: () => null } },
      { path: '/shopping/:id', name: 'shopping-list', component: { render: () => null } },
      { path: '/ingredients/:id', name: 'ingredient', component: { render: () => null } },
    ],
  })
  await router.push('/')
  i18n.global.locale.value = 'enGB'
  return mount(HomeView, { global: { plugins: [router, i18n, OpenVue, ToastService] } })
}

describe('HomeView loading', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getShoppingLists.mockResolvedValue([])
  })
  afterEach(() => vi.clearAllMocks())

  it('shows the sections with skeletons until the page answers, then the recipes', async () => {
    let answer!: (value: HomeResponse) => void
    getHome.mockReturnValue(new Promise((resolve) => (answer = resolve)))
    const wrapper = await open()
    await flushPromises()

    expect(wrapper.get('[data-testid="home-skeleton"]').attributes('role')).toBe('status')
    expect(wrapper.find('[data-testid="home-newest"]').text()).toContain('New recipes')
    expect(wrapper.find('[data-testid="recipe-card-r1"]').exists()).toBe(false)

    answer(home)
    await flushPromises()
    expect(wrapper.find('[data-testid="home-skeleton"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="recipe-card-r1"]').exists()).toBe(true)
  })

  it('drops the skeletons when the page fails to load', async () => {
    getHome.mockRejectedValue(new Error('down'))
    const wrapper = await open()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-skeleton"]').exists()).toBe(false)
  })

  it('puts the cards first, then new recipes, in season and favourites', async () => {
    getHome.mockResolvedValue({ ...home, in_season: [recipe] })
    const wrapper = await open()
    await flushPromises()

    const order = wrapper
      .findAll('[data-testid^="home-"]')
      .map((el) => el.attributes('data-testid'))
      .filter((id) => !id?.startsWith('home-shopping-'))
    expect(order).toEqual([
      'home-recentlyCooked',
      'home-shopping',
      'home-newest',
      'home-inSeason',
      'home-favourites',
    ])
  })

  it('lists the household shopping list first with what is left to buy', async () => {
    getHome.mockResolvedValue(home)
    const list = (id: string, name: string, open: number, at: string) =>
      ({ id, name, open_count: open, checked_count: 0, last_activity_at: at }) as ShoppingListSummary
    getShoppingLists.mockResolvedValue([
      list('l1', 'Party', 1, '2026-11-25T10:00:00Z'),
      list('l2', 'Weekly shop', 4, '2026-11-01T10:00:00Z'),
    ])
    const wrapper = await open()
    await flushPromises()

    const rows = wrapper.findAll('[data-testid^="home-shopping-"]')
    expect(rows.map((r) => r.attributes('data-testid'))).toEqual(['home-shopping-l2', 'home-shopping-l1'])
    expect(rows[0]!.text()).toContain('4 items to buy')
    expect(rows[0]!.text()).toContain('Household')
    expect(rows[1]!.text()).toContain('1 item to buy')
  })
})

describe('HomeView food fact', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getShoppingLists.mockResolvedValue([])
  })
  afterEach(() => vi.clearAllMocks())

  it('shows the food fact of the day as the first card when there is one', async () => {
    getHome.mockResolvedValue({
      ...home,
      food_fact: {
        key: 'potato.andes',
        text: 'Potatoes come from the Andes.',
        locale: 'en-GB',
        ingredient_id: 'i1',
        ingredient_name: 'potato',
        source_title: 'Potato',
        source_url: 'https://en.wikipedia.org/wiki/Potato',
      },
    })
    const wrapper = await open()
    await flushPromises()
    const cards = wrapper.findAll('[data-testid^="home-"]').map((el) => el.attributes('data-testid'))
    expect(cards[0]).toBe('home-foodFact')
  })

  it('leaves the card out when the page has no fact', async () => {
    getHome.mockResolvedValue({ ...home, food_fact: null })
    const wrapper = await open()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-foodFact"]').exists()).toBe(false)
  })
})
