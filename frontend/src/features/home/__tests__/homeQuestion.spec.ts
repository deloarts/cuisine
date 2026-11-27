import { afterEach, describe, expect, it, vi } from 'vitest'

import { appLoadPick, resetAppLoadPick } from '@/features/home/homeQuestion'

describe('appLoadPick', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    resetAppLoadPick()
  })

  it('draws once per app load and keeps the draw for later visits', () => {
    const random = vi.spyOn(Math, 'random').mockReturnValue(0.5)
    expect(appLoadPick(12)).toBe(6)
    random.mockReturnValue(0)
    expect(appLoadPick(12)).toBe(6)
    expect(random).toHaveBeenCalledTimes(1)
  })

  it('draws again after a new load', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.99)
    expect(appLoadPick(12)).toBe(11)
    resetAppLoadPick()
    vi.spyOn(Math, 'random').mockReturnValue(0)
    expect(appLoadPick(12)).toBe(0)
  })
})
