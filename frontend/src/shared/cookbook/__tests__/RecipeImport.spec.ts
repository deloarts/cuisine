import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/core/i18n'
import { importRecipes, previewRecipeImport, type RecipeImportReport } from '@/shared/api/recipeImport'
import { pickFiles } from '@/shared/composables/fileTransfer'
import RecipeImport from '@/shared/cookbook/RecipeImport.vue'

vi.mock('@/shared/api/recipeImport', () => ({
  RECIPE_FILE_TYPES: '.cui',
  previewRecipeImport: vi.fn<(file: File) => Promise<unknown>>(),
  importRecipes: vi.fn<(file: File, update: string[]) => Promise<unknown>>(),
}))

vi.mock('@/shared/composables/fileTransfer', () => ({
  pickFiles: vi.fn<(accept: string) => Promise<File[]>>(),
}))

const file = new File(['zip'], 'tarte.cui')
const report: RecipeImportReport = {
  recipes: [{ source_id: 'src-tart', id: 'local-tart', title: 'Marillentarte', updated: true }],
  created_ingredients: [],
  created_equipment: [],
  matched_ingredients: 2,
  matched_equipment: 0,
  conflicts: [
    { kind: 'variation', name: 'Mit Honig', detail: 'Left out.', recipe: 'Marillentarte' },
  ],
}

async function mountImport() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/recipes/:id', name: 'recipe', component: { render: () => null } },
    ],
  })
  await router.push('/')
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(RecipeImport, {
    global: { plugins: [router, i18n, OpenVue, ToastService] },
  })
  await flushPromises()
  return wrapper
}

describe('RecipeImport', () => {
  it('imports at once when nothing was imported before', async () => {
    vi.mocked(pickFiles).mockResolvedValue([file])
    vi.mocked(previewRecipeImport).mockResolvedValue({
      recipes: [{ source_id: 'src-tart', title: 'Marillentarte', earlier: null }],
    })
    vi.mocked(importRecipes).mockResolvedValue(report)
    const wrapper = await mountImport()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(importRecipes).toHaveBeenCalledWith(file, [])
    expect(wrapper.text()).toContain('Marillentarte')
    expect(wrapper.text()).toContain('Variation: Mit Honig')
    expect(wrapper.emitted('imported')).toHaveLength(1)
  })

  it('asks per recipe whether to update the earlier import', async () => {
    vi.mocked(pickFiles).mockResolvedValue([file])
    vi.mocked(previewRecipeImport).mockResolvedValue({
      recipes: [
        { source_id: 'src-pastry', title: 'Mürbteig', earlier: { id: 'p', title: 'Mürbteig', status: 'draft' } },
        { source_id: 'src-tart', title: 'Marillentarte', earlier: { id: 't', title: 'Tarte', status: 'published' } },
        { source_id: 'src-new', title: 'Neu', earlier: null },
      ],
    })
    vi.mocked(importRecipes).mockResolvedValue(report)
    const wrapper = await mountImport()

    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(importRecipes).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('as Tarte (published)')
    expect(wrapper.text()).toContain('The other recipe of the file becomes a new draft.')

    await wrapper.get('#copy-src-pastry').setValue(true)
    const confirm = wrapper.findAll('button').find((b) => b.text() === 'Import')
    await confirm!.trigger('click')
    await flushPromises()

    expect(importRecipes).toHaveBeenCalledWith(file, ['src-tart'])
  })
})
