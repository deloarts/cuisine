import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { RecipeListQuery, RecipeSummaryResponse } from '@/features/recipes/api/recipes'
import RecipesView from '@/features/recipes/views/RecipesView.vue'

const getMyHousehold = vi.fn<() => Promise<{ household: { members: { id: string; display_name: string }[] } | null }>>()
const listRecipes = vi.fn<(query: RecipeListQuery) => Promise<{ items: RecipeSummaryResponse[]; total: number }>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  listRecipes: (query: RecipeListQuery) => listRecipes(query),
  listTags: () => Promise.resolve([]),
  setFavourite: vi.fn<() => void>(),
  getMyHousehold: () => getMyHousehold(),
}))

function summary(overrides: Partial<RecipeSummaryResponse> = {}): RecipeSummaryResponse {
  return {
    id: 'r1',
    title: 'Lentil soup',
    description: '',
    description_text: '',
    visibility: 'instance',
    effective_visibility: 'instance',
    locale: 'en-GB',
    original_locale: 'en-GB',
    available_locales: ['en-GB'],
    status: 'published',
    cover_image_id: null,
    base_servings: 4,
    prep_minutes: 10,
    cook_minutes: 30,
    rest_minutes: null,
    total_minutes: 40,
    difficulty: 'easy',
    tags: [],
    allergens: [],
    diets: ['vegetarian', 'vegan'],
    rating_average: null,
    rating_count: 0,
    is_favourite: false,
    has_warning: false,
    unsuitable_for_guests: true,
    season_months: [],
    in_season: false,
    missing_equipment: null,
    kitchen_ready: null,
    variation_count: 0,
    variation_fits_guests: false,
    variation_fits_diets: false,
    can_edit: false,
    owner: null,
    created_via: 'web',
    last_cooked: null,
    created: '2026-11-01T10:00:00Z',
    changed: '2026-11-01T10:00:00Z',
    mirror: null,
    peer_capped: false,
    ...overrides,
  }
}

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/recipes', name: 'recipes', component: RecipesView },
      { path: '/recipes/drafts', name: 'recipe-drafts', component: { template: '<div />' } },
      { path: '/recipes/new', name: 'recipe-new', component: { template: '<div />' } },
      { path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(RecipesView, {
    global: {
      plugins: [router, i18n, OpenVue, ToastService],
      // The guest picker reads the user directory; the spec sets guests through the URL.
      stubs: { UserPicker: true },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('RecipesView diets and dinner guests', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    listRecipes.mockResolvedValue({ items: [summary()], total: 1 })
    getMyHousehold.mockResolvedValue({ household: null })
  })

  it('sends the diets and guests from the URL and flags the cards', async () => {
    const { wrapper } = await mountAt('/recipes?diet=vegan&guest=u2&hideUnsuitable=1')

    expect(listRecipes).toHaveBeenCalledWith(
      expect.objectContaining({ diets: ['vegan'], guests: ['u2'], hide_unsuitable_for_guests: true }),
    )
    expect(wrapper.text()).toContain("Someone won't like this")
    expect(wrapper.text()).toContain('Vegan')
    expect(wrapper.text()).toContain('With one guest')
    expect(wrapper.get('[data-testid="recipe-card-r1"]').attributes('href')).toContain('guest=u2')
  })

  it('filters by a diet picked in the panel and keeps it in the URL', async () => {
    listRecipes.mockResolvedValue({ items: [summary({ unsuitable_for_guests: false })], total: 1 })
    const { wrapper, router } = await mountAt('/recipes')
    expect(wrapper.text()).not.toContain("Someone won't like this")

    const button = (label: string) => wrapper.findAll('button').find((b) => b.text().startsWith(label))
    await button('Diets & guests')!.trigger('click')
    await button('Pescetarian')!.trigger('click')
    await flushPromises()

    expect(listRecipes).toHaveBeenLastCalledWith(
      expect.objectContaining({ diets: ['pescetarian'], guests: [], hide_unsuitable_for_guests: false }),
    )
    expect(router.currentRoute.value.query.diet).toEqual(['pescetarian'])
  })

  it('preselects the household members as dinner guests, unless the URL says none', async () => {
    getMyHousehold.mockResolvedValue({
      household: { members: [{ id: 'me', display_name: 'Me' }, { id: 'u2', display_name: 'Anna' }] },
    })
    const { useCurrentUserStore } = await import('@/core/stores/currentUserStore')
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: [] } as never

    const { router } = await mountAt('/recipes')
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ guests: ['u2'] }))
    expect(router.currentRoute.value.query.guest).toEqual(['u2'])

    listRecipes.mockClear()
    await mountAt('/recipes?noGuests=1')
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ guests: [] }))
  })
})

describe('RecipesView season filter', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    listRecipes.mockReset()
    listRecipes.mockResolvedValue({ items: [summary()], total: 1 })
    getMyHousehold.mockResolvedValue({ household: null })
  })

  it('asks for recipes in season and keeps the chip in the URL', async () => {
    const { wrapper, router } = await mountAt('/recipes')
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ in_season: false }))

    const chip = wrapper.findAll('button').find((b) => b.text() === 'In season now')!
    await chip.trigger('click')
    await flushPromises()

    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ in_season: true }))
    expect(router.currentRoute.value.query.season).toBe('1')
    expect(chip.attributes('aria-pressed')).toBe('true')
  })

  it('reads the season filter from the URL', async () => {
    await mountAt('/recipes?season=1')
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ in_season: true }))
  })
})

describe('RecipesView kitchen flags', () => {
  const mixer = { id: 'mixer', name: 'Stand mixer', kind: 'appliance', icon: null }
  const chip = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) =>
    wrapper.findAll('button').find((b) => b.text() === 'Only what my kitchen can do')

  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    listRecipes.mockReset()
    getMyHousehold.mockResolvedValue({ household: null })
  })

  it('hides the kitchen filter and flags nothing before the kitchen is set up', async () => {
    listRecipes.mockResolvedValue({ items: [summary()], total: 1 })
    const { wrapper } = await mountAt('/recipes')
    expect(chip(wrapper)).toBeUndefined()
    expect(wrapper.find('[data-testid="recipe-card-needs"]').exists()).toBe(false)
  })

  it('names what the kitchen lacks and filters by what it can do', async () => {
    listRecipes.mockResolvedValue({
      items: [
        summary({ kitchen_ready: false, missing_equipment: [mixer, { ...mixer, id: 'scale', name: 'Scale' }] }),
        summary({ id: 'r2', kitchen_ready: false, missing_equipment: [mixer] }),
        summary({ id: 'r3', kitchen_ready: true, missing_equipment: [] }),
      ],
      total: 3,
    })
    const { wrapper, router } = await mountAt('/recipes')
    const flags = wrapper.findAll('[data-testid="recipe-card-needs"]').map((f) => f.text())
    expect(flags).toEqual(['Needs Stand mixer and 1 more', 'Needs Stand mixer'])

    await chip(wrapper)!.trigger('click')
    await flushPromises()
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ only_kitchen_ready: true }))
    expect(router.currentRoute.value.query.kitchen).toBe('1')
  })

  it('keeps the filter chip when the URL turns it on', async () => {
    listRecipes.mockResolvedValue({ items: [], total: 0 })
    const { wrapper } = await mountAt('/recipes?kitchen=1')
    expect(listRecipes).toHaveBeenLastCalledWith(expect.objectContaining({ only_kitchen_ready: true }))
    expect(chip(wrapper)?.attributes('aria-pressed')).toBe('true')
  })
})
