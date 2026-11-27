import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type {
  RecipeDetailResponse,
  VariationResponse,
  VariationViewResponse,
} from '@/features/recipes/api/recipes'
import CookModeView from '@/features/recipes/views/CookModeView.vue'
import RecipeView from '@/features/recipes/views/RecipeView.vue'

const getRecipe = vi.fn<(id: string) => Promise<RecipeDetailResponse>>()
const listVariations = vi.fn<(id: string) => Promise<VariationResponse[]>>()
const viewVariation = vi.fn<(id: string, variationId: string) => Promise<VariationViewResponse>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  getRecipe: (id: string) => getRecipe(id),
  listVariations: (id: string) => listVariations(id),
  viewVariation: (id: string, variationId: string) => viewVariation(id, variationId),
  listRecipeCookEvents: () => Promise.resolve([]),
  listCoEditors: () => Promise.resolve([]),
  listCopies: () => Promise.resolve([]),
  copyRecipe: vi.fn<() => void>(),
  deleteVariation: vi.fn<() => void>(),
  setFavourite: vi.fn<() => void>(),
  getDeletionImpact: vi.fn<() => void>(),
  listShoppingLists: () => Promise.resolve([]),
  addRecipeToList: vi.fn<() => void>(),
  publishRecipe: vi.fn<() => void>(),
  unpublishRecipe: vi.fn<() => void>(),
  deleteRecipe: vi.fn<() => void>(),
  rateRecipe: vi.fn<() => void>(),
  removeRating: vi.fn<() => void>(),
  saveNote: vi.fn<() => void>(),
  logCookEvent: vi.fn<() => void>(),
  adoptVariation: vi.fn<() => void>(),
}))

const sugar = { ingredient_id: 'sugar', name: 'Sugar', amount: 50, unit: null, note: '' }
const honey = { ingredient_id: 'honey', name: 'Honey', amount: 50, unit: null, note: '' }
const raisins = { ingredient_id: 'raisins', name: 'Raisins', amount: 30, unit: null, note: '' }

function recipe(overrides: Partial<RecipeDetailResponse> = {}): RecipeDetailResponse {
  return {
    id: 'r1',
    title: 'Kaiserschmarrn',
    description: '',
    description_text: '',
    visibility: 'instance',
    effective_visibility: 'instance',
    locale: 'en-GB',
    original_locale: 'en-GB',
    available_locales: ['en-GB'],
    status: 'published',
    cover_image_id: null,
    base_servings: 2,
    prep_minutes: null,
    cook_minutes: null,
    rest_minutes: null,
    total_minutes: null,
    difficulty: 'easy',
    tags: [],
    allergens: [],
    diets: [],
    rating_average: 4,
    rating_count: 2,
    is_favourite: false,
    has_warning: false,
    unsuitable_for_guests: false,
    season_months: [],
    in_season: false,
    missing_equipment: null,
    kitchen_ready: null,
    variation_count: 1,
    variation_fits_guests: false,
    variation_fits_diets: false,
    can_edit: false,
    owner: { id: 'u1', display_name: 'Anna Cook' },
    created_via: 'web',
    last_cooked: null,
    created: '2026-11-01T10:00:00Z',
    changed: '2026-11-01T10:00:00Z',
    mirror: null,
    peer_capped: false,
    tips: '',
    source_url: null,
    source_name: null,
    servings: 2,
    yield_amount: null,
    yield_unit: null,
    needs: [],
    equipment: [],
    ingredients: [sugar, raisins],
    steps: [
      { id: 'step-1', position: 1, text: 'Whisk the batter.', duration_minutes: null, image_id: null, ingredients: [], equipment: [] },
      { id: 'step-2', position: 2, text: 'Sweeten it.', duration_minutes: null, image_id: null, ingredients: [sugar, raisins], equipment: [] },
    ],
    nutrition: { total: {}, per_serving: {}, complete: true, missing_ingredient_ids: [], extended: [] },
    warnings: [],
    own_rating: null,
    own_note: null,
    last_cooked_by_me: null,
    can_delete: false,
    based_on: null,
    based_on_count: 0,
    rating_overall_average: 4.3,
    rating_overall_count: 3,
    mirror_details: null,
    source_allergens_added: [],
    unknown_allergens: [],
    unknown_diet_markers: [],
    ...overrides,
  }
}

function variation(): VariationResponse {
  return {
    id: 'v1',
    recipe_id: 'r1',
    name: 'With honey',
    note: 'Less sweet',
    locale: 'en-GB',
    private: false,
    author: { id: 'u2', display_name: 'Ben' },
    based_on_revision: 2,
    current_revision: 2,
    is_stale: false,
    base_revision_available: true,
    stale_steps: [],
    changes: [
      {
        id: 'c1',
        kind: 'swap',
        step: 2,
        ingredient_id: 'sugar',
        ingredient_name: 'Sugar',
        sub_recipe: null,
        to_ingredient_id: 'honey',
        to_ingredient_name: 'Honey',
        amount: null,
        unit: null,
        keep_amount: true,
        note: '',
        text: '',
        duration_minutes: null,
        lines: [],
        equipment: [],
        available: true,
        applies: true,
      },
    ],
    rating_average: 5,
    rating_count: 1,
    own_rating: null,
    can_edit: false,
    can_delete: false,
    can_adopt: false,
    created: '2026-11-22T10:00:00Z',
    changed: '2026-11-22T10:00:00Z',
    mirrored: false,
    source_author_name: null,
  }
}

function applied(): VariationViewResponse {
  return {
    recipe: recipe({
      rating_average: 5,
      rating_count: 1,
      ingredients: [honey, raisins],
      steps: [
        { id: 'step-1', position: 1, text: 'Whisk the batter.', duration_minutes: null, image_id: null, ingredients: [], equipment: [] },
        { id: 'step-2', position: 2, text: 'Sweeten it.', duration_minutes: null, image_id: null, ingredients: [honey, raisins], equipment: [] },
      ],
    }),
    variation: variation(),
    steps: [
      { position: 1, origin_step: 1, added: false, text_changed: false, changed: false, change_ids: [], lines: [], removed: [] },
      {
        position: 2,
        origin_step: 2,
        added: false,
        text_changed: false,
        changed: true,
        change_ids: ['c1'],
        lines: [{ index: 0, kind: 'swapped', change_id: 'c1', swapped_from_ingredient_id: 'sugar', swapped_from_name: 'Sugar' }],
        removed: [],
      },
    ],
  }
}

async function mountAt(path: string, component: typeof RecipeView | typeof CookModeView) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/recipes', name: 'recipes', component: { template: '<div />' } },
      { path: '/recipes/:id', name: 'recipe', component: RecipeView },
      { path: '/recipes/:id/edit', name: 'recipe-edit', component: { template: '<div />' } },
      { path: '/recipes/:id/variations/new', name: 'recipe-variation-new', component: { template: '<div />' } },
      { path: '/recipes/:id/variations/:variationId/edit', name: 'recipe-variation-edit', component: { template: '<div />' } },
      { path: '/recipes/:id/cook', name: 'recipe-cook', component: CookModeView },
    ],
  })
  await router.push(path)
  const wrapper = mount(component, {
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('the variation switch on the recipe page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockReset().mockResolvedValue(recipe())
    listVariations.mockReset().mockResolvedValue([variation()])
    viewVariation.mockReset().mockResolvedValue(applied())
  })

  it('shows the original with the variation count and who does a step differently', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.get('[data-testid="recipe-variations"]').text()).toContain('one variation')
    const differently = wrapper.findAll('[data-testid="step-differently"]')
    expect(differently).toHaveLength(1)
    expect(differently[0]!.text()).toContain('Ben does this differently')
    expect(differently[0]!.text()).toContain('Honey instead of Sugar')
    expect(wrapper.get('[data-testid="rating-overall"]').text()).toContain('4.3')
    expect(viewVariation).not.toHaveBeenCalled()
  })

  it('switches to the applied variation, keeps it in the URL and marks the swapped line', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1', RecipeView)
    await wrapper.get('[data-testid="version-v1"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.variation).toBe('v1')
    expect(viewVariation).toHaveBeenCalledWith('r1', 'v1')
    expect(wrapper.get('[data-testid="variation-info"]').text()).toContain('Less sweet')
    expect(wrapper.text()).toContain('instead of Sugar')
    expect(wrapper.text()).toContain('Rating of "With honey"')
    expect(wrapper.findAll('[data-testid="step-differently"]')).toHaveLength(0)

    await wrapper.get('[data-testid="version-original"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.variation).toBeUndefined()
    expect(wrapper.find('[data-testid="variation-info"]').exists()).toBe(false)
  })

  it('opens cook mode on the chosen variation', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1?variation=v1', RecipeView)
    const start = wrapper.findAll('button').find((b) => b.text().includes('Start cooking'))
    await start!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe-cook')
    expect(router.currentRoute.value.query.variation).toBe('v1')
  })

  it('prints the chosen variation by name with a QR code that opens it', async () => {
    const { wrapper } = await mountAt('/recipes/r1?variation=v1', RecipeView)
    expect(wrapper.get('[data-testid="print-variation"]').text()).toBe('Variation: With honey')
    expect(wrapper.get('[data-testid="recipe-print-qr"]').text()).toContain(`${window.location.origin}/r/v1`)
  })
})

describe('the version choice in cook mode', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockReset().mockResolvedValue(recipe())
    listVariations.mockReset().mockResolvedValue([variation()])
    viewVariation.mockReset().mockResolvedValue(applied())
  })

  it('asks first, then cooks the chosen variation', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/cook', CookModeView)
    expect(wrapper.find('[data-testid="cook-choose"]').exists()).toBe(true)
    await wrapper.get('[data-testid="cook-choose-v1"]').trigger('click')
    await flushPromises()
    expect(viewVariation).toHaveBeenCalledWith('r1', 'v1')
    expect(router.currentRoute.value.query.variation).toBe('v1')
    expect(wrapper.find('[data-testid="cook-choose"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="cook-version"]').text()).toContain('With honey')
  })

  it('cooks the original when chosen', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[data-testid="cook-choose-original"]').trigger('click')
    await flushPromises()
    expect(viewVariation).not.toHaveBeenCalled()
    expect(router.currentRoute.value.query.variation).toBe('original')
    expect(wrapper.text()).toContain('Whisk the batter.')
  })

  it('skips the question when the link names the version', async () => {
    const { wrapper } = await mountAt('/recipes/r1/cook?variation=v1', CookModeView)
    expect(wrapper.find('[data-testid="cook-choose"]').exists()).toBe(false)
    expect(viewVariation).toHaveBeenCalledWith('r1', 'v1')
  })
})
