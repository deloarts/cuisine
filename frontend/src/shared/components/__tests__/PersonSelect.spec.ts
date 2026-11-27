import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { afterEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import PersonSelect from '@/shared/components/PersonSelect.vue'

const people = [
  { id: 'u1', display_name: 'Anna Huber', avatar_id: 'file-1' },
  { id: 'u2', display_name: 'Ben Maier', avatar_id: null },
]

function mountSelect(modelValue: string | null) {
  return mount(PersonSelect, {
    props: { people, modelValue, ariaLabel: 'Person', placeholder: 'Everyone' },
    global: { plugins: [i18n, OpenVue] },
    attachTo: document.body,
  })
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('PersonSelect', () => {
  it('shows the chosen person with their avatar', () => {
    const value = mountSelect('u1').find('[role="combobox"]')
    expect(value.text()).toContain('Anna Huber')
    expect(value.find('img').attributes('src')).toContain('/files/file-1/content')
  })

  it('shows the placeholder while nobody is chosen', () => {
    expect(mountSelect(null).find('[role="combobox"]').text()).toBe('Everyone')
  })

  it('lists everyone with an avatar or their initials', async () => {
    const wrapper = mountSelect(null)
    await wrapper.find('[role="combobox"]').trigger('click')
    await flushPromises()
    const options = [...document.body.querySelectorAll('[role="option"]')]
    expect(options.map((o) => o.textContent?.trim())).toEqual(['Anna Huber', 'Ben Maier'])
    expect(options[0]?.querySelector('img')).not.toBeNull()
    expect(options[1]?.querySelector('[data-initials="BM"]')).not.toBeNull()
    wrapper.unmount()
  })
})
