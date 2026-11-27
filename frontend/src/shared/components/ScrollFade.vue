<script setup lang="ts">
/**
 * A box whose content scrolls when its parent gives it less room than the
 * content needs. While more content lies below, its foot fades out, and the
 * scrollbar stays hidden except while the reader scrolls, so a short text
 * looks exactly as it would without the box.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const box = ref<HTMLElement | null>(null)
const more = ref(false)
const scrolling = ref(false)
let idle: ReturnType<typeof setTimeout> | undefined
let observer: ResizeObserver | undefined

function measure() {
  const el = box.value
  if (!el) return
  more.value = el.scrollTop + el.clientHeight < el.scrollHeight - 1
}

function onScroll() {
  measure()
  scrolling.value = true
  clearTimeout(idle)
  idle = setTimeout(() => (scrolling.value = false), 800)
}

onMounted(() => {
  measure()
  if (typeof ResizeObserver === 'undefined' || !box.value) return
  observer = new ResizeObserver(measure)
  observer.observe(box.value)
  for (const child of Array.from(box.value.children)) observer.observe(child)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(idle)
})
</script>

<template>
  <div
    ref="box"
    class="scroll-fade"
    :class="{ 'scroll-fade--more': more, 'scroll-fade--scrolling': scrolling }"
    data-testid="scroll-fade"
    @scroll.passive="onScroll"
  >
    <slot />
  </div>
</template>

<style scoped lang="scss">
// The scrollbar keeps its width at all times and only its thumb shows while
// the reader scrolls, so the text never reflows when it appears. Scrolling
// past either end, or over a box that has nothing to scroll, moves the page,
// so a swipe that starts on the text never gets stuck on a phone.
.scroll-fade {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: transparent;
  }
}

.scroll-fade--more {
  mask-image: linear-gradient(to bottom, black calc(100% - 3rem), transparent);
}

.scroll-fade--scrolling {
  scrollbar-color: var(--p-content-border-color) transparent;

  &::-webkit-scrollbar-thumb {
    background: var(--p-content-border-color);
  }
}
</style>
