<script setup lang="ts">
/**
 * Picks one published recipe by typing part of its title, like the
 * ingredient search: the dropdown button lists the recipes alphabetically
 * without a query, and every suggestion shows its cover, title and details.
 */
import { ref } from 'vue'

import { listRecipes } from '@/shared/api/cookbook'

import RecipeOption from './RecipeOption.vue'
import type { RecipeSummaryResponse } from './types'

withDefaults(defineProps<{ inputId: string; placeholder?: string }>(), { placeholder: undefined })
const model = defineModel<RecipeSummaryResponse | null>({ default: null })

const suggestions = ref<RecipeSummaryResponse[]>([])

async function search(event: { query: string }) {
  try {
    const search = event.query.trim()
    const page = await listRecipes({ ...(search ? { search } : {}), status: 'published', sort: 'title', limit: 20 })
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
    option-label="title"
    :placeholder="placeholder"
    force-selection
    :delay="200"
    dropdown
    fluid
    @complete="search"
  >
    <template #option="{ option }">
      <RecipeOption :recipe="option" />
    </template>
  </AutoComplete>
</template>
