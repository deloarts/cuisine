import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import RecipeTagList from '@/features/recipes/components/RecipeTagList.vue'

const tags = ['Lunch', 'Dinner', 'Main', 'Quick', 'Austrian'].map((name, i) => ({ id: `t${i}`, name }))

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/recipes', name: 'recipes', component: { template: '<div />' } }],
  })
}

// jsdom has no layout, so each element reports the line it would sit on: the
// first `perLine` items of the list share the first line.
function layOut(perLine: number) {
  vi.spyOn(HTMLElement.prototype, 'offsetTop', 'get').mockImplementation(function (this: HTMLElement) {
    const items = Array.from(this.parentElement?.children ?? [])
    return items.indexOf(this) < perLine ? 0 : 40
  })
}

async function mountList() {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(RecipeTagList, { props: { tags }, global: { plugins: [i18n, router()] } })
  await flushPromises()
  return wrapper
}

function names(wrapper: Awaited<ReturnType<typeof mountList>>) {
  return wrapper.findAll('a').map((a) => a.text())
}

describe('RecipeTagList', () => {
  afterEach(() => vi.restoreAllMocks())

  it('shows every tag when they fit on one line', async () => {
    layOut(10)
    const wrapper = await mountList()
    expect(names(wrapper)).toEqual(['Lunch', 'Dinner', 'Main', 'Quick', 'Austrian'])
    expect(wrapper.find('[data-testid="recipe-tags-more"]').exists()).toBe(false)
  })

  it('keeps the first line and leaves room for the chip that counts the rest', async () => {
    layOut(3)
    const wrapper = await mountList()
    expect(names(wrapper)).toEqual(['Lunch', 'Dinner'])
    expect(wrapper.get('[data-testid="recipe-tags-more"]').text()).toBe('+3 more')
  })

  it('shows every tag once the chip is clicked', async () => {
    layOut(3)
    const wrapper = await mountList()
    await wrapper.get('[data-testid="recipe-tags-more"]').trigger('click')
    expect(names(wrapper)).toEqual(['Lunch', 'Dinner', 'Main', 'Quick', 'Austrian'])
    expect(wrapper.find('[data-testid="recipe-tags-more"]').exists()).toBe(false)
  })
})
