import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { useCookMode, useStepTimer } from '@/features/recipes/composables/useCookMode'

describe('useCookMode', () => {
  it('walks the steps and ends on the finish screen', () => {
    const mode = useCookMode(ref(3))
    expect(mode.isFirst.value).toBe(true)
    mode.next()
    mode.next()
    expect(mode.index.value).toBe(2)
    expect(mode.isFinish.value).toBe(false)
    mode.next()
    expect(mode.isFinish.value).toBe(true)
    expect(mode.progress.value).toBe(1)
  })

  it('never leaves the range of screens', () => {
    const mode = useCookMode(ref(2))
    mode.prev()
    expect(mode.index.value).toBe(0)
    mode.goTo(10)
    expect(mode.index.value).toBe(2)
    mode.goTo(-4)
    expect(mode.index.value).toBe(0)
  })

  it('reports progress as the share of steps done', () => {
    const mode = useCookMode(ref(4))
    mode.next()
    expect(mode.progress.value).toBe(0.25)
  })
})

describe('useStepTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('counts down and calls back when the time is up', () => {
    const done = vi.fn<() => void>()
    const timer = useStepTimer(done)
    timer.start(1)
    expect(timer.remaining.value).toBe(60)
    vi.advanceTimersByTime(30_000)
    expect(timer.remaining.value).toBe(30)
    vi.advanceTimersByTime(30_000)
    expect(timer.remaining.value).toBe(0)
    expect(timer.running.value).toBe(false)
    expect(done).toHaveBeenCalledTimes(1)
  })

  it('pauses and resumes where it stopped', () => {
    const timer = useStepTimer(vi.fn<() => void>())
    timer.start(2)
    vi.advanceTimersByTime(20_000)
    timer.pause()
    vi.advanceTimersByTime(60_000)
    expect(timer.remaining.value).toBe(100)
    timer.start()
    vi.advanceTimersByTime(10_000)
    expect(timer.remaining.value).toBe(90)
    timer.reset()
    expect(timer.remaining.value).toBe(0)
  })
})
