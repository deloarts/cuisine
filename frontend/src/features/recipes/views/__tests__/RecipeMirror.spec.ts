import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { RecipeDetailResponse, VariationResponse } from '@/features/recipes/api/recipes'
import RecipeView from '@/features/recipes/views/RecipeView.vue'
import CookModeView from '@/features/recipes/views/CookModeView.vue'

const getRecipe = vi.fn<(id: string, options?: { guests?: string[] }) => Promise<RecipeDetailResponse>>()
const listVariations = vi.fn<() => Promise<VariationResponse[]>>()
const exportRecipe = vi.fn<() => void>()

vi.mock('@/features/recipes/api/recipes', () => ({
  getRecipe: (id: string, options?: { guests?: string[] }) => getRecipe(id, options),
  setFavourite: vi.fn<() => void>(),
  listRecipeCookEvents: () => Promise.resolve([]),
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
  listVariations: () => listVariations(),
  viewVariation: vi.fn<() => void>(),
  deleteVariation: vi.fn<() => void>(),
  listCoEditors: () => Promise.resolve([]),
  listCopies: () => Promise.resolve([]),
  copyRecipe: vi.fn<() => void>(),
  exportRecipe: () => exportRecipe(),
}))

const unit = { id: 'g', code: 'g', kind: 'mass', name: 'gram', plural_name: 'grams', abbreviation: 'g' }

function recipe(): RecipeDetailResponse {
  const flour = { ingredient_id: 'flour', name: 'Flour', amount: 200, unit, note: '' }
  const eggs = { ingredient_id: 'eggs', name: 'Eggs', amount: 2, unit: null, note: '' }
  return {
    id: 'r1',
    title: 'Pancakes',
    description: 'Thin ones',
    description_text: 'Thin ones',
    visibility: 'instance',
    effective_visibility: 'instance',
    locale: 'en-GB',
    original_locale: 'en-GB',
    available_locales: ['en-GB'],
    status: 'published',
    cover_image_id: null,
    base_servings: 2,
    prep_minutes: 10,
    cook_minutes: 20,
    rest_minutes: null,
    total_minutes: 30,
    difficulty: 'easy',
    tags: [],
    allergens: ['eggs', 'gluten'],
    diets: ['vegetarian'],
    rating_average: null,
    rating_count: 0,
    is_favourite: false,
    has_warning: true,
    unsuitable_for_guests: false,
    season_months: [],
    in_season: false,
    missing_equipment: null,
    kitchen_ready: null,
    variation_count: 0,
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
    ingredients: [flour, eggs],
    steps: [
      { id: 'step-1', position: 1, text: 'Whisk the flour and the eggs.', duration_minutes: null, image_id: null, ingredients: [flour, eggs], equipment: [] },
      { id: 'step-2', position: 2, text: 'Fry them thin.', duration_minutes: 5, image_id: null, ingredients: [], equipment: [] },
    ],
    nutrition: { total: {}, per_serving: { kcal: 350 }, complete: false, missing_ingredient_ids: ['eggs'], extended: [] },
    warnings: [
      { restriction_id: 'w1', kind: 'allergy', allergen: 'eggs', ingredient_id: 'eggs', diet: null, family_id: null, ingredient_names: ['Eggs'] },
    ],
    own_rating: null,
    own_note: null,
    last_cooked_by_me: null,
    can_delete: false,
    based_on: null,
    based_on_count: 0,
    rating_overall_average: null,
    rating_overall_count: 0,
    mirror_details: null,
    source_allergens_added: [],
    unknown_allergens: [],
    unknown_diet_markers: [],
  }
}

async function mountAt(path: string, component: typeof RecipeView | typeof CookModeView) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/recipes', name: 'recipes', component: { template: '<div />' } },
      { path: '/recipes/:id', name: 'recipe', component: RecipeView },
      { path: '/recipes/:id/edit', name: 'recipe-edit', component: { template: '<div />' } },
      { path: '/recipes/:id/cook', name: 'recipe-cook', component: CookModeView },
      { path: '/recipes/:id/variations/new', name: 'recipe-variation-new', component: { template: '<div />' } },
      { path: '/recipes/:id/variations/:variationId', name: 'recipe-variation-edit', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(component, {
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
  })
  await flushPromises()
  return { wrapper, router }
}

const kren = {
  step: 0,
  position: 1,
  name: 'Kren',
  amount: 20,
  unit,
  note: 'frisch gerieben',
  allergens: ['mustard'],
  diet_markers: [],
}

function mirror(overrides: Partial<RecipeDetailResponse> = {}): RecipeDetailResponse {
  return {
    ...recipe(),
    owner: null,
    can_edit: false,
    can_delete: false,
    peer_capped: true,
    mirror: { instance_name: 'Friends', author_name: 'Mia' },
    mirror_details: {
      peer: { id: 'p1', name: 'Friends' },
      instance_name: 'Friends',
      author_name: 'Mia',
      source_url: 'https://friends.example/r/source-1',
      source_revision: 'rev',
      accepted_at: '2026-11-22T10:00:00Z',
      updated_at: '2026-11-22T10:00:00Z',
      plain_lines: [kren],
      plain_equipment: [{ step: 1, name: 'Mörser', count: null, note: '' }],
      unlinked_sub_recipes: [{ step: 1, position: 0, title: null, amount: null, unit: null }],
    },
    ...overrides,
  }
}

describe('a mirror on the recipe page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(mirror())
    listVariations.mockResolvedValue([])
    useCurrentUserStore().user = { id: 'me', is_systemuser: false, effective_permissions: ['write:recipes'] } as never
  })

  it('names its source, links there and explains that copying stays here', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.get('[data-testid="mirror-badge"]').text()).toContain('From another instance')
    expect(wrapper.get('[data-testid="mirror-attribution"]').text()).toBe('by Mia · Friends')
    expect(document.querySelector('[data-testid="mirror-notice"]')).toBeNull()

    await wrapper.get('[data-testid="mirror-badge"]').trigger('click')
    await flushPromises()
    const link = document.querySelector<HTMLAnchorElement>('[data-testid="mirror-source-link"]')!
    expect(link.getAttribute('href')).toBe('https://friends.example/r/source-1')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
    expect(link.textContent?.trim()).toBe('Open at Friends')
    expect(document.querySelector('[data-testid="mirror-notice"]')?.textContent).toContain('stays on this cookbook')
    wrapper.unmount()
  })

  it('names only the instance when the source shows no author', async () => {
    getRecipe.mockResolvedValue(mirror({ mirror: { instance_name: 'Friends', author_name: null } }))
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.get('[data-testid="mirror-attribution"]').text()).toBe('from Friends')
  })

  it('offers no editing, publishing, deleting or export, but copying', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const labels = wrapper.findAll('button').map((b) => b.text())
    expect(labels).toContain('Copy as my recipe')
    for (const hidden of ['Edit', 'Delete', 'Unpublish', 'Export (.cui)', 'Co-editors']) {
      expect(labels.some((l) => l.includes(hidden))).toBe(false)
    }
  })

  it('puts plain lines into their steps and the ingredient list, scaled, with placeholders', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const steps = wrapper.findAll('.step')
    const first = steps[0]!.findAll('.line').map((l) => l.text())
    expect(first).toHaveLength(3)
    expect(first[1]).toContain('Kren')
    expect(first[1]).toContain('not in this catalogue')
    expect(steps[1]!.get('[data-testid="line-unlinked"]').text()).toBe('A recipe that is not on this cookbook')
    expect(steps[1]!.text()).toContain('Mörser')

    await wrapper.get('[aria-label="One serving more"]').trigger('click')
    expect(steps[0]!.text()).toContain('30 g')
    const side = wrapper.get('.recipe-side').text()
    expect(side).toContain('Kren')
    expect(side).toContain('30 g')
  })

  it('says which allergens the source added and lists unknown markers', async () => {
    getRecipe.mockResolvedValue(
      mirror({
        allergens: ['gluten', 'mustard'],
        source_allergens_added: ['mustard'],
        unknown_allergens: ['lupin_x'],
        unknown_diet_markers: ['contains_insects'],
        diets: [],
      }),
    )
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.get('[data-testid="source-allergens"]').text()).toBe('Allergen information from Friends added: Mustard')
    expect(wrapper.get('.recipe-allergens').text()).toContain('contains: lupin_x (unknown marker)')
    expect(wrapper.get('[data-testid="unknown-markers"]').text()).toBe('contains: contains_insects (unknown marker)')
  })

  it('tells dinner guests it might not fit when markers are unknown', async () => {
    getRecipe.mockResolvedValue(mirror({ unsuitable_for_guests: true, unknown_diet_markers: ['contains_insects'] }))
    const { wrapper } = await mountAt('/recipes/r1?guest=u2', RecipeView)
    expect(wrapper.get('[data-testid="guests-might-not-fit"]').text()).toContain('might not fit')
  })

  it('shows mirrored variations read only with their source author', async () => {
    listVariations.mockResolvedValue([
      {
        id: 'v1',
        recipe_id: 'r1',
        name: 'Mehr Kren',
        note: '',
        locale: 'en-GB',
        private: false,
        author: null,
        based_on_revision: 1,
        changes: [],
        can_edit: false,
        can_delete: false,
        can_adopt: false,
        is_stale: false,
        stale_steps: [],
        base_revision_available: true,
        rating_average: null,
        rating_count: 0,
        own_rating: null,
        created: '2026-11-22T10:00:00Z',
        changed: '2026-11-22T10:00:00Z',
        mirrored: true,
        source_author_name: 'Mia',
      } as unknown as VariationResponse,
    ])
    const { wrapper } = await mountAt('/recipes/r1?variation=v1', RecipeView)
    const info = wrapper.get('[data-testid="variation-info"]')
    expect(info.text()).toContain('by Mia · Friends')
    expect(info.text()).not.toContain('Adopt')
    expect(info.text()).not.toContain('Delete')
  })

  it('puts plain lines into the steps in cook mode', async () => {
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    const start = wrapper.findAll('button').find((b) => /step 1|Let's go|Start/i.test(b.text()))
    if (start) {
      await start.trigger('click')
      await flushPromises()
    }
    expect(wrapper.text()).toContain('Kren')
  })
})
