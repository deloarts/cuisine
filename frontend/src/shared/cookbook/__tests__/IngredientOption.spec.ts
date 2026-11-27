import { mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { beforeEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import IngredientOption from '@/shared/cookbook/IngredientOption.vue'
import type { IngredientMeta, IngredientResponse } from '@/shared/cookbook/types'

const date = {
  name: 'Date',
  category: { id: 'c1', name: 'Fruit' },
  family: { id: 'f1', name: 'Stone fruit' },
  allergens: [] as string[],
  status: 'active',
  season_months: [] as number[],
  owner: { id: 'u1', display_name: 'Anna Huber', avatar_id: null },
  locale: 'en-GB',
  matched_alias: null as string | null,
} as unknown as IngredientResponse

function mountOption(ingredient: Partial<IngredientResponse>, meta?: IngredientMeta[]) {
  return mount(IngredientOption, {
    props: { ingredient: { ...date, ...ingredient }, ...(meta ? { meta } : {}) },
    global: { plugins: [i18n, OpenVue] },
  })
}

beforeEach(() => {
  i18n.global.locale.value = 'enGB'
})

describe('IngredientOption', () => {
  it('shows category, family and the draft state by default', () => {
    const wrapper = mountOption({ status: 'draft' })
    expect(wrapper.text()).toContain('Fruit · Stone fruit')
    expect(wrapper.text()).toContain('Draft')
    expect(wrapper.text()).not.toContain('Anna Huber')
  })

  it('shows only what the picker asks for', () => {
    const wrapper = mountOption({ status: 'draft' }, ['category'])
    expect(wrapper.text()).toContain('Fruit')
    expect(wrapper.text()).not.toContain('Stone fruit')
    expect(wrapper.text()).not.toContain('Draft')
  })

  it('names the owner and language for telling near-duplicates apart', () => {
    expect(mountOption({}, ['owner', 'locale']).text()).toContain('by Anna Huber · English')
  })

  it('lists allergens by name and collapses the rest', () => {
    const wrapper = mountOption({ allergens: ['milk', 'nuts', 'eggs', 'gluten', 'sesame'] }, ['allergens'])
    expect(wrapper.text()).toContain('Contains Milk, Tree nuts, Eggs, Gluten, Sesame')
    expect(wrapper.text()).toContain('+2')
  })

  it('leads with the other name the search matched', () => {
    const wrapper = mountOption({ matched_alias: 'Dattel' })
    expect(wrapper.find('em').text()).toBe('Dattel')
    expect(wrapper.text()).toContain('listed as')
  })

  it('marks an ingredient in season this month', () => {
    const month = new Date().getMonth() + 1
    expect(mountOption({ season_months: [month] }, ['season']).text()).toContain('In season')
    expect(mountOption({ season_months: [] }, ['season']).text()).not.toContain('In season')
  })
})
