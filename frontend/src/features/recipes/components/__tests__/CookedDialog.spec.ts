import { flushPromises, mount } from '@vue/test-utils'
import { AxiosError } from 'axios'
import OpenVue from 'openvue/config'
import ToastService from 'openvue/toastservice'
import { describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import CookedDialog from '@/features/recipes/components/CookedDialog.vue'

const logCookEvent = vi.fn<(...args: unknown[]) => Promise<unknown>>()

vi.mock('@/features/recipes/api/recipes', () => ({
  logCookEvent: (...args: unknown[]) => logCookEvent(...args),
}))

function conflict(code: string) {
  return new AxiosError('Conflict', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 409,
    data: { code, detail: 'conflict' },
  } as never)
}

async function open() {
  i18n.global.locale.value = 'enGB'
  const wrapper = mount(CookedDialog, {
    props: { visible: false, recipeId: 'r1', servings: 2 },
    global: { plugins: [i18n, OpenVue, ToastService] },
    attachTo: document.body,
  })
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

function saveButton() {
  return [...document.body.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Log it')!
}

describe('CookedDialog', () => {
  it('names a day that already has the recipe and keeps the dialog open', async () => {
    logCookEvent.mockRejectedValueOnce(conflict('CookEventExistsError'))
    const wrapper = await open()
    saveButton().click()
    await flushPromises()
    const message = document.body.querySelector('[data-testid="cooked-exists"]')
    expect(message?.textContent).toContain('You already logged this recipe on that day.')
    expect(wrapper.emitted('logged')).toBeUndefined()
    expect(wrapper.emitted('update:visible')).toBeUndefined()
    wrapper.unmount()
  })

  it('logs the meal and closes', async () => {
    logCookEvent.mockResolvedValueOnce({ id: 'e1' })
    const wrapper = await open()
    saveButton().click()
    await flushPromises()
    expect(wrapper.emitted('logged')).toHaveLength(1)
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
    expect(document.body.querySelector('[data-testid="cooked-exists"]')).toBeNull()
    wrapper.unmount()
  })
})
