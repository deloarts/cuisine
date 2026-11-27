import { describe, expect, it } from 'vitest'

import type { RecipeEditResponse } from '@/features/recipes/api/recipes'
import {
  addEquipment,
  ensureLine,
  lineMentions,
  mentionProblemOf,
  removeEquipment,
  removeLine,
  stepsWithStrayMentions,
  addIngredient,
  addStep,
  editorFormFrom,
  emptyForm,
  moveStep,
  removeStep,
  toRequest,
  translationState,
  validate,
} from '@/features/recipes/composables/recipeEditorState'

function filledForm() {
  const form = emptyForm('en-GB')
  form.text['en-GB'].title = 'Goulash'
  form.steps[0]!.text['en-GB'] = 'Brown the onions.'
  return form
}

describe('recipe editor state', () => {
  it('starts with one empty step in the given language', () => {
    const form = emptyForm('de-AT')
    expect(form.original_locale).toBe('de-AT')
    expect(form.steps).toHaveLength(1)
    expect(form.base_servings).toBe(4)
  })

  it('asks for a title and the text of every step', () => {
    const form = emptyForm('en-GB')
    expect(validate(form)).toEqual(['titleRequired', 'stepTextRequired'])
    expect(validate(filledForm())).toEqual([])
  })

  it('refuses zero servings and an empty step list', () => {
    const form = filledForm()
    form.base_servings = 0
    form.steps = []
    expect(validate(form)).toEqual(['servingsInvalid', 'stepsRequired'])
  })

  it('sends only the original and the languages that have a title', () => {
    const form = filledForm()
    form.steps[0]!.text['de-AT'] = 'Zwiebeln anrösten.'
    let request = toRequest(form)
    expect(Object.keys(request.translations)).toEqual(['en-GB'])
    expect(Object.keys(request.steps![0]!.translations)).toEqual(['en-GB'])

    form.text['de-AT'].title = 'Gulasch'
    request = toRequest(form)
    expect(Object.keys(request.translations).sort()).toEqual(['de-AT', 'en-GB'])
    expect(request.steps![0]!.translations).toEqual({
      'en-GB': { text: 'Brown the onions.' },
      'de-AT': { text: 'Zwiebeln anrösten.' },
    })
  })

  it('turns blank sources into null and keeps step ingredients', () => {
    const form = filledForm()
    addIngredient(form, 0, { id: 'onion-id', name: 'Onion' })
    form.steps[0]!.ingredients[0]!.amount = 2
    form.steps[0]!.ingredients[0]!.notes['en-GB'] = 'finely chopped'
    const request = toRequest(form)
    expect(request.source_url).toBeNull()
    expect(request.steps![0]!.ingredients).toEqual([
      {
        ingredient_id: 'onion-id',
        amount: 2,
        unit_id: null,
        notes: { 'en-GB': { note: 'finely chopped' } },
      },
    ])
  })

  it('adds, moves and removes steps', () => {
    const form = filledForm()
    addStep(form)
    form.steps[1]!.text['en-GB'] = 'Add the paprika.'
    moveStep(form, 1, -1)
    expect(form.steps.map((s) => s.text['en-GB'])).toEqual(['Add the paprika.', 'Brown the onions.'])
    moveStep(form, 0, -1)
    expect(form.steps[0]!.text['en-GB']).toBe('Add the paprika.')
    removeStep(form, 0)
    expect(form.steps).toHaveLength(1)
  })

  it('sends a sub-recipe line by its recipe id', () => {
    const form = filledForm()
    addIngredient(form, 0, { id: 'sheets', name: 'Lasagna sheets', kind: 'recipe' })
    form.steps[0]!.ingredients[0]!.amount = 250
    const line = toRequest(form).steps![0]!.ingredients![0]!
    expect(line).toMatchObject({ sub_recipe_id: 'sheets', amount: 250 })
    expect(line).not.toHaveProperty('ingredient_id')
  })

  it('wants a yield with both amount and unit, or neither', () => {
    const form = filledForm()
    form.yield_amount = 500
    expect(validate(form)).toEqual(['yieldIncomplete'])
    form.yield_unit_id = 'g'
    expect(validate(form)).toEqual([])
    expect(toRequest(form)).toMatchObject({ yield_amount: 500, yield_unit_id: 'g' })
  })

  it('sends the shares only for the shared level', () => {
    const form = filledForm()
    form.shared_user_ids = ['u2']
    expect(toRequest(form)).toMatchObject({ visibility: 'instance', shared_user_ids: [] })
    form.visibility = 'shared'
    expect(toRequest(form)).toMatchObject({ visibility: 'shared', shared_user_ids: ['u2'] })
  })

  it('reads the chosen paired instances and sends them only for the shared level', () => {
    const form = filledForm()
    form.shared_peer_ids = ['p1']
    expect(toRequest(form)).toMatchObject({ visibility: 'instance', shared_peer_ids: [] })
    form.visibility = 'shared'
    expect(toRequest(form)).toMatchObject({ visibility: 'shared', shared_peer_ids: ['p1'] })
  })

  it('tells how far a translation is', () => {
    const form = filledForm()
    expect(translationState(form, 'de-AT')).toBe('missing')
    form.text['de-AT'].title = 'Gulasch'
    expect(translationState(form, 'de-AT')).toBe('partial')
    form.steps[0]!.text['de-AT'] = 'Zwiebeln anrösten.'
    expect(translationState(form, 'de-AT')).toBe('complete')
  })

  it('reads every language of a saved recipe back into the form', () => {
    const recipe = {
      id: 'r1',
      status: 'draft',
      original_locale: 'de-AT',
      translations: {
        'de-AT': { title: 'Gulasch', description: '', tips: '' },
        'en-GB': { title: 'Goulash', description: '', tips: '' },
      },
      base_servings: 4,
      prep_minutes: 15,
      cook_minutes: 90,
      rest_minutes: null,
      difficulty: 'medium',
      cover_image_id: null,
      source_url: null,
      source_name: null,
      tag_ids: ['t1'],
      yield_amount: null,
      yield_unit_id: null,
      less_visible_sub_recipe_ids: [],
      visibility: 'household',
      effective_visibility: 'household',
      shared_user_ids: [],
      shared_group_ids: [],
      can_change_visibility: true,
      steps: [
        {
          id: 'step-id',
          translations: { 'de-AT': { text: 'Anrösten.' }, 'en-GB': { text: 'Brown.' } },
          duration_minutes: 10,
          image_id: null,
          ingredients: [
            {
              id: 'line-id',
              ingredient_id: 'onion-id',
              sub_recipe_id: null,
              ingredient_name: 'Zwiebel',
              amount: 3,
              unit_id: null,
              notes: { 'de-AT': { note: 'fein' } },
            },
          ],
          equipment: [],
        },
      ],
      created_via: 'web',
      owner: null,
      can_edit: true,
      can_delete: true,
      co_editors: [],
      can_manage_co_editors: true,
      based_on: null,
      created: '',
      changed: '',
      published_at: null,
      shared_peers: [],
      peer_capped: false,
      peer_hidden_sub_recipe_ids: [],
      ingredients: [],
    } satisfies RecipeEditResponse
    const form = editorFormFrom(recipe)
    expect(form.original_locale).toBe('de-AT')
    expect(form.visibility).toBe('household')
    expect(form.text['en-GB'].title).toBe('Goulash')
    expect(form.steps[0]!.text).toEqual({ 'en-GB': 'Brown.', 'de-AT': 'Anrösten.' })
    expect(form.steps[0]!.ingredients[0]!.notes['de-AT']).toBe('fein')
    expect(toRequest(form).steps![0]!.ingredients![0]!.notes).toEqual({ 'de-AT': { note: 'fein' } })
  })

  describe('mentions and step lines', () => {
    const FLOUR = '11111111-1111-4111-8111-111111111111'
    const SHEETS = '22222222-2222-4222-8222-222222222222'

    it('adds a line with no amount for a chip the step lacks, once', () => {
      const form = filledForm()
      const step = form.steps[0]!
      ensureLine(step, { kind: 'ingredient', id: FLOUR, name: 'Flour' })
      ensureLine(step, { kind: 'ingredient', id: FLOUR, name: 'Flour' })
      ensureLine(step, { kind: 'recipe', id: SHEETS, name: 'Sheets' })
      expect(step.ingredients.map((i) => [i.ingredient_id, i.sub_recipe_id, i.amount])).toEqual([
        [FLOUR, null, null],
        [null, SHEETS, null],
      ])
    })

    it('turns the chips of a removed line into plain text in every language', () => {
      const form = filledForm()
      const step = form.steps[0]!
      ensureLine(step, { kind: 'ingredient', id: FLOUR, name: 'Flour' })
      step.text['en-GB'] = `Sift @[Flour](ingredient:${FLOUR}).`
      step.text['de-AT'] = `@[Mehl](ingredient:${FLOUR}) sieben.`
      removeLine(step, 0)
      expect(step.ingredients).toHaveLength(0)
      expect(step.text).toEqual({ 'en-GB': 'Sift Flour.', 'de-AT': 'Mehl sieben.' })
    })

    it('keeps the line when only the chip goes', () => {
      const form = filledForm()
      const step = form.steps[0]!
      ensureLine(step, { kind: 'ingredient', id: FLOUR, name: 'Flour' })
      step.text['en-GB'] = 'Sift it.'
      expect(step.ingredients).toHaveLength(1)
      expect(validate(form)).toEqual([])
    })

    it('flags a step that mentions something it has no line for', () => {
      const form = filledForm()
      form.steps[0]!.text['en-GB'] = `Sift @[Flour](ingredient:${FLOUR}).`
      expect(stepsWithStrayMentions(form)).toEqual([0])
      expect(validate(form)).toEqual(['mentionMissing'])
    })
  })

  describe('equipment', () => {
    const WHISK = '33333333-3333-4333-8333-333333333333'
    const BOWL = '44444444-4444-4444-8444-444444444444'

    it('adds the item for an equipment chip, once, and offers it to `@`', () => {
      const form = filledForm()
      const step = form.steps[0]!
      ensureLine(step, { kind: 'equipment', id: WHISK, name: 'Whisk' })
      ensureLine(step, { kind: 'equipment', id: WHISK, name: 'Whisk' })
      expect(step.ingredients).toHaveLength(0)
      expect(step.equipment.map((e) => [e.equipment_id, e.equipment_name, e.count])).toEqual([[WHISK, 'Whisk', null]])
      expect(lineMentions(step)).toEqual([{ kind: 'equipment', id: WHISK, name: 'Whisk' }])
    })

    it('turns the chips of a removed item into plain text in every language', () => {
      const form = filledForm()
      const step = form.steps[0]!
      addEquipment(step, { id: WHISK, name: 'Whisk' })
      addEquipment(step, { id: BOWL, name: 'Bowl' })
      step.text['en-GB'] = `Beat in the @[Bowl](equipment:${BOWL}) with the @[Whisk](equipment:${WHISK}).`
      step.text['de-AT'] = `Mit dem @[Schneebesen](equipment:${WHISK}) schlagen.`
      removeEquipment(step, 0)
      expect(step.equipment.map((e) => e.equipment_id)).toEqual([BOWL])
      expect(step.text).toEqual({
        'en-GB': `Beat in the @[Bowl](equipment:${BOWL}) with the Whisk.`,
        'de-AT': 'Mit dem Schneebesen schlagen.',
      })
      expect(validate(form)).toEqual([])
    })

    it('flags an equipment mention the step has no item for', () => {
      const form = filledForm()
      form.steps[0]!.text['de-AT'] = `Mit dem @[Schneebesen](equipment:${WHISK}) schlagen.`
      expect(stepsWithStrayMentions(form)).toEqual([0])
      addEquipment(form.steps[0]!, { id: WHISK, name: 'Whisk' })
      expect(stepsWithStrayMentions(form)).toEqual([])
    })

    it('reads step equipment with its notes and sends it back', () => {
      const form = filledForm()
      const step = form.steps[0]!
      addEquipment(step, { id: BOWL, name: 'Bowl' })
      step.equipment[0]!.count = 2
      step.equipment[0]!.notes['en-GB'] = ' large '
      const sent = toRequest(form).steps![0]!.equipment
      expect(sent).toEqual([{ equipment_id: BOWL, count: 2, notes: { 'en-GB': { note: 'large' } } }])

      const loaded = editorFormFrom({
        ...({} as RecipeEditResponse),
        original_locale: 'en-GB',
        translations: { 'en-GB': { title: 'Cake', description: '', tips: '' } },
        tag_ids: [],
        shared_user_ids: [],
        shared_group_ids: [],
        visibility: 'instance',
        steps: [
          {
            id: 'step-id',
            translations: { 'en-GB': { text: 'Mix.' } },
            duration_minutes: null,
            image_id: null,
            ingredients: [],
            equipment: [
              {
                id: 'equipment-line-id',
                equipment_id: BOWL,
                equipment_name: 'Bowl',
                count: 2,
                notes: { 'de-AT': { note: 'groß' } },
              },
            ],
          },
        ],
      })
      expect(loaded.steps[0]!.equipment[0]).toMatchObject({
        equipment_id: BOWL,
        equipment_name: 'Bowl',
        count: 2,
        notes: { 'en-GB': '', 'de-AT': 'groß' },
      })
    })
  })

  describe('the backend mention error', () => {
    it('reads step, locale, kind and id from a 422', () => {
      const err = {
        response: {
          status: 422,
          data: { detail: 'Step 2 mentions …', step: 2, locale: 'de-AT', mention_kind: 'equipment', mention_id: 'x' },
        },
      }
      expect(mentionProblemOf(err)).toEqual({ stepIndex: 1, locale: 'de-AT', kind: 'equipment', id: 'x' })
    })

    it('ignores other errors', () => {
      expect(mentionProblemOf({ response: { status: 422, data: { detail: 'Step 2 mentions …' } } })).toBeNull()
      expect(mentionProblemOf({ response: { status: 409, data: { step: 1 } } })).toBeNull()
      expect(mentionProblemOf(new Error('offline'))).toBeNull()
    })
  })
  it('sends back the ids of existing steps and lines, and none for new ones', () => {
    const loaded = editorFormFrom({
      ...({} as RecipeEditResponse),
      original_locale: 'en-GB',
      translations: { 'en-GB': { title: 'Cake', description: '', tips: '' } },
      tag_ids: [],
      shared_user_ids: [],
      shared_group_ids: [],
      visibility: 'instance',
      steps: [
        {
          id: 'step-id',
          translations: { 'en-GB': { text: 'Mix.' } },
          duration_minutes: null,
          image_id: null,
          ingredients: [
            {
              id: 'line-id',
              ingredient_id: 'flour-id',
              sub_recipe_id: null,
              ingredient_name: 'Flour',
              amount: 200,
              unit_id: null,
              notes: {},
            },
          ],
          equipment: [
            { id: 'equipment-line-id', equipment_id: 'bowl-id', equipment_name: 'Bowl', count: null, notes: {} },
          ],
        },
      ],
    })
    addIngredient(loaded, 0, { id: 'sugar-id', name: 'Sugar' })
    addStep(loaded)
    loaded.steps[1]!.text['en-GB'] = 'Bake.'
    const sent = toRequest(loaded).steps!
    expect(sent[0]!.id).toBe('step-id')
    expect(sent[0]!.ingredients!.map((i) => i.id)).toEqual(['line-id', undefined])
    expect(sent[0]!.equipment![0]!.id).toBe('equipment-line-id')
    expect(sent[1]!.id).toBeUndefined()
  })
})
