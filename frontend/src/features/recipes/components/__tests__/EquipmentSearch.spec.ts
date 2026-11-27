import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import EquipmentSearch from '@/features/recipes/components/EquipmentSearch.vue'
import type { EquipmentResponse } from '@/shared/cookbook/types'

function item(id: string, name: string, aliases: string[] = []): EquipmentResponse {
  return {
    id,
    name,
    locale: 'en-GB',
    available_locales: ['en-GB'],
    kind: 'utensil',
    icon: null,
    basic: false,
    status: 'active',
    seeded: true,
    aliases: { 'en-GB': aliases },
    translations: {},
    changed: '2026-11-01T00:00:00Z',
  } as EquipmentResponse
}

const catalogue = [item('e1', 'Whisk', ['Balloon whisk']), item('e2', 'Wok'), item('e3', 'Grater')]

async function mountSearch(taken: string[] = []) {
  const wrapper = mount(EquipmentSearch, {
    props: { inputId: 'eq', equipment: catalogue, taken },
    global: { plugins: [i18n, OpenVue] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

async function type(wrapper: Awaited<ReturnType<typeof mountSearch>>, text: string) {
  const input = wrapper.find('input#eq')
  ;(input.element as HTMLInputElement).value = text
  await input.trigger('input')
  // AutoComplete waits for a pause in typing before it searches.
  await new Promise((resolve) => setTimeout(resolve, 350))
  await flushPromises()
}

const offered = () => [...document.body.querySelectorAll('[role="option"]')].map((o) => o.textContent?.replace(/\s+/g, ' ').trim())

beforeEach(() => {
  i18n.global.locale.value = 'enGB'
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('EquipmentSearch', () => {
  it('finds items by name and by alias, showing the alias it matched', async () => {
    const wrapper = await mountSearch()
    await type(wrapper, 'w')
    expect(offered()).toEqual(['Whisk', 'Wok'])

    await type(wrapper, 'balloon')
    expect(offered()).toEqual(['Balloon whisk → listed as Whisk'])
    wrapper.unmount()
  })

  it('leaves out what the step already has', async () => {
    const wrapper = await mountSearch(['e1'])
    await type(wrapper, 'w')
    expect(offered()).toEqual(['Wok'])
    wrapper.unmount()
  })

  it('hands the picked item over and empties itself', async () => {
    const wrapper = await mountSearch()
    await type(wrapper, 'grat')
    ;(document.body.querySelector('[role="option"]') as HTMLElement).click()
    await flushPromises()
    expect(wrapper.emitted('select')?.[0]).toEqual([catalogue[2]])
    expect((wrapper.find('input#eq').element as HTMLInputElement).value).toBe('')
    wrapper.unmount()
  })
})
