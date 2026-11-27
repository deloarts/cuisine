<script setup lang="ts">
/**
 * The placeholder of a recipe page while it loads: the cover, the title with
 * the author and meta lines, a few chips and the description, then the
 * ingredient card beside the steps card from a tablet up, laid out like the
 * public recipe page so the recipe fills in without moving.
 */
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import ContentCard from '@/shared/components/ContentCard.vue'
</script>

<template>
  <SkeletonRegion class="recipe-detail-skeleton" testid="recipe-skeleton">
    <Skeleton height="auto" class="recipe-detail-skeleton-cover" />
    <div class="recipe-detail-skeleton-head">
      <Skeleton width="60%" height="2.5rem" />
      <div class="recipe-detail-skeleton-row">
        <Skeleton shape="circle" size="2rem" />
        <Skeleton width="10rem" height="0.875rem" />
      </div>
      <Skeleton width="14rem" height="0.875rem" />
      <div class="recipe-detail-skeleton-row">
        <Skeleton v-for="n in 3" :key="n" width="4.5rem" height="1.6rem" border-radius="1rem" />
      </div>
      <SkeletonLines :lines="2" />
    </div>
    <div class="recipe-detail-skeleton-columns">
      <ContentCard class="recipe-detail-skeleton-card">
        <Skeleton width="50%" height="1.5rem" />
        <Skeleton width="9rem" height="2.75rem" />
        <div v-for="n in 6" :key="n" class="recipe-detail-skeleton-line">
          <Skeleton width="3.5rem" height="0.875rem" />
          <Skeleton :width="n % 3 ? '70%' : '50%'" height="0.875rem" />
        </div>
      </ContentCard>
      <ContentCard class="recipe-detail-skeleton-card">
        <Skeleton width="35%" height="1.5rem" />
        <div v-for="n in 3" :key="n" class="recipe-detail-skeleton-step">
          <Skeleton shape="circle" size="2.25rem" />
          <SkeletonLines :lines="3" />
        </div>
      </ContentCard>
    </div>
  </SkeletonRegion>
</template>

<style scoped lang="scss">
.recipe-detail-skeleton {
  display: grid;
  gap: var(--space-4);
}

.recipe-detail-skeleton-cover {
  aspect-ratio: 16 / 9;
  max-height: 24rem;
}

.recipe-detail-skeleton-head {
  display: grid;
  gap: var(--space-2);
}

.recipe-detail-skeleton-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.recipe-detail-skeleton-columns {
  display: grid;
  gap: var(--space-4);
  align-items: start;
}

.recipe-detail-skeleton-card {
  display: grid;
  gap: var(--space-3);
}

.recipe-detail-skeleton-line {
  display: grid;
  grid-template-columns: minmax(4.5rem, auto) 1fr;
  gap: var(--space-2);
}

.recipe-detail-skeleton-step {
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  gap: var(--space-3);
}

@media (min-width: $bp-md) {
  .recipe-detail-skeleton-columns {
    grid-template-columns: minmax(16rem, 1fr) minmax(0, 2fr);
  }
}
</style>
