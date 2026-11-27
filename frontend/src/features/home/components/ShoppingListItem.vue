<script setup lang="ts">
/** One shopping list on the home page: its name, what is still to buy and whether it is the household's list. */
import { useI18n } from 'vue-i18n'

import type { ShoppingListSummary } from '@/features/home/api/home'

defineProps<{ list: ShoppingListSummary; household?: boolean }>()
const { t } = useI18n()
</script>

<template>
  <RouterLink
    :to="{ name: 'shopping-list', params: { id: list.id } }"
    class="shopping-item"
    :data-testid="`home-shopping-${list.id}`"
  >
    <span class="shopping-item-icon mdi mdi-cart-outline" aria-hidden="true" />
    <span class="shopping-item-text">
      <span class="shopping-item-title">{{ list.name }}</span>
      <span class="shopping-item-meta">
        {{ t('home.sections.shoppingOpen', { n: list.open_count }, list.open_count) }}
      </span>
    </span>
    <Tag v-if="household" :value="t('shopping.householdList')" severity="secondary" class="shopping-item-tag" />
  </RouterLink>
</template>

<style scoped lang="scss">
.shopping-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 3.5rem;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-md);
  color: inherit;
  text-decoration: none;
}

.shopping-item:hover,
.shopping-item:focus-visible {
  background: var(--p-content-hover-background);
}

.shopping-item-icon {
  display: grid;
  flex: 0 0 3.25rem;
  place-items: center;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
}

.p-dark .shopping-item-icon {
  background: var(--p-surface-800);
}

.shopping-item-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.shopping-item-title {
  overflow: hidden;
  font-weight: 700;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.shopping-item-meta {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.shopping-item-tag {
  flex: 0 0 auto;
}
</style>
