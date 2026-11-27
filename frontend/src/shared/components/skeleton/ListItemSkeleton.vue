<script setup lang="ts">
/**
 * The placeholder of one list row: an optional picture or avatar, a bold
 * first line with lighter lines under it, and an optional round button at
 * the end, so a list of rows keeps its height while it loads.
 */
withDefaults(
  defineProps<{
    thumb?: string
    round?: boolean
    lines?: number
    action?: boolean
  }>(),
  { thumb: undefined, round: false, lines: 2, action: false },
)
</script>

<template>
  <div class="list-item-skeleton">
    <Skeleton
      v-if="thumb"
      :size="thumb"
      :shape="round ? 'circle' : 'rectangle'"
      class="list-item-skeleton-thumb"
    />
    <div class="list-item-skeleton-text">
      <Skeleton width="65%" height="1rem" />
      <Skeleton v-for="n in lines - 1" :key="n" :width="n % 2 ? '40%' : '55%'" height="0.75rem" />
    </div>
    <Skeleton v-if="action" shape="circle" size="2.5rem" class="list-item-skeleton-thumb" />
  </div>
</template>

<style scoped lang="scss">
.list-item-skeleton {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  min-width: 0;
}

.list-item-skeleton-thumb {
  flex: 0 0 auto;
}

.list-item-skeleton-text {
  display: grid;
  flex: 1 1 auto;
  gap: var(--space-2);
  min-width: 0;
}
</style>
