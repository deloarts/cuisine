<script setup lang="ts">
/**
 * One filter of the ingredient table. The table puts each into its column's
 * filter row; on a phone, where the table shows a single column, the same
 * controls stack in the filter panel above it.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import type { NumberRange } from '@/shared/components/table-filters/NumberRangeRowFilter.vue'
import { ALLERGENS } from '@/shared/cookbook/allergens'
import { DIET_MARKERS } from '@/shared/cookbook/diets'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import type { IngredientFilters } from '@/features/ingredients/ingredientFilters'

export type IngredientFilterField =
  | 'q'
  | 'category'
  | 'family'
  | 'status'
  | 'mine'
  | 'allergens'
  | 'diets'
  | 'season'
  | 'kcal'
  | 'usage'

const props = defineProps<{ field: IngredientFilterField; label: string }>()
const filters = defineModel<IngredientFilters>({ required: true })

const { t } = useI18n()
const resources = useCookbookResources()

const statusOptions = computed(() => [
  { value: 'active', label: t('ingredients.status.active') },
  { value: 'draft', label: t('ingredients.status.draft') },
])
const ownerOptions = computed(() => [
  { value: false, label: t('ingredients.filters.everyone') },
  { value: true, label: t('ingredients.filters.mine') },
])
const allergenOptions = computed(() => ALLERGENS.map((a) => ({ value: a, label: t(`allergens.${a}`) })))
const dietOptions = computed(() => DIET_MARKERS.map((m) => ({ value: m, label: t(`dietMarkers.${m}`) })))
const monthOptions = computed(() =>
  Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: t(`ingredients.season.long.${i + 1}`) })),
)

const kcal = computed<NumberRange>({
  get: (): NumberRange =>
    filters.value.kcalMin === null && filters.value.kcalMax === null
      ? null
      : [filters.value.kcalMin, filters.value.kcalMax],
  set: (value: NumberRange) => {
    filters.value.kcalMin = value?.[0] ?? null
    filters.value.kcalMax = value?.[1] ?? null
  },
})
const usage = computed<NumberRange>({
  get: (): NumberRange =>
    filters.value.usageMin === null && filters.value.usageMax === null
      ? null
      : [filters.value.usageMin, filters.value.usageMax],
  set: (value: NumberRange) => {
    filters.value.usageMin = value?.[0] ?? null
    filters.value.usageMax = value?.[1] ?? null
  },
})
const aria = computed(() => t('tableFilters.filterBy', { column: props.label }))
</script>

<template>
  <InputText
    v-if="field === 'q'"
    v-model="filters.q"
    :placeholder="t('ingredients.filters.search')"
    :aria-label="aria"
    size="small"
    fluid
  />
  <Select
    v-else-if="field === 'category'"
    v-model="filters.category"
    :options="resources.categories.value"
    option-label="name"
    option-value="id"
    :placeholder="t('tableFilters.all')"
    :aria-label="aria"
    show-clear
    size="small"
    fluid
  />
  <Select
    v-else-if="field === 'family'"
    v-model="filters.family"
    :options="resources.families.value"
    option-label="name"
    option-value="id"
    :placeholder="t('tableFilters.all')"
    :aria-label="aria"
    show-clear
    filter
    size="small"
    fluid
  />
  <Select
    v-else-if="field === 'status'"
    v-model="filters.status"
    :options="statusOptions"
    option-label="label"
    option-value="value"
    :placeholder="t('tableFilters.all')"
    :aria-label="aria"
    show-clear
    size="small"
    fluid
  />
  <Select
    v-else-if="field === 'mine'"
    v-model="filters.mine"
    :options="ownerOptions"
    option-label="label"
    option-value="value"
    :aria-label="aria"
    size="small"
    fluid
  />
  <MultiSelect
    v-else-if="field === 'allergens'"
    v-model="filters.allergens"
    :options="allergenOptions"
    option-label="label"
    option-value="value"
    :placeholder="t('tableFilters.any')"
    :aria-label="aria"
    :max-selected-labels="1"
    size="small"
    fluid
  />
  <MultiSelect
    v-else-if="field === 'diets'"
    v-model="filters.diets"
    :options="dietOptions"
    option-label="label"
    option-value="value"
    :placeholder="t('tableFilters.any')"
    :aria-label="aria"
    :max-selected-labels="1"
    size="small"
    fluid
  />
  <MultiSelect
    v-else-if="field === 'season'"
    v-model="filters.season"
    :options="monthOptions"
    option-label="label"
    option-value="value"
    :placeholder="t('tableFilters.any')"
    :aria-label="aria"
    :max-selected-labels="2"
    size="small"
    fluid
  />
  <NumberRangeFilter v-else-if="field === 'kcal'" v-model="kcal" :column="label" unit="kcal" />
  <NumberRangeFilter v-else-if="field === 'usage'" v-model="usage" :column="label" />
</template>
