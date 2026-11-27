<script setup lang="ts">
/**
 * Nutrition per serving, with a note when some ingredients could not be
 * counted. The vitamins, minerals and other extended nutrients sit in a
 * collapsed "More nutrients" list; an amount that misses data for some
 * ingredients is marked, because the real value is higher.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { contentLocaleOf } from '@/shared/cookbook/contentLocale'

import type { RecipeDetailResponse } from '@/features/recipes/api/recipes'
import { extendedRows } from '@/features/recipes/utils/nutrients'

// Only what both the recipe page and the public page carry.
const props = defineProps<{
  nutrition: Pick<RecipeDetailResponse['nutrition'], 'per_serving' | 'complete' | 'extended'>
}>()
const { t, te, locale } = useI18n()
const moreOpen = ref(false)

const more = computed(() =>
  extendedRows(props.nutrition.extended ?? [], contentLocaleOf(locale.value), (key) =>
    te(`nutrients.${key}`) ? t(`nutrients.${key}`) : key,
  ),
)
const moreIncomplete = computed(() => more.value.some((row) => !row.complete))

const ROWS = [
  ['kcal', 'kcal', ''],
  ['protein', 'protein', 'g'],
  ['fat', 'fat', 'g'],
  ['saturated_fat', 'saturatedFat', 'g'],
  ['carbohydrates', 'carbohydrates', 'g'],
  ['sugar', 'sugar', 'g'],
  ['fibre', 'fibre', 'g'],
  ['salt', 'salt', 'g'],
] as const

const rows = computed(() =>
  ROWS.map(([field, label, unit]) => {
    const value = props.nutrition.per_serving[field]
    return {
      field,
      label: t(`recipes.nutrition.${label}`),
      value:
        value === null || value === undefined
          ? '–'
          : `${new Intl.NumberFormat(contentLocaleOf(locale.value), {
              maximumFractionDigits: field === 'kcal' ? 0 : 1,
            }).format(value)}${unit ? ` ${unit}` : ''}`,
    }
  }),
)
const hasAny = computed(() =>
  Object.values(props.nutrition.per_serving).some((v) => v !== null && v !== undefined),
)
</script>

<template>
  <div class="nutrition">
    <template v-if="hasAny">
      <dl class="nutrition-grid">
        <div v-for="row in rows" :key="row.field" class="nutrition-row">
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
      <p v-if="!nutrition.complete" class="hint">
        <span class="mdi mdi-information-outline" aria-hidden="true" />
        {{ t('recipes.nutrition.incomplete') }}
      </p>
    </template>
    <p v-else class="hint">{{ t('recipes.nutrition.none') }}</p>
    <div v-if="more.length" class="nutrition-more">
      <button
        type="button"
        class="nutrition-more-toggle"
        :aria-expanded="moreOpen"
        aria-controls="nutrition-more-list"
        @click="moreOpen = !moreOpen"
      >
        <span class="mdi" :class="moreOpen ? 'mdi-chevron-up' : 'mdi-chevron-down'" aria-hidden="true" />
        {{ t('recipes.nutrition.more', { n: more.length }) }}
      </button>
      <div v-show="moreOpen" id="nutrition-more-list">
        <dl class="nutrition-grid">
          <div v-for="row in more" :key="row.key" class="nutrition-row" :data-testid="`nutrient-${row.key}`">
            <dt>{{ row.label }}</dt>
            <dd>
              <span v-if="!row.complete" class="nutrition-partial" :title="t('recipes.nutrition.atLeast')">
                <span aria-hidden="true">≥ </span>
                <span class="visually-hidden">{{ t('recipes.nutrition.atLeast') }}</span>
              </span>
              {{ row.value }}
            </dd>
          </div>
        </dl>
        <p v-if="moreIncomplete" class="hint">
          <span class="mdi mdi-information-outline" aria-hidden="true" />
          {{ t('recipes.nutrition.moreIncomplete') }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2) var(--space-4);
  margin: 0;
}

.nutrition-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
  border-bottom: 1px dashed var(--p-content-border-color);

  dt {
    min-width: 0;
    color: var(--p-text-muted-color);
  }

  // The amount keeps its unit on its line; the label wraps instead.
  dd {
    flex-shrink: 0;
    margin: 0;
    white-space: nowrap;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
}

.hint {
  margin-top: var(--space-3);
}

.nutrition-more {
  margin-top: var(--space-3);
}

.nutrition-more-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  margin-bottom: var(--space-2);
  padding: 0;
  border: none;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-weight: 700;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.nutrition-partial {
  color: var(--p-text-muted-color);
  font-weight: 400;
}
// On paper the toggle has nothing to do; the extra nutrients print when
// they are open on screen.
@media print {
  .nutrition-more-toggle {
    display: none;
  }
}
</style>
