import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { MealPlanRequest, MealPlanSuggestion, SuggestionQuery } from '@/features/meal-plan/api/mealPlan'
import EntryDialog from '@/features/meal-plan/components/EntryDialog.vue'
import { SUGGESTION_TYPE } from '@/features/meal-plan/suggestionDrag'
import MealPlanView from '@/features/meal-plan/views/MealPlanView.vue'
import { resetHousehold } from '@/shared/household/useHousehold'

const large = ref(true)
const webGet = vi.fn<(path: string) => Promise<unknown>>()
const getSuggestions = vi.fn<(query: SuggestionQuery) => Promise<MealPlanSuggestion[]>>()
const planMeal = vi.fn<(body: MealPlanRequest) => Promise<unknown>>()

vi.mock('@/shared/composables/useWideScreen', () => ({ useLargeScreen: () => large }))
vi.mock('@/core/api/webRequest', () => ({ webApi: { get: (path: string) => webGet(path) } }))
vi.mock('@/features/meal-plan/api/mealPlan', () => ({
  getSuggestions: (query: SuggestionQuery) => getSuggestions(query),
  planMeal: (body: MealPlanRequest) => planMeal(body),
  listEntries: () => webGet('/meal-plan'),
  listShoppingLists: () => webGet('/shopping-lists'),
}))

const goulash = {
  recipe: { id: 'r1', title: 'Gulasch', base_servings: 4, cover_image_id: null },
  reason: 'often_cooked',
} as unknown as MealPlanSuggestion

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/meal-plan', component: MealPlanView },
      { path: '/recipes/:id', name: 'recipe', component: { render: () => null } },
      { path: '/household', name: 'household', component: { render: () => null } },
    ],
  })
  await router.push('/meal-plan')
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(MealPlanView, {
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

function drop(data: Record<string, string>) {
  return {
    dataTransfer: { types: Object.keys(data), getData: (type: string) => data[type] ?? '', dropEffect: '' },
  }
}

describe('MealPlanView suggestions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetHousehold()
    large.value = true
    webGet.mockImplementation((path) => Promise.resolve(path === '/households/mine' ? { household: null } : []))
    getSuggestions.mockResolvedValue([goulash])
    planMeal.mockResolvedValue({})
  })
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('shows the suggestions below the week only on a large screen', async () => {
    const wrapper = await open()
    expect(wrapper.text()).toContain('Gulasch')
    large.value = false
    await flushPromises()
    expect(wrapper.text()).not.toContain('Suggestions')
  })

  it('plans a suggestion dropped on a meal and reloads the week', async () => {
    const wrapper = await open()
    const slot = wrapper.findAll('.slot')[2]!
    const payload = { [SUGGESTION_TYPE]: JSON.stringify({ id: 'r1', title: 'Gulasch', servings: 4 }) }
    await slot.trigger('dragover', drop(payload))
    expect(slot.classes()).toContain('slot--drop')
    const loads = webGet.mock.calls.filter(([path]) => path === '/meal-plan').length
    await slot.trigger('drop', drop(payload))
    await flushPromises()
    expect(planMeal).toHaveBeenCalledWith(
      expect.objectContaining({ slot: 'dinner', recipe_id: 'r1', title: 'Gulasch', servings: 4 }),
    )
    expect(webGet.mock.calls.filter(([path]) => path === '/meal-plan').length).toBe(loads + 1)
  })

  it('ignores anything else dropped on a meal', async () => {
    const wrapper = await open()
    await wrapper.findAll('.slot')[0]!.trigger('drop', drop({ 'text/plain': 'Gulasch' }))
    await flushPromises()
    expect(planMeal).not.toHaveBeenCalled()
  })

  it('opens the meal dialog with the suggested recipe', async () => {
    const wrapper = await open()
    await wrapper.get('button[aria-label="Plan Gulasch"]').trigger('click')
    await flushPromises()
    // The dialog fills its fields when its opening transition ends, which
    // jsdom never runs, so the spec reads what the view handed it.
    const dialog = wrapper.findComponent(EntryDialog)
    expect(dialog.props('visible')).toBe(true)
    expect(dialog.props('editing')).toBeNull()
    expect(dialog.props('preset')).toEqual({ recipeId: 'r1', recipeTitle: 'Gulasch', servings: 4 })
    expect(dialog.props('mealSlot')).toBe('dinner')
  })
})
