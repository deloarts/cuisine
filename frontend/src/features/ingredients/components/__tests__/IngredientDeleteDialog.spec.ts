import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { IngredientResponse } from '@/shared/cookbook/types'
import { i18n } from '@/core/i18n'
import type { IngredientDeletionImpact, IngredientDetail } from '@/features/ingredients/api/ingredients'
import IngredientDeleteDialog from '@/features/ingredients/components/IngredientDeleteDialog.vue'

const impact = vi.fn<() => Promise<IngredientDeletionImpact>>()
const merge = vi.fn<(id: string, into: string) => Promise<IngredientDetail>>()
const remove = vi.fn<() => Promise<void>>()

vi.mock('@/features/ingredients/api/ingredients', () => ({
  ingredientDeletionImpact: () => impact(),
  mergeIngredient: (id: string, into: string) => merge(id, into),
  deleteIngredient: () => remove(),
}))

// The picker searches the catalogue; the spec sets its value directly.
vi.mock('@/shared/cookbook/IngredientPicker.vue', () => ({
  default: {
    name: 'IngredientPicker',
    props: ['modelValue', 'inputId'],
    emits: ['update:modelValue'],
    template: '<input :id="inputId" />',
  },
}))

async function open(props: Record<string, unknown> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } }],
  })
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(IngredientDeleteDialog, {
    props: { visible: false, ingredientId: 'i1', name: 'Erdäpfel', ...props },
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

const button = (label: string) =>
  [...document.body.querySelectorAll('button')].find((b) => b.textContent?.trim() === label)

describe('IngredientDeleteDialog', () => {
  it('blocks a used ingredient, lists the recipes and leads to the merge', async () => {
    impact.mockResolvedValue({
      seeded: false,
      recipe_count: 3,
      recipes: [{ id: 'r1', title: 'Gulasch', cover_image_id: null, status: 'published' }],
      can_merge: true,
    })
    merge.mockResolvedValue({ id: 'i2', name: 'Erdapfel' } as IngredientDetail)
    const wrapper = await open()
    expect(document.body.textContent).toContain('used in 3 recipes')
    expect(document.body.textContent).toContain('Gulasch')
    expect(document.body.textContent).toContain('2 more recipes')
    expect(button('Delete')).toBeUndefined()

    button('Merge into…')!.click()
    await flushPromises()
    expect(button('Merge')!.disabled).toBe(true)

    const picker = wrapper.findComponent({ name: 'IngredientPicker' })
    picker.vm.$emit('update:modelValue', { id: 'i2', name: 'Erdapfel' } as IngredientResponse)
    await flushPromises()
    button('Merge')!.click()
    await flushPromises()
    expect(merge).toHaveBeenCalledWith('i1', 'i2')
    expect(wrapper.emitted('merged')?.[0]).toEqual([{ id: 'i2', name: 'Erdapfel' }])
    wrapper.unmount()
  })

  it('refuses to merge an ingredient into itself', async () => {
    impact.mockResolvedValue({ seeded: false, recipe_count: 0, recipes: [], can_merge: true })
    const wrapper = await open({ mode: 'merge' })
    const picker = wrapper.findComponent({ name: 'IngredientPicker' })
    picker.vm.$emit('update:modelValue', { id: 'i1', name: 'Erdäpfel' } as IngredientResponse)
    await flushPromises()
    expect(document.body.textContent).toContain('Pick a different ingredient.')
    expect(button('Merge')!.disabled).toBe(true)
    wrapper.unmount()
  })

  it('never offers to delete a seeded ingredient', async () => {
    impact.mockResolvedValue({ seeded: true, recipe_count: 0, recipes: [], can_merge: true })
    const wrapper = await open()
    expect(document.body.textContent).toContain('comes with Cuisine and cannot be deleted')
    expect(button('Delete')).toBeUndefined()
    wrapper.unmount()
  })

  it('deletes an unused ingredient after the confirmation', async () => {
    impact.mockResolvedValue({ seeded: false, recipe_count: 0, recipes: [], can_merge: false })
    remove.mockResolvedValue()
    const wrapper = await open()
    button('Delete')!.click()
    await flushPromises()
    expect(remove).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
    wrapper.unmount()
  })
})
