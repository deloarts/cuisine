<script setup lang="ts">
/**
 * Picks a unit by its id. The list groups the units by kind and shows each
 * one's abbreviation, full name and what it is worth in grams or millilitres;
 * typing filters by abbreviation, names and code. The chosen unit shows only
 * its abbreviation, so a narrow amount column stays readable.
 *
 * Given the line's `ingredient`, every row says how much one unit of it
 * weighs instead, and a unit it cannot be weighed in is muted with a note
 * that its amount stays out of the nutrition. Such a unit can still be
 * chosen. Other attributes (labels, placeholder, `show-clear`, `disabled`)
 * pass through to the Select.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  gramsPerUnit,
  groupUnits,
  unitBase,
  unitSearchText,
  unitShortLabel,
  type WeighableIngredient,
} from './units'
import type { UnitResponse } from './types'

const props = withDefaults(
  defineProps<{
    units: readonly UnitResponse[]
    ingredient?: WeighableIngredient | null
    ariaLabel?: string
    ariaLabelledby?: string
  }>(),
  { ingredient: null, ariaLabel: undefined, ariaLabelledby: undefined },
)
const model = defineModel<string | null>({ default: null })

const { t, locale } = useI18n()

interface UnitRow {
  id: string
  unit: UnitResponse
  /** What assistive technology reads for the row. */
  label: string
  search: string
  /** "= 10 g", "≈ 120 g", or null when there is nothing to add. */
  worth: string | null
  /** True when the line's ingredient cannot be weighed in this unit. */
  unweighed: boolean
}

// Two decimals, but small values keep three significant digits, so a
// milligram reads "= 0,001 g" and never "= 0 g".
const number = computed(() => {
  const tag = locale.value === 'deAT' ? 'de-AT' : 'en-GB'
  const regular = new Intl.NumberFormat(tag, { maximumFractionDigits: 2 })
  const small = new Intl.NumberFormat(tag, { maximumSignificantDigits: 3 })
  return { format: (n: number) => (n > 0 && n < 1 ? small : regular).format(n) }
})

function worth(unit: UnitResponse): { worth: string | null; unweighed: boolean } {
  const base = unitBase(unit)
  const baseText = base ? `= ${number.value.format(base.amount)} ${base.symbol}` : null
  if (!props.ingredient || unit.kind === 'mass') return { worth: baseText, unweighed: false }
  const grams = gramsPerUnit(unit, props.ingredient)
  if (grams === null) return { worth: null, unweighed: true }
  return { worth: t('pickers.approxGrams', { amount: number.value.format(grams) }), unweighed: false }
}

function row(unit: UnitResponse): UnitRow {
  const w = worth(unit)
  const extra = w.worth ?? (w.unweighed ? t('pickers.notWeighed') : null)
  const short = unitShortLabel(unit)
  const name = short !== unit.name ? `${short}, ${unit.name}` : unit.name
  return { id: unit.id, unit, label: extra ? `${name}, ${extra}` : name, search: unitSearchText(unit), ...w }
}

const groups = computed(() =>
  groupUnits(props.units).map((g) => ({ label: t(`unitKinds.${g.kind}`), items: g.units.map(row) })),
)
const rows = computed(() => groups.value.flatMap((g) => g.items))
const selected = computed(() => rows.value.find((r) => r.id === model.value) ?? null)
</script>

<template>
  <Select
    v-model="model"
    :options="groups"
    option-group-label="label"
    option-group-children="items"
    option-label="label"
    option-value="id"
    :filter-fields="['search']"
    :aria-label="ariaLabel"
    :aria-labelledby="ariaLabelledby"
    filter
  >
    <template #value="{ placeholder }">
      <span v-if="selected" class="unit-value">
        {{ unitShortLabel(selected.unit) }}
        <span
          v-if="selected.unweighed"
          class="mdi mdi-scale-off unit-value-warning"
          :title="t('pickers.notWeighedShort')"
          aria-hidden="true"
        />
        <span v-if="selected.unweighed" class="visually-hidden">{{ t('pickers.notWeighedShort') }}</span>
      </span>
      <span v-else>{{ placeholder || ' ' }}</span>
    </template>
    <template #optiongroup="{ option }">
      <span class="unit-group">{{ option.label }}</span>
    </template>
    <template #option="{ option }">
      <span class="unit-option" :class="{ 'unit-option--muted': option.unweighed }">
        <strong class="unit-option-abbr">{{ unitShortLabel(option.unit) }}</strong>
        <span class="unit-option-name">{{ option.unit.name }}</span>
        <small v-if="option.worth" class="unit-option-worth">{{ option.worth }}</small>
        <small v-else-if="option.unweighed" class="unit-option-worth">{{ t('pickers.notWeighed') }}</small>
      </span>
    </template>
  </Select>
</template>

<style scoped lang="scss">
.unit-value {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.unit-value-warning {
  color: var(--p-orange-500);
}

.unit-group {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.unit-option {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: baseline;
  width: 100%;
}

.unit-option--muted {
  color: var(--p-text-muted-color);
}

.unit-option-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unit-option-worth {
  color: var(--p-text-muted-color);
  text-align: right;
}
</style>
