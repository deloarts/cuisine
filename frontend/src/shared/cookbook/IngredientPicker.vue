<script setup lang="ts">
/**
 * Picks one catalogue ingredient by typing part of its name. Drafts are
 * offered too, so an ingredient an agent created can be used before it is
 * reviewed. Each suggestion shows the details `meta` asks for; the default
 * suits merging and mapping, where near-duplicates must be told apart.
 */
import { ref } from 'vue'

import { listIngredients } from '@/shared/api/cookbook'

import IngredientOption from './IngredientOption.vue'
import type { IngredientMeta, IngredientResponse } from './types'

withDefaults(
  defineProps<{ inputId: string; placeholder?: string; disabled?: boolean; meta?: readonly IngredientMeta[] }>(),
  {
    placeholder: undefined,
    disabled: false,
    meta: () => ['category', 'family', 'draft', 'owner', 'locale'],
  },
)
const model = defineModel<IngredientResponse | null>({ default: null })

const suggestions = ref<IngredientResponse[]>([])

async function search(event: { query: string }) {
  try {
    const page = await listIngredients({ search: event.query, limit: 20 })
    suggestions.value = page.items
  } catch {
    suggestions.value = []
  }
}
</script>

<template>
  <AutoComplete
    v-model="model"
    :input-id="inputId"
    :suggestions="suggestions"
    option-label="name"
    :placeholder="placeholder"
    :disabled="disabled"
    force-selection
    fluid
    @complete="search"
  >
    <template #option="{ option }">
      <IngredientOption :ingredient="option" :meta="meta" />
    </template>
  </AutoComplete>
</template>
