<script setup lang="ts">
/**
 * The placeholder of a legal page's text while it loads: a short line for
 * its publication date, then headings each followed by a paragraph.
 */
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'

withDefaults(defineProps<{ dated?: boolean; sections?: number }>(), { dated: true, sections: 3 })
</script>

<template>
  <SkeletonRegion class="legal-text-skeleton" testid="legal-skeleton">
    <Skeleton v-if="dated" width="12rem" height="0.875rem" />
    <div v-for="n in sections" :key="n" class="legal-text-skeleton-section">
      <Skeleton :width="n % 2 ? '40%' : '30%'" height="1.25rem" />
      <SkeletonLines :lines="n === 1 ? 4 : 3" />
    </div>
  </SkeletonRegion>
</template>

<style scoped lang="scss">
.legal-text-skeleton {
  display: grid;
  gap: var(--space-4);
}

.legal-text-skeleton-section {
  display: grid;
  gap: var(--space-3);
}
</style>
