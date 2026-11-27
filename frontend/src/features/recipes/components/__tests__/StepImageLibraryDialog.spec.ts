import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import type { StepImageResponse } from '@/features/recipes/api/recipes'
import StepImageLibraryDialog from '@/features/recipes/components/StepImageLibraryDialog.vue'

type Query = { ingredientIds: string[]; equipmentIds: string[]; search?: string; offset?: number }
const listStepImages = vi.fn<(q: Query) => Promise<{ items: StepImageResponse[]; total: number }>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  listStepImages: (q: Query) => listStepImages(q),
}))

function image(id: string, title: string, matches: number, text = 'Chop finely.'): StepImageResponse {
  return {
    image_id: id,
    recipe: { id: `r-${id}`, title, cover_image_id: null, status: 'published' },
    step_number: 2,
    step_text: text,
    matches,
  }
}

async function open(current: string | null = null) {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(StepImageLibraryDialog, {
    props: { visible: false, ingredientIds: ['onion'], equipmentIds: ['knife'], current },
    global: { plugins: [i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

const items = () => [...document.body.querySelectorAll<HTMLButtonElement>('[data-testid="step-image-library-item"]')]

afterEach(() => {
  listStepImages.mockReset()
  document.body.innerHTML = ''
})

describe('StepImageLibraryDialog', () => {
  it('asks for photos ranked by the step and says what they share', async () => {
    listStepImages.mockResolvedValue({ items: [image('a', 'Goulash', 2), image('b', 'Soup', 0)], total: 2 })
    const wrapper = await open('b')

    expect(listStepImages).toHaveBeenCalledWith(
      expect.objectContaining({ ingredientIds: ['onion'], equipmentIds: ['knife'], search: '', offset: 0 }),
    )
    const [first, second] = items()
    expect(first!.textContent).toContain('Goulash · Step 2')
    expect(first!.textContent).toContain('shares 2 items')
    expect(second!.textContent).not.toContain('shares')
    expect(second!.getAttribute('aria-pressed')).toBe('true')
    wrapper.unmount()
  })

  it('hands the picked photo back and closes', async () => {
    listStepImages.mockResolvedValue({ items: [image('a', 'Goulash', 1)], total: 1 })
    const wrapper = await open()

    items()[0]!.click()
    await flushPromises()

    expect(wrapper.emitted('pick')).toEqual([['a']])
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
    wrapper.unmount()
  })

  it('loads the next page on demand', async () => {
    listStepImages
      .mockResolvedValueOnce({ items: [image('a', 'Goulash', 1)], total: 2 })
      .mockResolvedValueOnce({ items: [image('b', 'Soup', 0)], total: 2 })
    const wrapper = await open()

    const more = [...document.body.querySelectorAll('button')].find((b) => b.textContent?.includes('Show more'))!
    more.click()
    await flushPromises()

    expect(listStepImages).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 1 }))
    expect(items()).toHaveLength(2)
    expect(document.body.textContent).not.toContain('Show more')
    wrapper.unmount()
  })

  it('says when no step has a photo yet', async () => {
    listStepImages.mockResolvedValue({ items: [], total: 0 })
    const wrapper = await open()

    expect(document.body.querySelector('[data-testid="step-image-library-empty"]')!.textContent).toContain(
      'No step has a photo yet.',
    )
    wrapper.unmount()
  })
})
