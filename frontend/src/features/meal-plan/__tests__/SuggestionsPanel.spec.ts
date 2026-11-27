import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { MealPlanSuggestion, SuggestionQuery } from '@/features/meal-plan/api/mealPlan'
import SuggestionsPanel from '@/features/meal-plan/components/SuggestionsPanel.vue'
import { SUGGESTION_TYPE } from '@/features/meal-plan/suggestionDrag'

const getSuggestions = vi.fn<(query: SuggestionQuery) => Promise<MealPlanSuggestion[]>>()

vi.mock('@/features/meal-plan/api/mealPlan', () => ({
  getSuggestions: (query: SuggestionQuery) => getSuggestions(query),
}))

function suggestion(id: string, title: string, reason: MealPlanSuggestion['reason']): MealPlanSuggestion {
  return { recipe: { id, title, base_servings: 4, cover_image_id: null }, reason } as unknown as MealPlanSuggestion
}

const goulash = suggestion('r1', 'Gulasch', 'often_cooked')
const salad = suggestion('r2', 'Kürbissalat', 'in_season')

async function open(planned: string[] = []) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/recipes/:id', name: 'recipe', component: { render: () => null } },
    ],
  })
  await router.push('/')
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(SuggestionsPanel, {
    props: { dateFrom: '2026-11-23', dateTo: '2026-11-29', scope: 'household', planned },
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  return wrapper
}

describe('SuggestionsPanel', () => {
  beforeEach(() => {
    getSuggestions.mockResolvedValue([goulash, salad])
  })
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('shows its frame at once and then the suggestions with their reasons', async () => {
    let answer: (value: MealPlanSuggestion[]) => void = () => undefined
    getSuggestions.mockReturnValue(new Promise((resolve) => (answer = resolve)))
    const wrapper = await open()
    expect(wrapper.find('h2').text()).toContain('Suggestions')
    expect(wrapper.findAll('li')).toHaveLength(12)
    answer([goulash, salad])
    await flushPromises()
    expect(getSuggestions).toHaveBeenCalledWith({
      date_from: '2026-11-23',
      date_to: '2026-11-29',
      scope: 'household',
      slot: undefined,
      limit: 12,
    })
    const cards = wrapper.findAll('li')
    expect(cards).toHaveLength(2)
    expect(cards[0]!.text()).toContain('Gulasch')
    expect(cards[0]!.text()).toContain('Often cooked')
    expect(cards[1]!.text()).toContain('In season')
    expect(cards[0]!.find('a').attributes('href')).toBe('/recipes/r1')
  })

  it('drops a planned recipe at once and reloads for the new week', async () => {
    const wrapper = await open()
    await flushPromises()
    getSuggestions.mockResolvedValue([salad])
    await wrapper.setProps({ planned: ['r1'] })
    expect(wrapper.text()).not.toContain('Gulasch')
    await flushPromises()
    expect(getSuggestions).toHaveBeenCalledTimes(2)
    await wrapper.setProps({ dateFrom: '2026-11-30', dateTo: '2026-12-06' })
    await flushPromises()
    expect(getSuggestions).toHaveBeenLastCalledWith(expect.objectContaining({ date_from: '2026-11-30' }))
  })

  it('emits the recipe to plan, with no meal chosen', async () => {
    const wrapper = await open()
    await flushPromises()
    await wrapper.get('button[aria-label="Plan Gulasch"]').trigger('click')
    const [recipe, slot] = wrapper.emitted('plan')![0]!
    expect((recipe as { id: string }).id).toBe('r1')
    expect(slot).toBeNull()
  })

  it('puts the recipe into the drag data', async () => {
    const wrapper = await open()
    await flushPromises()
    const data = new Map<string, string>()
    const dataTransfer = { setData: (type: string, value: string) => data.set(type, value), effectAllowed: '' }
    await wrapper.get('[data-recipe-id="r2"]').trigger('dragstart', { dataTransfer })
    expect(JSON.parse(data.get(SUGGESTION_TYPE)!)).toEqual({ id: 'r2', title: 'Kürbissalat', servings: 4 })
    expect(dataTransfer.effectAllowed).toBe('copy')
  })

  it('says so when there is nothing to suggest', async () => {
    getSuggestions.mockResolvedValue([])
    const wrapper = await open()
    await flushPromises()
    expect(wrapper.text()).toContain('Nothing to suggest yet')
  })
})
