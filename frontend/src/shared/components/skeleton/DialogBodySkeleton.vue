<script setup lang="ts">
/**
 * What a dialog shows while it asks the server what an action would touch:
 * a few lines of text and its row of buttons, so the dialog opens at about
 * its final size and does not jump when the answer arrives.
 */
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'

withDefaults(defineProps<{ lines?: number; actions?: number; label?: string }>(), {
  lines: 2,
  actions: 2,
  label: undefined,
})
</script>

<template>
  <SkeletonRegion class="dialog-body-skeleton" :label="label" testid="dialog-skeleton">
    <SkeletonLines :lines="lines" />
    <div class="dialog-body-skeleton-actions">
      <Skeleton v-for="n in actions" :key="n" width="6rem" height="2.5rem" />
    </div>
  </SkeletonRegion>
</template>

<style scoped lang="scss">
.dialog-body-skeleton {
  display: grid;
  gap: var(--space-4);
}

.dialog-body-skeleton-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
