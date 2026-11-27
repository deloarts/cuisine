import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '@/core/i18n'
import RecipePrintQr from '@/features/recipes/components/RecipePrintQr.vue'

const toDataURL = vi.fn<(text: string, options?: object) => Promise<string>>()

vi.mock('qrcode', () => ({
  default: { toDataURL: (text: string, options?: object) => toDataURL(text, options) },
}))

describe('RecipePrintQr', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'enGB'
    toDataURL.mockResolvedValue('data:image/png;base64,qr')
  })

  it('encodes the absolute link through the resolver route', async () => {
    const wrapper = mount(RecipePrintQr, {
      props: { publicId: 'r1' },
      global: { plugins: [i18n] },
    })
    await flushPromises()

    const url = `${window.location.origin}/r/r1`
    expect(toDataURL).toHaveBeenCalledWith(url, expect.any(Object))
    expect(wrapper.get('img').attributes('src')).toBe('data:image/png;base64,qr')
    expect(wrapper.get('img').attributes('alt')).toBe('QR code linking to this recipe')
    expect(wrapper.text()).toContain(url)
  })

  it('follows a new id and keeps the caption when drawing fails', async () => {
    const wrapper = mount(RecipePrintQr, {
      props: { publicId: 'r1' },
      global: { plugins: [i18n] },
    })
    await flushPromises()
    toDataURL.mockRejectedValue(new Error('no canvas'))
    await wrapper.setProps({ publicId: 'v2' })
    await flushPromises()

    expect(toDataURL).toHaveBeenLastCalledWith(`${window.location.origin}/r/v2`, expect.any(Object))
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('Scan to open this recipe in Cuisine')
  })
})
