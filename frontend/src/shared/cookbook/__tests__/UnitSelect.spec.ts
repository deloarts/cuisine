import { flushPromises, mount } from '@vue/test-utils'
import OpenVue from 'openvue/config'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import type { UnitResponse } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'

function unit(code: string, kind: string, toBase: number | null, sortOrder: number, name: string): UnitResponse {
  return {
    id: `u-${code}`,
    seeded: true,
    code,
    kind,
    to_base: toBase,
    sort_order: sortOrder,
    name,
    plural_name: name,
    abbreviation: code,
    translations: {},
  } as UnitResponse
}

const units = [
  unit('g', 'mass', 1, 10, 'Gram'),
  unit('dag', 'mass', 10, 20, 'Decagram'),
  unit('cl', 'volume', 10, 30, 'Centilitre'),
  unit('pc', 'count', null, 40, 'Piece'),
]

async function openSelect(props: Record<string, unknown> = {}) {
  const wrapper = mount(UnitSelect, {
    props: { units, ariaLabel: 'Unit', ...props },
    global: { plugins: [i18n, OpenVue] },
    attachTo: document.body,
  })
  await wrapper.find('[role="combobox"]').trigger('click')
  await flushPromises()
  return wrapper
}

// What assistive technology reads for each entry of the open list: an option's
// label, or a group heading's text.
const rows = () =>
  [...document.body.querySelectorAll('[role="option"]')].map((o) => o.getAttribute('aria-label') ?? o.textContent?.trim())

beforeEach(() => {
  i18n.global.locale.value = 'enGB'
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('UnitSelect', () => {
  it('groups units by kind and shows what each is worth in the base unit', async () => {
    const wrapper = await openSelect()
    expect(rows()).toEqual([
      'Weight',
      'g, Gram',
      'dag, Decagram, = 10 g',
      'Volume',
      'cl, Centilitre, = 10 ml',
      'Count',
      'pc, Piece',
    ])
    wrapper.unmount()
  })

  it('weighs each unit for the line\'s ingredient and mutes the ones it cannot weigh', async () => {
    const wrapper = await openSelect({
      ingredient: {
        density_g_per_ml: null,
        conversions: [{ unit_id: 'u-pc', unit_code: 'pc', unit_name: 'Piece', grams: 55 }],
      },
    })
    expect(rows()).toEqual([
      'Weight',
      'g, Gram',
      'dag, Decagram, = 10 g',
      'Volume',
      'cl, Centilitre, no weight, not in the nutrition',
      'Count',
      'pc, Piece, ≈ 55 g',
    ])
    wrapper.unmount()
  })

  it('shows only the abbreviation of the chosen unit, with a warning when it cannot be weighed', async () => {
    const wrapper = mount(UnitSelect, {
      props: { units, modelValue: 'u-cl', ariaLabel: 'Unit', ingredient: { density_g_per_ml: null, conversions: [] } },
      global: { plugins: [i18n, OpenVue] },
    })
    const value = wrapper.find('[role="combobox"]').text()
    expect(value).toContain('cl')
    expect(value).not.toContain('Centilitre')
    expect(value).toContain('Not counted in the nutrition')
  })
})
