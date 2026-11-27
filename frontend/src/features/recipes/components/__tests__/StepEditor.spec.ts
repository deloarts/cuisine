import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

import { webApi } from '@/core/api/webRequest'
import { i18n } from '@/core/i18n'
import StepEditor from '@/features/recipes/components/StepEditor.vue'
import {
  emptyStep,
  newStepIngredient,
  type EditorStep,
  type EditorStepIngredient,
} from '@/features/recipes/composables/recipeEditorState'
import type { SummaryLine } from '@/features/recipes/utils/ingredientSummary'
import type { IngredientResponse, UnitResponse } from '@/shared/cookbook/types'

const searchIngredients = vi.fn<(q: string) => Promise<{ items: IngredientResponse[] }>>()
const uploadImage = vi.fn<(file: File) => Promise<{ id: string }>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  searchIngredients: (q: string) => searchIngredients(q),
  searchRecipes: () => Promise.resolve({ items: [] }),
  uploadImage: (file: File) => uploadImage(file),
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

const units = [unit('g', 'mass', 1), unit('pc', 'count', null)]

function ingredient(id: string, name: string): IngredientResponse {
  return {
    ...({} as IngredientResponse),
    id,
    name,
    matched_alias: null,
    conversions: [],
    density_g_per_ml: null,
    season_months: [],
    allergens: [],
    status: 'active',
  } as IngredientResponse
}

function line(id: string, name: string, amount: number | null, unitId: string | null): EditorStepIngredient {
  const row = newStepIngredient({ id, name, kind: 'ingredient' })
  row.amount = amount
  row.unit_id = unitId
  return row
}

function mountStep(step: EditorStep, declared: SummaryLine[] = [], recipeLines: SummaryLine[] = []) {
  const wrapper = mount(StepEditor, {
    props: {
      step,
      index: 0,
      count: 1,
      locale: 'en-GB',
      units,
      canCreateIngredient: false,
      equipment: [],
      declared,
      recipeLines,
    },
    global: { plugins: [createPinia(), i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  return wrapper
}

// Each option by the name assistive technology reads, a group heading by its text.
const offered = () =>
  [...document.body.querySelectorAll('[role="option"]')].map(
    (o) => o.getAttribute('aria-label') ?? o.textContent?.replace(/\s+/g, ' ').trim(),
  )

async function openPicker(wrapper: ReturnType<typeof mountStep>) {
  const input = wrapper.get('input[id^="step-"][id$="-add"]:not([id$="-eq-add"])')
  const button = input.element.parentElement!.querySelector('button')!
  button.click()
  await new Promise((resolve) => setTimeout(resolve, 50))
  await flushPromises()
  return input
}

async function type(wrapper: ReturnType<typeof mountStep>, text: string) {
  const input = wrapper.get('input[id^="step-"][id$="-add"]:not([id$="-eq-add"])')
  ;(input.element as HTMLInputElement).value = text
  await input.trigger('input')
  // AutoComplete waits for a pause in typing before it searches.
  await new Promise((resolve) => setTimeout(resolve, 350))
  await flushPromises()
}

beforeEach(() => {
  i18n.global.locale.value = 'enGB'
  searchIngredients.mockReset().mockResolvedValue({ items: [] })
  uploadImage.mockReset()
  // Weights of an ingredient not picked in this session are not needed here.
  vi.spyOn(webApi, 'get').mockRejectedValue(new Error('not in this spec'))
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('StepEditor photo', () => {
  // Focusing a file input hidden off the layout scrolled the app shell and
  // left the page shifted out of view; the input must never take focus.
  it('opens the file picker from a button without moving focus to the hidden input', async () => {
    const step = reactive(emptyStep())
    const wrapper = mountStep(step)
    await flushPromises()
    const input = wrapper.get('input[type="file"]').element as HTMLInputElement
    const click = vi.spyOn(input, 'click')

    const button = wrapper.findAll('button').find((b) => b.text() === 'Add a photo')
    expect(button, 'an "Add a photo" button').toBeDefined()
    ;(button!.element as HTMLButtonElement).focus()
    await button!.trigger('click')

    expect(click).toHaveBeenCalledOnce()
    expect(input.hidden).toBe(true)
    expect(input.tabIndex).toBe(-1)
    expect(document.activeElement).not.toBe(input)
    wrapper.unmount()
  })

  it('uploads the chosen file and keeps its id on the step', async () => {
    uploadImage.mockResolvedValue({ id: 'img-1' })
    const step = reactive(emptyStep())
    const wrapper = mountStep(step)
    await flushPromises()
    const input = wrapper.get('input[type="file"]')
    const file = new File(['x'], 'onion.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(uploadImage).toHaveBeenCalledWith(file)
    expect(step.image_id).toBe('img-1')
    expect(wrapper.findAll('button').some((b) => b.text() === 'Replace the photo')).toBe(true)
    wrapper.unmount()
  })
})

describe('StepEditor ingredient picker with the declared list', () => {
  // Onion: 2 pc declared, unused. Flour: 500 g declared, 200 g used by
  // another step. Salt: to taste, already used. Paprika: on this step already.
  const declared: SummaryLine[] = [
    line('onion', 'Onion', 2, 'pc'),
    line('flour', 'Flour', 500, 'g'),
    line('salt', 'Salt', null, null),
    line('paprika', 'Paprika', 1, 'pc'),
  ]
  const otherStep = [line('flour', 'Flour', 200, 'g'), line('salt', 'Salt', null, null)]

  function setup() {
    const step = reactive(emptyStep())
    step.ingredients.push(line('paprika', 'Paprika', null, null))
    const wrapper = mountStep(step, declared, [...otherStep, ...step.ingredients])
    return { step, wrapper }
  }

  it('offers the unused and partly used lines first, under their own heading', async () => {
    searchIngredients.mockResolvedValue({ items: [ingredient('flour', 'Flour'), ingredient('leek', 'Leek')] })
    const { wrapper } = setup()
    await flushPromises()
    await openPicker(wrapper)

    expect(offered()).toEqual([
      'From the ingredient list',
      'Onion, 2 pc, not used in any step yet',
      'Flour, 300 g left',
      'More ingredients and recipes',
      'Leek',
    ])
    wrapper.unmount()
  })

  it('filters the list lines by what is typed', async () => {
    const { wrapper } = setup()
    await flushPromises()
    await type(wrapper, 'flo')
    expect(offered().slice(0, 3)).toEqual(['From the ingredient list', 'Flour, 300 g left', 'More ingredients and recipes'])

    await type(wrapper, 'leek')
    expect(offered()).not.toContain('From the ingredient list')
    wrapper.unmount()
  })

  it('adds a picked line with the missing amount in the declared unit', async () => {
    const { step, wrapper } = setup()
    await flushPromises()
    await type(wrapper, 'flo')
    ;(document.body.querySelector('[role="option"][aria-label^="Flour"]') as HTMLElement).click()
    await flushPromises()

    const added = step.ingredients.at(-1)!
    expect(added).toMatchObject({ ingredient_id: 'flour', amount: 300, unit_id: 'g' })
    wrapper.unmount()
  })

  it('picks a list line from the keyboard, skipping the heading', async () => {
    const { step, wrapper } = setup()
    await flushPromises()
    const input = await openPicker(wrapper)
    await input.trigger('keydown', { code: 'ArrowDown', key: 'ArrowDown' })
    await input.trigger('keydown', { code: 'Enter', key: 'Enter' })
    await flushPromises()

    expect(step.ingredients.at(-1)).toMatchObject({ ingredient_id: 'onion', amount: 2, unit_id: 'pc' })
    wrapper.unmount()
  })

  it('keeps the plain list when the declared list has nothing left to offer', async () => {
    searchIngredients.mockResolvedValue({ items: [ingredient('leek', 'Leek')] })
    const step = reactive(emptyStep())
    const wrapper = mountStep(step, [line('leek', 'Leek', null, null)], [line('leek', 'Leek', 1, 'pc')])
    await flushPromises()
    await openPicker(wrapper)
    expect(offered()).toEqual(['Leek'])
    wrapper.unmount()
  })
})
