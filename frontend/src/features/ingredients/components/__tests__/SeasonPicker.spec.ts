import { mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import SeasonPicker from '@/features/ingredients/components/SeasonPicker.vue'

describe('SeasonPicker', () => {
  it('toggles months into a sorted list and sums them up as ranges', async () => {
    const wrapper = mount(SeasonPicker, {
      props: { modelValue: [5], labelledby: 'season' },
      global: { plugins: [i18n, OpenVue] },
    })
    i18n.global.locale.value = 'enGB'
    await wrapper.get('button[aria-label="April"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([[4, 5]])
    await wrapper.setProps({ modelValue: [4, 5] })
    expect(wrapper.get('button[aria-label="May"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain('Apr–May')
  })

  it('offers all year and not seasonal as shortcuts', async () => {
    const wrapper = mount(SeasonPicker, {
      props: { modelValue: [], labelledby: 'season' },
      global: { plugins: [i18n, OpenVue] },
    })
    expect(wrapper.text()).toContain('Not seasonal')
    const allYear = wrapper.findAll('button').find((b) => b.text() === 'All year')!
    await allYear.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]])
  })

  it('changes nothing when read-only', async () => {
    const wrapper = mount(SeasonPicker, {
      props: { modelValue: [1], labelledby: 'season', disabled: true },
      global: { plugins: [i18n, OpenVue] },
    })
    expect(wrapper.findAll('button').some((b) => b.text() === 'All year')).toBe(false)
    expect(wrapper.get('button[aria-label="January"]').attributes('disabled')).toBeDefined()
  })
})
