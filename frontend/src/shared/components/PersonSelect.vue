<script setup lang="ts">
/**
 * Picks one person by id from a list the caller loads, each shown with their
 * avatar in the list and in the chosen value. Other attributes (labels,
 * placeholder, `filter`, `show-clear`, `size`) pass through to the Select.
 */
import { computed } from 'vue'

import PersonOption from '@/shared/components/PersonOption.vue'

/** What the select needs of a person. */
interface SelectablePerson {
  id: string
  display_name: string
  avatar_id?: string | null
}

const props = defineProps<{
  people: readonly SelectablePerson[]
  ariaLabel?: string
  ariaLabelledby?: string
}>()
const model = defineModel<string | null>({ default: null })

const selected = computed(() => props.people.find((p) => p.id === model.value) ?? null)
</script>

<template>
  <Select
    v-model="model"
    :options="[...people]"
    option-label="display_name"
    option-value="id"
    :aria-label="ariaLabel"
    :aria-labelledby="ariaLabelledby"
  >
    <template #value="{ placeholder }">
      <PersonOption v-if="selected" :name="selected.display_name" :avatar-id="selected.avatar_id" size="small" />
      <span v-else>{{ placeholder || ' ' }}</span>
    </template>
    <template #option="{ option }">
      <PersonOption :name="option.display_name" :avatar-id="option.avatar_id" />
    </template>
  </Select>
</template>
