<script setup lang="ts">
/**
 * Adds an equipment item to a step, the same way `IngredientSearch` adds a
 * line: type part of its name or one of its aliases and pick it, and the
 * input empties itself for the next one. The dropdown button lists the whole
 * catalogue. Items the step already has are left out.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { matchEquipment } from '@/features/recipes/utils/equipment'
import EquipmentOption from '@/shared/cookbook/EquipmentOption.vue'
import type { EquipmentResponse } from '@/shared/cookbook/types'

const props = withDefaults(
  defineProps<{ inputId: string; equipment: readonly EquipmentResponse[]; taken?: readonly string[] }>(),
  { taken: () => [] },
)
const emit = defineEmits<{ select: [item: EquipmentResponse] }>()

const { t } = useI18n()

interface Suggestion {
  item: EquipmentResponse
  name: string
  alias: string | null
}

const query = ref<string | Suggestion>('')
const suggestions = ref<Suggestion[]>([])

const offered = computed(() => {
  const taken = new Set(props.taken)
  return props.equipment.filter((item) => !taken.has(item.id))
})

function complete(event: { query: string }) {
  const byId = new Map(offered.value.map((item) => [item.id, item]))
  suggestions.value = matchEquipment(offered.value, event.query, offered.value.length).flatMap((ref) => {
    const item = byId.get(ref.id)
    return item ? [{ item, name: item.name, alias: ref.alias ?? null }] : []
  })
}

function chosen(event: { value: Suggestion }) {
  query.value = ''
  emit('select', event.value.item)
}
</script>

<template>
  <AutoComplete
    v-model="query"
    :input-id="inputId"
    :suggestions="suggestions"
    option-label="name"
    :placeholder="t('recipes.equipment.add')"
    :empty-search-message="t('recipes.equipment.none')"
    dropdown
    fluid
    @complete="complete"
    @option-select="chosen"
  >
    <template #option="{ option }">
      <EquipmentOption :name="option.name" :icon="option.item.icon" :alias="option.alias" />
    </template>
  </AutoComplete>
</template>
