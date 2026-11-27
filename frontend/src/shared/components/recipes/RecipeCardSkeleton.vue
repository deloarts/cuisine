<script setup lang="ts">
/**
 * The placeholder of a recipe card: the same frame, the 4:3 cover, the
 * title, two lines of description, the meta line and either the tags or
 * the author, so a grid of cards keeps its rows while the recipes load.
 * It narrows the same way as `RecipeCard` in a slim column.
 */
withDefaults(defineProps<{ author?: boolean }>(), { author: false })
</script>

<template>
  <div class="recipe-card-skeleton">
    <div class="recipe-card-skeleton-frame">
      <Skeleton height="auto" border-radius="0" class="recipe-card-skeleton-cover" />
      <div class="recipe-card-skeleton-body">
        <Skeleton width="75%" height="1.5rem" />
        <div class="recipe-card-skeleton-description">
          <Skeleton height="0.75rem" />
          <Skeleton width="70%" height="0.75rem" />
        </div>
        <Skeleton width="50%" height="0.75rem" />
        <div v-if="author" class="recipe-card-skeleton-author">
          <Skeleton shape="circle" size="1.4rem" />
          <Skeleton width="40%" height="0.75rem" />
        </div>
        <div v-else class="recipe-card-skeleton-tags">
          <Skeleton width="3.5rem" height="1.2rem" border-radius="1rem" />
          <Skeleton width="4.5rem" height="1.2rem" border-radius="1rem" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.recipe-card-skeleton {
  container-type: inline-size;
  height: 100%;
}

.recipe-card-skeleton-frame {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  box-shadow: var(--shadow-md);
}

.recipe-card-skeleton-cover {
  aspect-ratio: 4 / 3;
}

.recipe-card-skeleton-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
}

.recipe-card-skeleton-description {
  display: grid;
  gap: var(--space-1);
}

.recipe-card-skeleton-author,
.recipe-card-skeleton-tags {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

@container (width < 13rem) {
  .recipe-card-skeleton-description,
  .recipe-card-skeleton-tags {
    display: none;
  }

  .recipe-card-skeleton-body {
    padding: var(--space-2);
  }
}
</style>
