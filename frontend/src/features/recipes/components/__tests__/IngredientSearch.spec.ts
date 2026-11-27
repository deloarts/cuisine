import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import IngredientSearch, { type FromListOption } from '@/features/recipes/components/IngredientSearch.vue'

vi.mock('@/features/recipes/api/recipes', () => ({
  searchIngredients: () => Promise.resolve({ items: [] }),
  searchRecipes: () => Promise.resolve({ items: [] }),
}))

const bacon: FromListOption = {
  key: 'bacon',
  target: { id: 'bacon', name: 'Bacon', kind: 'ingredient' } as FromListOption['target'],
  hint: '9 pc, not used in any step yet',
}

describe('IngredientSearch', () => {
  it('empties the field after a pick from the dropdown button', async () => {
    i18n.global.locale.value = 'enGB'
    const wrapper = mount(IngredientSearch, {
      props: { inputId: 'search', canCreate: false, fromList: [bacon] },
      global: { plugins: [createPinia(), i18n, OpenVue, ToastService] },
    })
    const picker = wrapper.findComponent({ name: 'AutoComplete' })
    const option = { kind: 'list', name: 'Bacon', label: `Bacon, ${bacon.hint}`, option: bacon }
    ;(picker.vm as unknown as { onOptionSelect: (event: Event, option: unknown) => void }).onOptionSelect(
      new Event('click'),
      option,
    )
    await flushPromises()

    expect(wrapper.emitted('select')).toEqual([[bacon.target]])
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('')
    wrapper.unmount()
  })
})
