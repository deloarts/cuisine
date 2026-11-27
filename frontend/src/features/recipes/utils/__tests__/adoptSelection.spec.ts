import { describe, expect, it } from 'vitest'

import type { VariationChangeView, VariationResponse } from '@/features/recipes/api/recipes'
import {
  adoptPayload,
  chosenChanges,
  selectAll,
  toggleChange,
} from '@/features/recipes/utils/adoptSelection'

function change(id: string, overrides: Partial<VariationChangeView> = {}): VariationChangeView {
  return {
    id,
    kind: 'remove_line',
    step: 1,
    ingredient_id: 'raisins',
    ingredient_name: 'Raisins',
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
    available: true,
    applies: true,
    ...overrides,
  }
}

function variation(changes: VariationChangeView[]): VariationResponse {
  return {
    id: 'v1',
    recipe_id: 'r1',
    name: 'With honey',
    note: '',
    locale: 'en-GB',
    private: false,
    author: null,
    based_on_revision: 1,
    current_revision: 1,
    is_stale: false,
    base_revision_available: true,
    stale_steps: [],
    changes,
    rating_average: null,
    rating_count: 0,
    own_rating: null,
    can_edit: false,
    can_delete: false,
    can_adopt: true,
    created: '',
    changed: '',
    mirrored: false,
    source_author_name: null,
  }
}

describe('adopt selection', () => {
  it('starts with every adoptable change and sends null for the whole variation', () => {
    const v = variation([change('a'), change('b')])
    const selected = selectAll(v)
    expect(selected).toEqual(['a', 'b'])
    expect(adoptPayload(v, selected)).toBeNull()
  })

  it('sends the chosen ids in the variation order', () => {
    const v = variation([change('a'), change('b'), change('c')])
    let selected = toggleChange(selectAll(v), 'a')
    selected = toggleChange(selected, 'a')
    selected = toggleChange(selected, 'b')
    expect(selected).toEqual(['c', 'a'])
    expect(adoptPayload(v, selected)).toEqual(['a', 'c'])
    expect(chosenChanges(v, selected).map((c) => c.id)).toEqual(['a', 'c'])
  })

  it('leaves out changes that cannot be adopted and then names the rest explicitly', () => {
    const v = variation([change('a'), change('b', { applies: false }), change('c', { available: false })])
    const selected = selectAll(v)
    expect(selected).toEqual(['a'])
    expect(adoptPayload(v, [...selected, 'b'])).toEqual(['a'])
  })
})
