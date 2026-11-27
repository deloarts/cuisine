import { describe, expect, it } from 'vitest'

import type { StepView, VariationChangeView, VariationResponse } from '@/features/recipes/api/recipes'
import {
  cookVersion,
  lineMarks,
  stepDifferences,
  versionFromQuery,
} from '@/features/recipes/utils/variations'

function change(overrides: Partial<VariationChangeView>): VariationChangeView {
  return {
    id: 'c1',
    kind: 'swap',
    step: 1,
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
    ...overrides,
  }
}

function variation(overrides: Partial<VariationResponse> = {}): VariationResponse {
  return {
    id: 'v1',
    recipe_id: 'r1',
    name: 'With honey',
    note: '',
    locale: 'en-GB',
    private: false,
    author: { id: 'u2', display_name: 'Anna' },
    based_on_revision: 3,
    current_revision: 3,
    is_stale: false,
    base_revision_available: true,
    stale_steps: [],
    changes: [change({})],
    rating_average: null,
    rating_count: 0,
    own_rating: null,
    can_edit: false,
    can_delete: false,
    can_adopt: false,
    created: '2026-11-22T10:00:00Z',
    changed: '2026-11-22T10:00:00Z',
    mirrored: false,
    source_author_name: null,
    ...overrides,
  }
}

function step(position: number, ingredientIds: string[]): StepView {
  return {
    id: `step-${position}`,
    position,
    text: '',
    duration_minutes: null,
    image_id: null,
    ingredients: ingredientIds.map((id) => ({ ingredient_id: id, name: id, amount: 1, unit: null, note: '' })),
    equipment: [],
  }
}

describe('the version switch', () => {
  const list = [variation({ id: 'v1' }), variation({ id: 'v2' })]

  it('reads a known variation from the query and falls back to the original', () => {
    expect(versionFromQuery('v2', list)).toBe('v2')
    expect(versionFromQuery('original', list)).toBeNull()
    expect(versionFromQuery('gone', list)).toBeNull()
    expect(versionFromQuery(undefined, list)).toBeNull()
    expect(versionFromQuery(['v1'], list)).toBeNull()
  })
})

describe('the version cook mode cooks', () => {
  const list = [variation({ id: 'v1' })]

  it('asks when the recipe has variations and the link names none', () => {
    expect(cookVersion(undefined, list)).toEqual({ chosen: null, ask: true })
    expect(cookVersion('unknown', list)).toEqual({ chosen: null, ask: true })
  })

  it('cooks what the link names without asking', () => {
    expect(cookVersion('v1', list)).toEqual({ chosen: 'v1', ask: false })
    expect(cookVersion('original', list)).toEqual({ chosen: null, ask: false })
  })

  it('never asks for a recipe without variations', () => {
    expect(cookVersion(undefined, [])).toEqual({ chosen: null, ask: false })
    expect(cookVersion('v1', [])).toEqual({ chosen: null, ask: false })
  })
})

describe('what a variation does differently per step', () => {
  it('finds step changes, extra steps after the step, and recipe-wide swaps where the ingredient is used', () => {
    const v = variation({
      changes: [
        change({ id: 'a', step: 2, kind: 'remove_line', ingredient_id: 'raisins' }),
        change({ id: 'b', step: 0, kind: 'extra_step', text: 'Preheat.' }),
        change({ id: 'c', step: null, kind: 'swap', ingredient_id: 'sugar' }),
        change({ id: 'd', step: 1, kind: 'step_text', available: false }),
      ],
    })
    const first = stepDifferences([v], step(1, ['flour']))
    expect(first.map((d) => d.changes.map((c) => c.id))).toEqual([['b']])
    const second = stepDifferences([v], step(2, ['sugar', 'raisins']))
    expect(second[0]!.changes.map((c) => c.id)).toEqual(['a', 'c'])
    expect(stepDifferences([v], step(3, ['milk']))).toEqual([])
  })

  it('marks swapped and added lines by index and ignores indexes out of range', () => {
    const marks = lineMarks(
      {
        position: 1,
        origin_step: 1,
        added: false,
        text_changed: false,
        changed: true,
        change_ids: ['c1'],
        lines: [
          { index: 0, kind: 'swapped', change_id: 'c1', swapped_from_ingredient_id: 'sugar', swapped_from_name: 'Sugar' },
          { index: 2, kind: 'added', change_id: 'c2', swapped_from_ingredient_id: null, swapped_from_name: null },
          { index: 7, kind: 'added', change_id: 'c3', swapped_from_ingredient_id: null, swapped_from_name: null },
        ],
        removed: [],
      },
      3,
    )
    expect(marks).toEqual([{ kind: 'swapped', from: 'Sugar' }, null, { kind: 'added', from: null }])
    expect(lineMarks(undefined, 2)).toEqual([null, null])
  })
})
