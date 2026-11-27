<script setup lang="ts">
/**
 * The months an ingredient is in season in Austria, as twelve toggle
 * buttons (three rows of four on a phone, one row of twelve from the small
 * breakpoint up) with "all year" and "not seasonal" shortcuts. The value is
 * the sorted list of month numbers; an empty list means not seasonal.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatSeason, MONTHS, toggleMonth } from '@/shared/cookbook/season'

const props = withDefaults(defineProps<{ labelledby: string; disabled?: boolean }>(), { disabled: false })
const months = defineModel<number[]>({ required: true })

const { t } = useI18n()

const summary = computed(() =>
  months.value.length
    ? formatSeason(months.value, (m) => t(`ingredients.season.short.${m}`))
    : t('ingredients.season.none'),
)

function toggle(month: number) {
  if (!props.disabled) months.value = toggleMonth(months.value, month)
}
</script>

<template>
  <div class="season-picker">
    <div class="season-months" role="group" :aria-labelledby="labelledby">
      <button
        v-for="month in MONTHS"
        :key="month"
        type="button"
        class="season-month"
        :class="{ 'season-month-on': months.includes(month) }"
        :aria-pressed="months.includes(month)"
        :aria-label="t(`ingredients.season.long.${month}`)"
        :disabled="disabled"
        @click="toggle(month)"
      >
        {{ t(`ingredients.season.short.${month}`) }}
      </button>
    </div>
    <div class="season-footer">
      <span class="text-muted season-summary" aria-live="polite">{{ summary }}</span>
      <span v-if="!disabled" class="season-shortcuts">
        <Button type="button" :label="t('ingredients.season.allYear')" text size="small" @click="months = [...MONTHS]" />
        <Button type="button" :label="t('ingredients.season.clear')" text size="small" @click="months = []" />
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.season-picker {
  display: grid;
  gap: var(--space-2);
}

.season-months {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-1);
}

.season-month {
  min-height: 2.75rem;
  padding: 0 var(--space-1);
  font: inherit;
  font-size: var(--font-size-sm);
  color: var(--p-text-color);
  cursor: pointer;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
}

.season-month-on {
  font-weight: 700;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
}

.season-month:disabled {
  cursor: default;
  opacity: 0.7;
}

.season-month:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}

.season-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.season-summary {
  font-size: var(--font-size-sm);
}

@media (min-width: $bp-sm) {
  .season-months {
    grid-template-columns: repeat(12, minmax(0, 1fr));
  }
}
</style>
