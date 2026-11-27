import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import RecipePicker from '@/shared/cookbook/RecipePicker.vue'

const get = vi.fn<(...args: unknown[]) => Promise<unknown>>()
vi.mock('@/core/api/webRequest', () => ({ webApi: { get: (...args: unknown[]) => get(...args) } }))

describe('RecipePicker', () => {
  it('lists the recipes alphabetically from the dropdown button and searches typed text', async () => {
    get.mockResolvedValue({ items: [] })
    const wrapper = mount(RecipePicker, {
      props: { inputId: 'pick' },
      global: { plugins: [i18n, OpenVue] },
      attachTo: document.body,
    })
    const autocomplete = wrapper.findComponent({ name: 'AutoComplete' })
    expect(wrapper.find('[data-pc-section="dropdown"]').exists()).toBe(true)

    autocomplete.vm.$emit('complete', { query: '' })
    await flushPromises()
    expect(get).toHaveBeenLastCalledWith('/recipes', {
      query: { status: 'published', sort: 'title', limit: 20 },
    })

    autocomplete.vm.$emit('complete', { query: ' coq ' })
    await flushPromises()
    expect(get).toHaveBeenLastCalledWith('/recipes', {
      query: { search: 'coq', status: 'published', sort: 'title', limit: 20 },
    })
    wrapper.unmount()
  })
})
