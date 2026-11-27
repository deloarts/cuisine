<script setup lang="ts">
/**
 * Faint steam rising behind the sign-in card, as if a pot were cooking just
 * below the screen. It is a live fluid simulation (see steamSimulation.ts)
 * and stays empty when the browser has no WebGL2 or the visitor asked for
 * reduced motion. It pauses while the tab is hidden. On a device whose
 * orientation sensor the page may read, the steam rises against real gravity.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { watchDeviceUp } from '@/app/layouts/steam/deviceUp'
import { createSteamSimulation, type SteamSimulation } from '@/app/layouts/steam/steamSimulation'

const canvas = ref<HTMLCanvasElement | null>(null)
let simulation: SteamSimulation | null = null
let observer: ResizeObserver | null = null
let stopWatchingUp: (() => void) | null = null

function onVisibilityChange() {
  if (document.hidden) simulation?.stop()
  else simulation?.start()
}

function onContextLost() {
  simulation?.stop()
  simulation = null
}

onMounted(() => {
  const element = canvas.value
  if (!element || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  try {
    simulation = createSteamSimulation(element)
  } catch {
    simulation = null
  }
  if (!simulation) return

  element.addEventListener('webglcontextlost', onContextLost)
  document.addEventListener('visibilitychange', onVisibilityChange)
  if (typeof ResizeObserver !== 'undefined') {
    let first = true
    observer = new ResizeObserver(() => {
      // The observer reports once on start; the simulation is already sized.
      if (first) {
        first = false
        return
      }
      simulation?.resize()
    })
    observer.observe(element)
  }
  stopWatchingUp = watchDeviceUp((x, y) => simulation?.setUp(x, y))
  simulation.start()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  stopWatchingUp?.()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  canvas.value?.removeEventListener('webglcontextlost', onContextLost)
  simulation?.destroy()
  simulation = null
})
</script>

<template>
  <canvas ref="canvas" class="steam-backdrop" aria-hidden="true" />
</template>

<style scoped lang="scss">
.steam-backdrop {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
