<script setup lang="ts">
/**
 * A few lines of placeholder text. The last line of a paragraph is shorter,
 * the way real text ends, unless `widths` names every line's width.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{ lines?: number; height?: string; widths?: string[] }>(), {
  lines: 3,
  height: '0.875rem',
  widths: undefined,
})

const shown = computed(() =>
  Array.from({ length: props.lines }, (_, i) => props.widths?.[i] ?? (i === props.lines - 1 && props.lines > 1 ? '60%' : '100%')),
)
</script>

<template>
  <div class="skeleton-lines">
    <Skeleton v-for="(width, i) in shown" :key="i" :width="width" :height="props.height" />
  </div>
</template>

<style scoped lang="scss">
.skeleton-lines {
  display: grid;
  gap: var(--space-2);
}
</style>
