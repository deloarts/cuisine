import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import SteamBackdrop from '@/app/layouts/SteamBackdrop.vue'

describe('SteamBackdrop', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('leaves the canvas empty when the browser has no WebGL2', () => {
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
    const wrapper = mount(SteamBackdrop)

    expect(wrapper.find('canvas').attributes('aria-hidden')).toBe('true')
    expect(getContext).toHaveBeenCalledWith('webgl2', expect.anything())
    wrapper.unmount()
  })

  it('does not start the simulation when reduced motion is asked for', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
    mount(SteamBackdrop)

    expect(getContext).not.toHaveBeenCalled()
  })
})
