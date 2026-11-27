import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

import { useShellScroll } from '@/app/layouts/useShellScroll'

const Shell = defineComponent({
  setup() {
    const main = ref<HTMLElement | null>(null)
    useShellScroll(main)
    return () => h('main', { ref: main }, [h(RouterView)])
  },
})

async function setup() {
  const page = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/recipes', component: page },
      { path: '/recipes/:id', component: page },
    ],
  })
  await router.push('/recipes')
  const wrapper = mount(Shell, { global: { plugins: [router] }, attachTo: document.body })
  const main = wrapper.get('main').element as HTMLElement
  // jsdom has no layout, so the scroll area is given room to scroll.
  Object.defineProperty(main, 'scrollHeight', { value: 5000 })
  return { router, wrapper, main }
}

describe('useShellScroll', () => {
  it('opens a new page at the top and keeps the position for a query change', async () => {
    const { router, wrapper, main } = await setup()
    main.scrollTop = 800
    await router.push('/recipes?tag=soup')
    await flushPromises()
    expect(main.scrollTop).toBe(800)

    await router.push('/recipes/r1')
    await flushPromises()
    expect(main.scrollTop).toBe(0)
    wrapper.unmount()
  })

  it('returns to where a page was left when going back', async () => {
    const { router, wrapper, main } = await setup()
    main.scrollTop = 600
    await router.push('/recipes/r1')
    await flushPromises()
    main.scrollTop = 200

    window.dispatchEvent(new PopStateEvent('popstate'))
    router.back()
    await new Promise((resolve) => setTimeout(resolve, 50))
    await flushPromises()
    expect(main.scrollTop).toBe(600)
    wrapper.unmount()
  })
})
