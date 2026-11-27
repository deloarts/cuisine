<script setup lang="ts">
/**
 * The two inputs of a numeric range filter, holding one `[min, max]` value.
 * Clearing both emits null, and each bound clamps to the other so the pair
 * can never be inverted, which a server would reject. Ported from Glados.
 */
import { useI18n } from 'vue-i18n'

export type NumberRange = [number | null, number | null] | null

const props = withDefaults(
  defineProps<{
    modelValue: NumberRange
    /** Names the column in the inputs' accessible labels. */
    column: string
    /** How many decimals the inputs accept; 0 keeps them integer-only. */
    fractionDigits?: number
  }>(),
  { fractionDigits: 0 },
)
const emit = defineEmits<{ 'update:modelValue': [value: NumberRange] }>()

const { t } = useI18n()

function update(index: 0 | 1, value: number | null | undefined): void {
  const next: [number | null, number | null] = [props.modelValue?.[0] ?? null, props.modelValue?.[1] ?? null]
  next[index] = value ?? null
  emit('update:modelValue', next[0] === null && next[1] === null ? null : next)
}
</script>

<template>
  <div class="number-range">
    <InputNumber
      :model-value="modelValue?.[0] ?? null"
      :min="0"
      :max="modelValue?.[1] ?? undefined"
      :max-fraction-digits="fractionDigits"
      :use-grouping="false"
      :placeholder="t('tableFilters.min')"
      :aria-label="t('tableFilters.minOf', { column })"
      size="small"
      fluid
      class="number-range-input"
      @update:model-value="update(0, $event)"
    />
    <InputNumber
      :model-value="modelValue?.[1] ?? null"
      :min="modelValue?.[0] ?? 0"
      :max-fraction-digits="fractionDigits"
      :use-grouping="false"
      :placeholder="t('tableFilters.max')"
      :aria-label="t('tableFilters.maxOf', { column })"
      size="small"
      fluid
      class="number-range-input"
      @update:model-value="update(1, $event)"
    />
  </div>
</template>

<style scoped lang="scss">
.number-range {
  display: flex;
  gap: var(--space-1);
  min-width: 0;
}

.number-range-input {
  flex: 1 1 0;
  min-width: 0;
}
</style>
