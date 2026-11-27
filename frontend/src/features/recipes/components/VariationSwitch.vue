<script setup lang="ts">
/**
 * Switches between the original recipe and each of its variations, one
 * chip per version with its rating. The chips scroll sideways on a phone.
 */
import { useI18n } from 'vue-i18n'

import type { VariationResponse } from '@/features/recipes/api/recipes'

defineProps<{ variations: VariationResponse[] }>()
/** The chosen variation's id, or null for the original. */
const model = defineModel<string | null>({ required: true })

const { t } = useI18n()
</script>

<template>
  <div class="variation-switch">
    <p id="variation-switch-label" class="variation-switch-label">
      <span class="mdi mdi-source-branch" aria-hidden="true" />
      {{ t('recipes.variations.count', { n: variations.length }, variations.length) }}
    </p>
    <div class="variation-chips" role="group" aria-labelledby="variation-switch-label">
      <button
        type="button"
        class="variation-chip"
        :class="{ 'variation-chip--on': model === null }"
        :aria-pressed="model === null"
        data-testid="version-original"
        @click="model = null"
      >
        {{ t('recipes.variations.original') }}
      </button>
      <button
        v-for="variation in variations"
        :key="variation.id"
        type="button"
        class="variation-chip"
        :class="{ 'variation-chip--on': model === variation.id }"
        :aria-pressed="model === variation.id"
        :data-testid="`version-${variation.id}`"
        @click="model = variation.id"
      >
        <span v-if="variation.private" class="mdi mdi-lock-outline" :title="t('recipes.variations.privateHint')" aria-hidden="true" />
        {{ variation.name }}
        <span v-if="variation.rating_average !== null" class="variation-chip-rating">
          <span class="mdi mdi-star" aria-hidden="true" />
          {{ variation.rating_average.toFixed(1) }}
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.variation-switch {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.variation-switch-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-text-muted-color);
  font-weight: 700;
}

.variation-chips {
  display: flex;
  gap: var(--space-2);
  margin: 0 calc(-1 * var(--space-3));
  padding: var(--space-1) var(--space-3);
  overflow-x: auto;
  scrollbar-width: none;
}

.variation-chip {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: 2rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  white-space: nowrap;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.variation-chip--on {
  border-color: var(--p-primary-color);
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.variation-chip-rating {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-sm);

  .mdi {
    color: var(--p-yellow-500);
  }
}

@media (min-width: $bp-sm) {
  .variation-chips {
    flex-wrap: wrap;
    margin: 0;
    padding: 0;
    overflow: visible;
  }
}
</style>
