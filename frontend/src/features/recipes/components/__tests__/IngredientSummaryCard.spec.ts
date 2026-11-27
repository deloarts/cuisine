import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import IngredientSearch from '@/features/recipes/components/IngredientSearch.vue'
import IngredientSummaryCard from '@/features/recipes/components/IngredientSummaryCard.vue'
import {
  emptyForm,
  newStepIngredient,
  type EditorForm,
  type EditorStepIngredient,
} from '@/features/recipes/composables/recipeEditorState'
import { useIngredientWeights } from '@/features/recipes/composables/useIngredientWeights'
import type { UnitResponse } from '@/shared/cookbook/types'

vi.mock('@/features/recipes/api/recipes', () => ({
  searchIngredients: () => Promise.resolve({ items: [] }),
  searchRecipes: () => Promise.resolve({ items: [] }),
}))

function unit(id: string, kind: string, toBase: number | null): UnitResponse {
  return {
    ...({} as UnitResponse),
    id,
    code: id,
    kind,
    to_base: toBase,
    name: id,
    plural_name: id,
    abbreviation: id,
    sort_order: 0,
  }
}

const units = [unit('g', 'mass', 1), unit('cup', 'volume', 240), unit('pc', 'count', null)]

function row(id: string, name: string, amount: number | null, unitId: string | null): EditorStepIngredient {
  return { ...newStepIngredient({ id, name }), amount, unit_id: unitId }
}

function formWith(declared: EditorStepIngredient[], steps: EditorStepIngredient[][]): EditorForm {
  const form = emptyForm('en-GB')
  form.ingredients = declared
  form.steps = steps.map((ingredients) => ({ ...form.steps[0]!, ingredients }))
  return reactive(form) as EditorForm
}

async function mountCard(form: EditorForm) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  const wrapper = mount(IngredientSummaryCard, {
    props: { form, locale: 'en-GB', units, canCreateIngredient: false },
    global: { plugins: [router, i18n, OpenVue, ToastService] },
  })
  await flushPromises()
  return wrapper
}

const usages = (wrapper: Awaited<ReturnType<typeof mountCard>>) =>
  wrapper.findAll('[data-testid="summary-line"]').map((li) => {
    const usage = li.find('[data-testid="summary-usage"]')
    return usage.exists() ? [usage.attributes('data-usage'), usage.text()] : null
  })

describe('IngredientSummaryCard', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'enGB'
    // Flour weighs 120 g a cup; known from the session, so nothing is fetched.
    useIngredientWeights().remember('flour', {
      density_g_per_ml: null,
      conversions: [{ unit_id: 'cup', grams: 120 } as never],
    })
    useIngredientWeights().remember('salt', { density_g_per_ml: null, conversions: [] })
  })

  it('lists the declared lines and the ingredients only the steps name', async () => {
    const form = formWith(
      [row('flour', 'Flour', 300, 'g')],
      [[row('flour', 'Flour', 100, 'g'), row('egg', 'Egg', 2, 'pc')], [row('egg', 'Egg', 1, 'pc')]],
    )
    const wrapper = await mountCard(form)
    expect(wrapper.findAll('[data-testid="summary-line"]')).toHaveLength(1)
    const only = wrapper.findAll('[data-testid="summary-step-only"]')
    expect(only).toHaveLength(1)
    expect(only[0]!.text()).toContain('Egg')
    expect(only[0]!.text()).toContain('3 pc')
    expect(only[0]!.text()).toContain('only in the steps')
  })

  it('adds a step-only ingredient to the list with what the steps use', async () => {
    const form = formWith([], [[row('egg', 'Egg', 2, 'pc')], [row('egg', 'Egg', 1, 'pc')]])
    const wrapper = await mountCard(form)
    await wrapper.get('[data-testid="summary-add-step-only"]').trigger('click')
    expect(form.ingredients).toHaveLength(1)
    expect(form.ingredients[0]).toMatchObject({ ingredient_id: 'egg', amount: 3, unit_id: 'pc' })
    expect(form.ingredients[0]!.id).toBeUndefined()
    expect(wrapper.find('[data-testid="summary-step-only"]').exists()).toBe(false)
    expect(usages(wrapper)).toEqual([null])
  })

  it('adds an ingredient picked in the summary to the list', async () => {
    const form = formWith([], [[]])
    const wrapper = await mountCard(form)
    wrapper.getComponent(IngredientSearch).vm.$emit('select', { id: 'salt', name: 'Salt', kind: 'ingredient' })
    await flushPromises()
    expect(form.ingredients.map((l) => l.ingredient_id)).toEqual(['salt'])
    expect(form.steps[0]!.ingredients).toEqual([])
    expect(usages(wrapper)).toEqual([['unused', expect.stringContaining('Not used in any step')]])
  })

  it('warns about a line no step uses and about the part the steps leave out', async () => {
    const form = formWith(
      [row('salt', 'Salt', 5, 'g'), row('flour', 'Flour', 500, 'g')],
      [[row('flour', 'Flour', 200, 'g')], [row('flour', 'Flour', 100, 'g')]],
    )
    const wrapper = await mountCard(form)
    expect(usages(wrapper)).toEqual([
      ['unused', expect.stringContaining('Not used in any step')],
      ['partly', expect.stringContaining('200 g not used in any step')],
    ])
  })

  it('weighs the units when it can and says when it cannot check', async () => {
    const form = formWith(
      [row('flour', 'Flour', 300, 'g'), row('egg', 'Egg', 2, 'pc')],
      [[row('flour', 'Flour', 1, 'cup'), row('egg', 'Egg', 100, 'g')]],
    )
    const wrapper = await mountCard(form)
    expect(usages(wrapper)).toEqual([
      ['partly', expect.stringContaining('180 g not used in any step')],
      ['unchecked', expect.stringContaining("Can't be checked")],
    ])
  })

  it('removes a declared line', async () => {
    const form = formWith([row('salt', 'Salt', 5, 'g')], [[]])
    const wrapper = await mountCard(form)
    await wrapper.get('[aria-label="Remove Salt"]').trigger('click')
    expect(form.ingredients).toEqual([])
  })
})
