<script setup lang="ts">
/**
 * The row filter of a numeric column: one small field sums up the range
 * that is set and opens a panel with the minimum and maximum inputs, so a
 * narrow column keeps one readable field instead of two cramped ones.
 * Ported from Glados.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberRangeRowFilter, { type NumberRange } from './NumberRangeRowFilter.vue'

const props = withDefaults(
  defineProps<{
    modelValue: NumberRange
    column: string
    fractionDigits?: number
    /** Shown after the numbers of the summary, such as "kcal". */
    unit?: string
  }>(),
  { fractionDigits: 0, unit: undefined },
)
const emit = defineEmits<{ 'update:modelValue': [value: NumberRange] }>()

const { t, locale } = useI18n()
const popover = ref<{ toggle: (event: Event) => void } | null>(null)

function format(value: number): string {
  const number = new Intl.NumberFormat(locale.value === 'deAT' ? 'de-AT' : 'en-GB', {
    maximumFractionDigits: props.fractionDigits,
    useGrouping: false,
  }).format(value)
  return props.unit ? `${number} ${props.unit}` : number
}

const summary = computed(() => {
  const min = props.modelValue?.[0] ?? null
  const max = props.modelValue?.[1] ?? null
  if (min !== null && max !== null) {
    return min === max ? format(min) : t('tableFilters.between', { min: format(min), max: format(max) })
  }
  if (min !== null) return t('tableFilters.atLeast', { min: format(min) })
  if (max !== null) return t('tableFilters.atMost', { max: format(max) })
  return ''
})

function toggle(event: Event): void {
  popover.value?.toggle(event)
}
</script>

<template>
  <div class="number-range-filter">
    <IconField>
      <InputText
        :model-value="summary"
        readonly
        :placeholder="t('tableFilters.any')"
        :aria-label="t('tableFilters.filterBy', { column })"
        aria-haspopup="dialog"
        size="small"
        fluid
        class="number-range-filter-field"
        @click="toggle"
        @keydown.enter.prevent="toggle"
        @keydown.space.prevent="toggle"
      />
      <InputIcon
        v-if="summary"
        class="mdi mdi-close number-range-filter-clear"
        role="button"
        tabindex="0"
        :aria-label="t('tableFilters.clear')"
        @click.stop="emit('update:modelValue', null)"
        @keydown.enter.prevent="emit('update:modelValue', null)"
      />
    </IconField>
    <Popover ref="popover">
      <div class="number-range-filter-panel">
        <span class="number-range-filter-label">{{ column }}</span>
        <NumberRangeRowFilter
          :model-value="modelValue"
          :column="column"
          :fraction-digits="fractionDigits"
          @update:model-value="emit('update:modelValue', $event)"
        />
      </div>
    </Popover>
  </div>
</template>

<style scoped lang="scss">
.number-range-filter {
  min-width: 0;
}

.number-range-filter-field {
  cursor: pointer;
  text-overflow: ellipsis;
}

.number-range-filter-clear {
  cursor: pointer;
}

.number-range-filter-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 16rem;
}

.number-range-filter-label {
  font-size: var(--font-size-sm);
}
</style>
