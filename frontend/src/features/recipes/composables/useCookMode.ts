/**
 * Step navigation for cook mode, shared by both layouts: `index` is the
 * current step, the one step mode shows and flow mode highlights. There is no
 * screen after the last step; finishing leaves cook mode.
 */
import { computed, ref, watch, type Ref } from 'vue'

export function useCookMode(stepCount: Ref<number>) {
  const index = ref(0)

  const isFirst = computed(() => index.value === 0)
  const isLast = computed(() => index.value >= stepCount.value - 1)
  const progress = computed(() =>
    stepCount.value === 0 ? 1 : Math.min((index.value + 1) / stepCount.value, 1),
  )

  function goTo(target: number) {
    index.value = Math.max(0, Math.min(target, stepCount.value - 1))
  }

  const next = () => goTo(index.value + 1)
  const prev = () => goTo(index.value - 1)

  // A recipe that loads after the view mounted starts on its first step.
  watch(stepCount, () => goTo(index.value))

  return { index, isFirst, isLast, progress, next, prev, goTo }
}

/**
 * A countdown for a step with a duration. It counts in whole seconds from
 * the moment it starts, so a tab in the background still finishes on time.
 */
export function useStepTimer(onDone: () => void) {
  const total = ref(0)
  const remaining = ref(0)
  const running = ref(false)
  let endsAt = 0
  let handle: ReturnType<typeof setInterval> | null = null

  function clear() {
    if (handle !== null) clearInterval(handle)
    handle = null
  }

  function tick() {
    remaining.value = Math.max(0, Math.round((endsAt - Date.now()) / 1000))
    if (remaining.value === 0) {
      clear()
      running.value = false
      onDone()
    }
  }

  function start(minutes?: number) {
    if (minutes !== undefined) {
      total.value = minutes * 60
      remaining.value = total.value
    }
    if (remaining.value <= 0) return
    endsAt = Date.now() + remaining.value * 1000
    running.value = true
    clear()
    handle = setInterval(tick, 250)
  }

  function pause() {
    tick()
    clear()
    running.value = false
  }

  function reset() {
    clear()
    running.value = false
    total.value = 0
    remaining.value = 0
  }

  return { total, remaining, running, start, pause, reset, stop: clear }
}
