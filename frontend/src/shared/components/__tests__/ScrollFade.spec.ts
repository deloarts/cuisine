import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { h } from 'vue'

import ScrollFade from '@/shared/components/ScrollFade.vue'

function sized(el: HTMLElement, scrollHeight: number, clientHeight: number) {
  Object.defineProperty(el, 'scrollHeight', { configurable: true, value: scrollHeight })
  Object.defineProperty(el, 'clientHeight', { configurable: true, value: clientHeight })
}

describe('ScrollFade', () => {
  it('fades while content lies below and shows the scrollbar only while scrolling', async () => {
    vi.useFakeTimers()
    const wrapper = mount(ScrollFade, { slots: { default: () => h('p', 'A long text') } })
    const box = wrapper.get('[data-testid="scroll-fade"]')
    sized(box.element as HTMLElement, 400, 100)

    await box.trigger('scroll')
    expect(box.classes()).toContain('scroll-fade--more')
    expect(box.classes()).toContain('scroll-fade--scrolling')

    ;(box.element as HTMLElement).scrollTop = 300
    await box.trigger('scroll')
    expect(box.classes()).not.toContain('scroll-fade--more')

    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(box.classes()).not.toContain('scroll-fade--scrolling')
    vi.useRealTimers()
    wrapper.unmount()
  })
})
