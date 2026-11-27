import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import type { RecipeDeletionImpact } from '@/features/recipes/api/recipes'
import DeleteRecipeDialog from '@/features/recipes/components/DeleteRecipeDialog.vue'

const getDeletionImpact = vi.fn<() => Promise<RecipeDeletionImpact>>()
const deleteRecipe = vi.fn<() => Promise<void>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  getDeletionImpact: () => getDeletionImpact(),
  deleteRecipe: () => deleteRecipe(),
}))

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/recipes/:id', name: 'recipe', component: { template: '<div />' } }],
  })
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(DeleteRecipeDialog, {
    props: { visible: false, recipeId: 'r1', title: 'Goulash' },
    global: { plugins: [router, i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

describe('DeleteRecipeDialog', () => {
  it('lists the recipes that block the deletion', async () => {
    getDeletionImpact.mockResolvedValue({
      blocked: true,
      used_by: [{ id: 'r2', title: 'Lasagna', cover_image_id: null, status: 'published' }],
      used_by_hidden_count: 2,
    })
    const wrapper = await open()
    expect(document.body.textContent).toContain('Lasagna')
    expect(document.body.textContent).toContain('2 more recipes')
    expect(document.body.querySelector('#delete-confirm-name')).toBeNull()
    wrapper.unmount()
  })

  it('deletes only after the name is typed', async () => {
    getDeletionImpact.mockResolvedValue({ blocked: false, used_by: [], used_by_hidden_count: 0 })
    deleteRecipe.mockResolvedValue()
    const wrapper = await open()
    const input = document.body.querySelector<HTMLInputElement>('#delete-confirm-name')!
    const submit = () =>
      [...document.body.querySelectorAll('button')].find((b) => b.textContent?.includes('Delete for good'))!

    input.value = 'Goul'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(submit().disabled).toBe(true)

    input.value = 'Goulash'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    submit().click()
    await flushPromises()
    expect(deleteRecipe).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
    wrapper.unmount()
  })
})
