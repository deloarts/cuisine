<script setup lang="ts">
/**
 * What a shopping list shows until it has loaded: the toolbar, the bar that
 * adds an item and two category groups of item rows, spaced like the real
 * list so it fills in without moving.
 */
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import ContentCard from '@/shared/components/ContentCard.vue'
</script>

<template>
  <SkeletonRegion testid="shopping-list-skeleton">
    <div class="shopping-list-skeleton-toolbar">
      <Skeleton width="9rem" height="2.75rem" />
      <Skeleton width="12rem" height="2.75rem" />
    </div>
    <ContentCard class="shopping-list-skeleton-add">
      <Skeleton height="2.75rem" />
    </ContentCard>
    <div v-for="g in 2" :key="g" class="shopping-list-skeleton-group">
      <Skeleton width="7rem" height="1rem" class="shopping-list-skeleton-title" />
      <ContentCard as="ul" class="shopping-list-skeleton-items">
        <li v-for="n in g === 1 ? 4 : 2" :key="n" class="shopping-list-skeleton-item">
          <Skeleton shape="circle" size="1.5rem" />
          <span class="shopping-list-skeleton-text">
            <Skeleton :width="n % 2 ? '50%' : '35%'" height="1rem" />
            <Skeleton width="25%" height="0.75rem" />
          </span>
        </li>
      </ContentCard>
    </div>
  </SkeletonRegion>
</template>

<style scoped lang="scss">
.shopping-list-skeleton-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.shopping-list-skeleton-add,
.shopping-list-skeleton-group {
  margin-bottom: var(--space-4);
}

.shopping-list-skeleton-title {
  margin-bottom: var(--space-2);
}

.shopping-list-skeleton-items {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

.shopping-list-skeleton-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 3rem;
  padding: var(--space-2) var(--space-1);
  border-bottom: 1px solid var(--p-content-border-color);

  &:last-child {
    border-bottom: 0;
  }
}

.shopping-list-skeleton-text {
  display: grid;
  flex: 1;
  gap: var(--space-1);
}
</style>
