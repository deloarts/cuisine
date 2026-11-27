import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { FoodFactResponse } from '@/features/home/api/home'
import FoodFactCard from '@/features/home/components/FoodFactCard.vue'

const fact: FoodFactResponse = {
  key: 'potato.andes',
  text: 'Potatoes were first domesticated in the Andes.',
  locale: 'en-GB',
  ingredient_id: 'a1b2c3d4-0000-4000-8000-000000000001',
  ingredient_name: 'potato',
  source_title: 'Potato',
  source_url: 'https://en.wikipedia.org/wiki/Potato',
}

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/ingredients/:id', name: 'ingredient', component: { render: () => null } },
    ],
  })
  await router.push('/')
  i18n.global.locale.value = 'enGB'
  return mount(FoodFactCard, { props: { fact }, global: { plugins: [router, i18n] } })
}

describe('FoodFactCard', () => {
  it('shows the fact in its language with links to the ingredient and the source', async () => {
    const wrapper = await open()

    expect(wrapper.text()).toContain('Food fact of the day')
    expect(wrapper.get('[lang="en-GB"]').text()).toBe(fact.text)
    expect(wrapper.get('[data-testid="food-fact-ingredient"]').attributes('href')).toBe(
      `/ingredients/${fact.ingredient_id}`,
    )
    const source = wrapper.get('[data-testid="food-fact-source"]')
    expect(source.attributes('href')).toBe(fact.source_url)
    expect(source.attributes('rel')).toBe('noopener noreferrer')
    expect(source.text()).toContain('Source: Wikipedia, Potato')
  })
})
