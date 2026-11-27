import { describe, expect, it } from 'vitest'

import type { VariationResponse } from '@/features/recipes/api/recipes'
import {
  addExtraLine,
  changeKind,
  emptyVariationForm,
  incompleteChanges,
  newChange,
  removeExtraLine,
  setTarget,
  toVariationRequest,
  validateVariation,
  variationFormFrom,
} from '@/features/recipes/composables/variationEditorState'

const SUGAR = '11111111-1111-4111-8111-111111111111'
const HONEY = '22222222-2222-4222-8222-222222222222'

describe('variation editor state', () => {
  it('needs a name and at least one complete change', () => {
    const form = emptyVariationForm('en-GB')
    expect(validateVariation(form)).toEqual(['nameRequired', 'changesRequired'])
    form.name = 'With honey'
    form.changes.push(newChange('swap'))
    expect(validateVariation(form)).toEqual(['changeIncomplete'])
    expect(incompleteChanges(form)).toEqual([0])
  })

  it('starts a swap on the whole recipe, an extra step at the start, the rest on step 1', () => {
    expect(newChange('swap').step).toBeNull()
    expect(newChange('extra_step').step).toBe(0)
    expect(newChange('remove_line').step).toBe(1)
    expect(newChange('step_text', 3).step).toBe(3)
  })

  it('turns a swap that keeps the amount into a request without amount, unit or note', () => {
    const form = emptyVariationForm('de-AT')
    form.name = '  Mit Honig '
    const swap = newChange('swap', 2)
    setTarget(swap, { kind: 'ingredient', id: SUGAR, name: 'Zucker' })
    swap.to_ingredient_id = HONEY
    swap.amount = 50
    swap.note = 'flüssig'
    form.changes.push(swap)
    expect(validateVariation(form)).toEqual([])
    expect(toVariationRequest(form)).toEqual({
      name: 'Mit Honig',
      note: '',
      locale: 'de-AT',
      private: false,
      changes: [
        {
          kind: 'swap',
          id: null,
          step: 2,
          ingredient_id: SUGAR,
          to_ingredient_id: HONEY,
          keep_amount: true,
          amount: null,
          unit_id: null,
          note: '',
          text: '',
        },
      ],
    })
    swap.keep_amount = false
    expect(toVariationRequest(form).changes![0]).toMatchObject({ keep_amount: false, amount: 50, note: 'flüssig' })
  })

  it('keeps the step and the id when the kind changes, and clears the rest', () => {
    const change = newChange('remove_line', 2)
    change.id = 'kept-id'
    setTarget(change, { kind: 'recipe', id: SUGAR, name: 'Sheets' })
    const next = changeKind(change, 'step_text')
    expect(next).toMatchObject({ id: 'kept-id', key: change.key, kind: 'step_text', step: 2, sub_recipe_id: null })
  })

  it('unlinks the chips of a removed extra-step line', () => {
    const change = newChange('extra_step', 1)
    addExtraLine(change, { id: SUGAR, name: 'Sugar' })
    addExtraLine(change, { id: SUGAR, name: 'Sugar' })
    change.text = `Caramelise @[Sugar](ingredient:${SUGAR}).`
    expect(change.lines).toHaveLength(1)
    removeExtraLine(change, 0)
    expect(change.lines).toHaveLength(0)
    expect(change.text).toBe('Caramelise Sugar.')
  })

  it('loads a saved variation with its change ids and drops changes whose ingredient is gone', () => {
    const variation = {
      id: 'v1',
      recipe_id: 'r1',
      name: 'With honey',
      note: 'Less sweet',
      locale: 'en-GB',
      private: true,
      changes: [
        {
          id: 'c1',
          kind: 'extra_step',
          step: 0,
          ingredient_id: null,
          ingredient_name: null,
          sub_recipe: null,
          to_ingredient_id: null,
          to_ingredient_name: null,
          amount: null,
          unit: null,
          keep_amount: true,
          note: '',
          text: 'Warm the honey.',
          duration_minutes: 5,
          lines: [{ ingredient_id: HONEY, ingredient_name: 'Honey', amount: 2, unit: null, note: '' }],
          equipment: [],
          available: true,
          applies: true,
        },
        {
          id: 'c2',
          kind: 'remove_line',
          step: 1,
          ingredient_id: null,
          ingredient_name: null,
          sub_recipe: null,
          to_ingredient_id: null,
          to_ingredient_name: null,
          amount: null,
          unit: null,
          keep_amount: true,
          note: '',
          text: '',
          duration_minutes: null,
          lines: [],
          equipment: [],
          available: false,
          applies: false,
        },
      ],
    } as unknown as VariationResponse
    const form = variationFormFrom(variation)
    expect(form).toMatchObject({ name: 'With honey', note: 'Less sweet', private: true })
    expect(form.changes.map((c) => c.id)).toEqual(['c1'])
    expect(toVariationRequest(form).changes![0]).toMatchObject({
      id: 'c1',
      kind: 'extra_step',
      step: 0,
      duration_minutes: 5,
      lines: [{ ingredient_id: HONEY, amount: 2, unit_id: null, note: '' }],
      equipment: [],
    })
  })
})
