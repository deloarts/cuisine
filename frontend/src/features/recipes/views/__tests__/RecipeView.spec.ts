import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ConfirmationService from 'openvue/confirmationservice'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { RecipeDetailResponse } from '@/features/recipes/api/recipes'
import { isoDay } from '@/features/recipes/utils/dates'
import RecipeView from '@/features/recipes/views/RecipeView.vue'
import CookModeView from '@/features/recipes/views/CookModeView.vue'

const getRecipe = vi.fn<(id: string, options?: { guests?: string[] }) => Promise<RecipeDetailResponse>>()
const setFavourite = vi.fn<() => Promise<void>>()
const getDeletionImpact = vi.fn<() => Promise<unknown>>()
const logCookOnce = vi.fn<(...args: unknown[]) => Promise<unknown>>()
const saveCookModeLayout = vi.fn<(layout: string) => Promise<unknown>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  getRecipe: (id: string, options?: { guests?: string[] }) => getRecipe(id, options),
  setFavourite: () => setFavourite(),
  listRecipeCookEvents: () => Promise.resolve([]),
  getDeletionImpact: () => getDeletionImpact(),
  listShoppingLists: () => Promise.resolve([]),
  addRecipeToList: vi.fn<() => void>(),
  publishRecipe: vi.fn<() => void>(),
  unpublishRecipe: vi.fn<() => void>(),
  deleteRecipe: vi.fn<() => void>(),
  rateRecipe: vi.fn<() => void>(),
  removeRating: vi.fn<() => void>(),
  saveNote: vi.fn<() => void>(),
  logCookEvent: vi.fn<() => void>(),
  logCookOnce: (...args: unknown[]) => logCookOnce(...args),
  saveCookModeLayout: (layout: string) => saveCookModeLayout(layout),
  listVariations: () => Promise.resolve([]),
  viewVariation: vi.fn<() => void>(),
  deleteVariation: vi.fn<() => void>(),
  listCoEditors: () => Promise.resolve([]),
  listCopies: () => Promise.resolve([]),
  copyRecipe: vi.fn<() => void>(),
  exportRecipe: vi.fn<() => void>(),
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
    ],
  })
  await router.push(path)
  const wrapper = mount(component, {
    global: { plugins: [router, i18n, OpenVue, ToastService, ConfirmationService] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('RecipeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(recipe())
  })

  it('scales every amount when the servings change', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.text()).toContain('2 servings')
    expect(wrapper.text()).toContain('200 g')

    await wrapper.get('[aria-label="One serving more"]').trigger('click')

    expect(wrapper.text()).toContain('3 servings')
    expect(wrapper.text()).toContain('300 g')
    expect(wrapper.text()).toContain('3')
    expect(getRecipe).toHaveBeenCalledTimes(1)
  })

  it('shows the reader their own warning and the incomplete nutrition note', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.text()).toContain('Allergy: Eggs')
    expect(wrapper.text()).toContain('Only you see this')
    expect(wrapper.text()).toContain('the values are too low')
  })

  it('shows the diets it fits and the dinner guest flag from the URL', async () => {
    getRecipe.mockResolvedValue({ ...recipe(), unsuitable_for_guests: true })
    const { wrapper } = await mountAt('/recipes/r1?guest=u2&guest=u3', RecipeView)
    expect(getRecipe).toHaveBeenCalledWith('r1', expect.objectContaining({ guests: ['u2', 'u3'] }))
    expect(wrapper.text()).toContain('Vegetarian')
    expect(wrapper.text()).toContain("Someone won't like this")
    expect(wrapper.text()).toContain('At least one of your dinner guests')
  })

  it('opens cook mode with the chosen servings', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1', RecipeView)
    await wrapper.get('[aria-label="One serving more"]').trigger('click')
    const start = wrapper.findAll('button').find((b) => b.text().includes('Start cooking'))
    await start!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe-cook')
    expect(router.currentRoute.value.query.servings).toBe('3')
  })

  it('prints through the browser with the chosen servings and a QR code to the resolver', async () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {})
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    await wrapper.get('[aria-label="One serving more"]').trigger('click')

    await wrapper.get('[data-testid="recipe-print"]').trigger('click')

    expect(print).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="recipe-print-qr"]').text()).toContain(`${window.location.origin}/r/r1`)
    expect(wrapper.text()).toContain('300 g')
  })
})

function withNeeds(): RecipeDetailResponse {
  return {
    ...recipe(),
    needs: [
      {
        sub_recipe: { id: 'sheets', title: 'Pasta sheets', accessible: true, total_minutes: 45, cover_image_id: null },
        amount: 250,
        unit,
        batches: 0.5,
      },
      {
        sub_recipe: { id: null, title: null, accessible: false, total_minutes: null, cover_image_id: null },
        amount: null,
        unit: null,
        batches: 1,
      },
    ],
  }
}

describe('RecipeView sub-recipes', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(withNeeds())
  })

  it('lists what the recipe needs, scaled, with a placeholder for hidden ones', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.text()).toContain('Needs')
    expect(wrapper.text()).toContain('Pasta sheets')
    expect(wrapper.text()).toContain('250 g')
    expect(wrapper.text()).toContain("a recipe you don't have access to")
    expect(wrapper.text()).toContain('plus for Pasta sheets')

    await wrapper.get('[aria-label="One serving more"]').trigger('click')
    expect(wrapper.text()).toContain('375 g')
  })
})

describe('CookModeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(recipe())
    logCookOnce.mockReset()
    logCookOnce.mockResolvedValue({ event: {}, created: true })
    saveCookModeLayout.mockReset()
    saveCookModeLayout.mockResolvedValue({ id: 'me', language: 'enGB', cook_mode_layout: 'flow' })
    Element.prototype.scrollIntoView = vi.fn<() => void>()
  })

  it('walks the steps with the scaled ingredients and finishes by logging and leaving', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/cook?servings=4', CookModeView)
    expect(wrapper.text()).toContain('Step 1 of 2')
    expect(wrapper.text()).toContain('Whisk the flour')
    expect(wrapper.text()).toContain('400 g')

    const button = (label: string) => wrapper.findAll('button').find((b) => b.text() === label)
    await button('Next')!.trigger('click')
    expect(wrapper.text()).toContain('Fry them thin.')
    expect(wrapper.text()).toContain('Timer 5 min')
    expect(button('Next')).toBeUndefined()

    await button('Finish')!.trigger('click')
    await flushPromises()
    expect(logCookOnce).toHaveBeenCalledTimes(1)
    expect(logCookOnce).toHaveBeenCalledWith('r1', isoDay(), 4, null)
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(wrapper.text()).not.toContain('Enjoy your meal!')
  })

  it('leaves silently when the log fails', async () => {
    logCookOnce.mockRejectedValueOnce(new Error('offline'))
    const { wrapper, router } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[data-testid="cook-next"]').trigger('click')
    await wrapper.get('[data-testid="cook-finish"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(document.body.textContent).not.toContain('offline')
  })

  it('does not log when closed with the X', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[aria-label="Leave cook mode"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe')
    expect(logCookOnce).not.toHaveBeenCalled()
  })

  it('does not log a draft', async () => {
    getRecipe.mockResolvedValue({ ...recipe(), status: 'draft' })
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[data-testid="cook-next"]').trigger('click')
    await wrapper.get('[data-testid="cook-finish"]').trigger('click')
    await flushPromises()
    expect(logCookOnce).not.toHaveBeenCalled()
  })

  it('does not log a sub-recipe and leads back to its parent', async () => {
    const { wrapper, router } = await mountAt('/recipes/r1/cook?parent=p1&batches=1', CookModeView)
    await wrapper.get('[data-testid="cook-next"]').trigger('click')
    await wrapper.get('[data-testid="cook-finish"]').trigger('click')
    await flushPromises()
    expect(logCookOnce).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('recipe-cook')
    expect(router.currentRoute.value.params.id).toBe('p1')
  })

  it('opens in the layout saved on the account and finishes from the end of the column', async () => {
    useCurrentUserStore().user = { id: 'me', cook_mode_layout: 'flow' } as never
    const { wrapper, router } = await mountAt('/recipes/r1/cook', CookModeView)
    const flow = wrapper.get('[data-testid="cook-flow"]')
    expect(flow.text()).toContain('Whisk the flour')
    expect(flow.text()).toContain('Fry them thin.')
    expect(wrapper.find('nav').exists()).toBe(false)

    await wrapper.get('[data-testid="cook-finish"]').trigger('click')
    await flushPromises()
    expect(logCookOnce).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.name).toBe('recipe')
  })

  it('switches the layout, keeps the step and saves the choice', async () => {
    saveCookModeLayout.mockImplementation((layout) => Promise.resolve({ id: 'me', language: 'enGB', cook_mode_layout: layout }))
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[data-testid="cook-next"]').trigger('click')

    await wrapper.get('[data-testid="cook-layout-toggle"]').trigger('click')
    await flushPromises()
    expect(saveCookModeLayout).toHaveBeenLastCalledWith('flow')
    expect(wrapper.find('[data-testid="cook-flow"]').exists()).toBe(true)
    expect(wrapper.get('[aria-current="step"]').text()).toContain('Fry them thin.')
    expect(useCurrentUserStore().user?.cook_mode_layout).toBe('flow')

    await wrapper.get('[data-testid="cook-layout-toggle"]').trigger('click')
    await flushPromises()
    expect(saveCookModeLayout).toHaveBeenLastCalledWith('step')
    expect(wrapper.get('[data-testid="cook-step"]').text()).toContain('Fry them thin.')
    expect(wrapper.get('[data-testid="cook-step-label"]').text()).toBe('Step 2 of 2')
  })

  it('goes back to the old layout when saving it fails', async () => {
    saveCookModeLayout.mockRejectedValueOnce(new Error('offline'))
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[data-testid="cook-layout-toggle"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="cook-flow"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="cook-step"]').exists()).toBe(true)
  })

  it('makes a step current with a tap on its number in flow mode', async () => {
    useCurrentUserStore().user = { id: 'me', cook_mode_layout: 'flow' } as never
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    await wrapper.get('[aria-label="Go to step 2"]').trigger('click')
    expect(wrapper.get('[aria-current="step"]').text()).toContain('Fry them thin.')
    expect(wrapper.get('[data-testid="cook-step-label"]').text()).toBe('Step 2 of 2')
  })

  it('offers the sub-recipes first and opens one in cook mode', async () => {
    getRecipe.mockResolvedValue(withNeeds())
    const { wrapper, router } = await mountAt('/recipes/r1/cook?servings=4', CookModeView)
    expect(wrapper.text()).toContain('Make this first')

    const button = (label: string) => wrapper.findAll('button').find((b) => b.text() === label)
    await button('Cook it now')!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('sheets')
    expect(router.currentRoute.value.query).toMatchObject({ batches: '1', parent: 'r1' })
  })

  it('goes from the intro to step 1', async () => {
    getRecipe.mockResolvedValue(withNeeds())
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    const start = wrapper.findAll('button').find((b) => b.text().startsWith('Start with step 1'))
    await start!.trigger('click')
    expect(wrapper.text()).toContain('Whisk the flour')
  })
})

describe('RecipeView seasons and more nutrients', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
  })

  it('shows the season months and whether the recipe is in season now', async () => {
    getRecipe.mockResolvedValue({ ...recipe(), season_months: [11, 12, 1, 2, 6], in_season: true })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.text()).toContain('In season: Jun, Nov–Feb')
    expect(wrapper.text()).toContain('In season now')
  })

  it('lists the extended nutrients per serving behind a toggle and marks incomplete ones', async () => {
    const base = recipe()
    getRecipe.mockResolvedValue({
      ...base,
      nutrition: {
        ...base.nutrition,
        extended: [
          { key: 'vitamin_c_mg', unit: 'mg', total: 24, per_serving: 12, complete: true },
          { key: 'vitamin_b12_ug', unit: 'ug', total: 1.2, per_serving: 0.6, complete: false },
        ],
      },
    })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const toggle = wrapper.findAll('button').find((b) => b.text().startsWith('More nutrients (2)'))!
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('[data-testid="nutrient-vitamin_c_mg"]').text()).toBe('Vitamin C 12 mg')
    const b12 = wrapper.get('[data-testid="nutrient-vitamin_b12_ug"]').text()
    expect(b12).toContain('Vitamin B12')
    expect(b12).toContain('≥')
    expect(b12).toContain('0.6 µg')
    expect(wrapper.text()).toContain('so the real amount is higher')
  })
})

const BOWL = '55555555-5555-4555-8555-555555555555'
const MIXER = '66666666-6666-4666-8666-666666666666'

function withEquipment(): RecipeDetailResponse {
  const base = withNeeds()
  const bowl = { id: BOWL, name: 'Bowl', kind: 'cookware', icon: null }
  const mixer = { id: MIXER, name: 'Stand mixer', kind: 'appliance', icon: 'blender' }
  const roller = { id: 'roller', name: 'Rolling pin', kind: 'utensil', icon: null }
  return {
    ...base,
    kitchen_ready: false,
    missing_equipment: [mixer],
    equipment: [
      { equipment: bowl, count: 2, sub_recipe: null, missing: false },
      { equipment: mixer, count: null, sub_recipe: null, missing: true },
      { equipment: roller, count: null, sub_recipe: base.needs[0]!.sub_recipe, missing: false },
      { equipment: bowl, count: 3, sub_recipe: base.needs[0]!.sub_recipe, missing: false },
    ],
    steps: [
      {
        ...base.steps[0]!,
        text: `Beat in the @[Bowl](equipment:${BOWL}) with the @[Mixer](equipment:${MIXER}).`,
        equipment: [
          { id: 'line-bowl', equipment: bowl, count: 2, note: 'large' },
          { id: 'line-mixer', equipment: mixer, count: null, note: '' },
        ],
      },
      base.steps[1]!,
    ],
  }
}

describe("RecipeView You'll need", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(withEquipment())
  })

  it('lists the own items, then each sub-recipe, and marks what the kitchen lacks', async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const panel = wrapper.get('[data-testid="recipe-equipment"]')
    expect(panel.text()).toContain("You'll need")
    expect(panel.text()).toContain('Your kitchen lacks one item.')
    expect(panel.text()).toContain('2 × Bowl')
    expect(panel.text()).toContain('For Pasta sheets')
    expect(panel.text()).toContain('3 × Bowl')
    expect(panel.findAll(`[data-testid="equipment-${MIXER}"]`)[0]!.text()).toContain('Not in your kitchen')
    expect(panel.findAll('[data-testid="equipment-roller"]')[0]!.text()).not.toContain('Not in your kitchen')
  })

  it("shows a step's equipment with its note and resolves the step's equipment chips", async () => {
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const step = wrapper.get('.step')
    expect(step.text()).toContain('Equipment for this step')
    expect(step.text()).toContain('large')
    expect(step.findAll('.mention--equipment').map((m) => m.text())).toEqual(['Bowl', 'Stand mixer'])
  })
})

describe('CookModeView equipment', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(withEquipment())
  })

  it('sets out every item once on the start screen, marks missing ones, and lists each step\'s equipment', async () => {
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    const setOut = wrapper.get('[data-testid="cook-set-out"]')
    expect(setOut.text()).toContain('3 × Bowl')
    expect(setOut.text()).toContain('Rolling pin')
    expect(setOut.findAll('li')).toHaveLength(3)
    expect(setOut.get(`[data-testid="equipment-${MIXER}"]`).text()).toContain('Not in your kitchen')

    const start = wrapper.findAll('button').find((b) => b.text().startsWith('Start with step 1'))
    await start!.trigger('click')
    const stepEquipment = wrapper.get('[data-testid="cook-step-equipment"]')
    expect(stepEquipment.text()).toContain('2 × Bowl')
    expect(stepEquipment.get(`[data-testid="equipment-${MIXER}"]`).text()).toContain('Not in your kitchen')
  })

  it('opens on a set-out screen when there is nothing to make first', async () => {
    getRecipe.mockResolvedValue({ ...withEquipment(), needs: [] })
    const { wrapper } = await mountAt('/recipes/r1/cook', CookModeView)
    expect(wrapper.text()).toContain('Before you start')
    expect(wrapper.text()).not.toContain('Make this first')
  })
})

describe('RecipeView actions and cards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    i18n.global.locale.value = 'enGB'
    getRecipe.mockResolvedValue(recipe())
  })

  function signIn(permissions: string[], extra: Record<string, unknown> = {}) {
    useCurrentUserStore().user = {
      id: 'me',
      is_systemuser: false,
      effective_permissions: permissions,
      ...extra,
    } as never
  }

  function dialActions(wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) {
    return wrapper.findAll('[data-testid="recipe-dial"] [role="menuitem"]').map((b) => b.text())
  }

  it('offers a reader only the export in the speed dial and keeps print in the header', async () => {
    signIn([])
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(dialActions(wrapper)).toEqual(['Export (.cui)'])
    expect(wrapper.find('.recipe-actions [data-testid="recipe-print"]').exists()).toBe(true)
  })

  it('offers another writer a variation and a copy, but no editing', async () => {
    signIn(['write:recipes'])
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(dialActions(wrapper)).toEqual(['Write a variation', 'Copy as my recipe', 'Export (.cui)'])
  })

  it('offers the owner of a published recipe every action but the copy', async () => {
    signIn(['write:recipes'])
    getRecipe.mockResolvedValue({ ...recipe(), owner: { id: 'me', display_name: 'Me' }, can_edit: true, can_delete: true })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(dialActions(wrapper)).toEqual([
      'Write a variation',
      'Export (.cui)',
      'Edit',
      'Co-editors',
      'Back to draft',
      'Delete',
    ])
  })

  it('offers publishing instead of a variation on a draft', async () => {
    signIn(['write:recipes'])
    getRecipe.mockResolvedValue({
      ...recipe(),
      status: 'draft',
      owner: { id: 'me', display_name: 'Me' },
      can_edit: true,
      can_delete: true,
    })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const actions = dialActions(wrapper)
    expect(actions).toContain('Publish')
    expect(actions).not.toContain('Write a variation')
    expect(actions).not.toContain('Back to draft')
  })

  it('labels every action for screen readers and tooltips', async () => {
    signIn(['write:recipes'])
    getRecipe.mockResolvedValue({ ...recipe(), owner: { id: 'me', display_name: 'Me' }, can_edit: true, can_delete: true })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const dial = wrapper.get('[data-testid="recipe-dial"]')
    expect(dial.get('button[aria-haspopup="true"]').attributes('aria-label')).toBe('More actions')
    for (const item of dial.findAll('[role="menuitem"]')) expect(item.text()).not.toBe('')
  })

  it('opens the delete dialog and goes to the editor from the speed dial', async () => {
    signIn(['write:recipes'])
    getDeletionImpact.mockResolvedValue({ blocked: false, used_by: [], used_by_hidden_count: 0 })
    getRecipe.mockResolvedValue({ ...recipe(), owner: { id: 'me', display_name: 'Me' }, can_edit: true, can_delete: true })
    const { wrapper, router } = await mountAt('/recipes/r1', RecipeView)

    await wrapper.get('[data-testid="recipe-delete"]').trigger('click')
    await flushPromises()
    expect(getDeletionImpact).toHaveBeenCalledTimes(1)

    await wrapper.get('[data-testid="recipe-edit"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('recipe-edit')
  })

  it('names the favourite button by its state and toggles it', async () => {
    signIn([])
    setFavourite.mockResolvedValue()
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const button = wrapper.get('[data-testid="recipe-favourite"]')
    expect(button.text()).toBe('Favourite')

    await button.trigger('click')
    await flushPromises()
    expect(setFavourite).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="recipe-favourite"]').text()).toBe('Favourited')
  })

  it('says the recipe was cooked today instead of offering a second log', async () => {
    getRecipe.mockResolvedValue({ ...recipe(), last_cooked: isoDay(), last_cooked_by_me: isoDay() })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const buttons = wrapper.findAll('[data-testid="recipe-cooked"]')
    expect(buttons).toHaveLength(2)
    for (const button of buttons) {
      expect(button.text()).toBe('Cooked today')
      expect(button.attributes('disabled')).toBeDefined()
    }
  })

  it('offers the log while today is not logged yet', async () => {
    getRecipe.mockResolvedValue({ ...recipe(), last_cooked_by_me: '2020-01-01' })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const button = wrapper.get('[data-testid="recipe-cooked"]')
    expect(button.text()).toBe('I cooked this')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('orders the cards below the recipe as tips, notes, cooked and rating', async () => {
    signIn([])
    getRecipe.mockResolvedValue({ ...recipe(), tips: 'Rest the batter.' })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const cards = wrapper.findAll('[data-testid^="recipe-card-"]').map((c) => c.attributes('data-testid'))
    expect(cards).toEqual(['recipe-card-tips', 'recipe-card-notes', 'recipe-card-cooked', 'recipe-card-rating'])
  })

  it('leaves out the cards the reader turned off on their account', async () => {
    signIn([], {
      recipe_show_tips: false,
      recipe_show_notes: true,
      recipe_show_cooked: false,
      recipe_show_rating: true,
    })
    getRecipe.mockResolvedValue({ ...recipe(), tips: 'Rest the batter.' })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const cards = wrapper.findAll('[data-testid^="recipe-card-"]').map((c) => c.attributes('data-testid'))
    expect(cards).toEqual(['recipe-card-notes', 'recipe-card-rating'])
  })

  it('shows no agent tag on a recipe an agent imported', async () => {
    signIn([])
    getRecipe.mockResolvedValue({ ...recipe(), created_via: 'mcp' })
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    expect(wrapper.text()).not.toContain('Imported by an agent')
  })

  it('puts the steps into a card with their heading', async () => {
    signIn([])
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const steps = wrapper.get('[data-testid="recipe-steps"]')
    expect(steps.classes()).toContain('card')
    expect(steps.get('h2').text()).toBe('Preparation')
    expect(steps.findAll('.step')).toHaveLength(2)
  })

  it('shows the page as a skeleton while the recipe loads', async () => {
    signIn([])
    let resolve: (value: RecipeDetailResponse) => void = () => {}
    getRecipe.mockReturnValue(new Promise((r) => (resolve = r)))
    const { wrapper } = await mountAt('/recipes/r1', RecipeView)
    const skeleton = wrapper.get('[data-testid="recipe-skeleton"]')
    expect(skeleton.attributes('role')).toBe('status')
    expect(skeleton.attributes('aria-label')).toBe('Loading')
    expect(wrapper.find('h1').exists()).toBe(false)

    resolve(recipe())
    await flushPromises()
    expect(wrapper.find('[data-testid="recipe-skeleton"]').exists()).toBe(false)
    expect(wrapper.get('h1').text()).toBe('Pancakes')
  })
})
