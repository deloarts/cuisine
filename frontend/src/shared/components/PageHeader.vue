<script setup lang="ts">
/**
 * A page's title with its actions at the end. The `title-end` slot sits right
 * after the title, for a tag that belongs to it. A `sticky` header stays at
 * the top of the main area while the page scrolls, for editors whose save
 * actions must stay in reach on a long form.
 */
defineProps<{ title: string; sticky?: boolean }>()
</script>

<template>
  <div class="page-header" :class="{ 'page-header-sticky': sticky }">
    <div class="page-title">
      <h1>{{ title }}</h1>
      <slot name="title-end" />
    </div>
    <div class="page-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;

  h1 {
    font-size: var(--font-size-3xl);
  }
}

.page-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

// The header sticks at the main area's edge, above the shell's padding, and
// carries the shell's background so the page scrolls away under it.
.page-header-sticky {
  position: sticky;
  top: calc(-1 * var(--shell-pad-y, 0px));
  z-index: 2;
  margin-top: calc(-1 * var(--shell-pad-y, 0px));
  padding-block: var(--shell-pad-y, 0px) var(--space-2);
  background: var(--p-surface-50);
}

:global(.p-dark) .page-header-sticky {
  background: var(--p-surface-950);
}

.page-actions {
  display: flex;
  gap: var(--space-2);
}
</style>
