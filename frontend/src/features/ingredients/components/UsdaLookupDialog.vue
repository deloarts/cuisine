<script setup lang="ts">
/**
 * Searches USDA FoodData Central for a generic food and hands its nutrition
 * per 100 g back to the editor. The data is public domain (CC0); the editor
 * names the source next to the values it took over.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { searchUsda, type FoodMatch } from '@/features/ingredients/api/ingredients'
import { useAppToast } from '@/core/composables/useAppToast'

const props = defineProps<{ initialQuery: string }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ pick: [match: FoodMatch] }>()

const { t } = useI18n()
const toast = useAppToast()

const query = ref('')
const results = ref<FoodMatch[]>([])
const searching = ref(false)
const searched = ref(false)

function onShow() {
  query.value = props.initialQuery
  results.value = []
  searched.value = false
  if (query.value.trim()) void search()
}

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    results.value = await searchUsda(query.value.trim(), 15)
    searched.value = true
  } catch (err) {
    toast.error(err)
  } finally {
    searching.value = false
  }
}

function pick(match: FoodMatch) {
  emit('pick', match)
  visible.value = false
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('ingredients.usda.title')" class="usda-dialog" @show="onShow">
    <form class="usda-search" @submit.prevent="search">
      <InputText
        v-model="query"
        :aria-label="t('ingredients.usda.query')"
        :placeholder="t('ingredients.usda.query')"
        fluid
      />
      <Button type="submit" icon="mdi mdi-magnify" :label="t('ingredients.usda.search')" :loading="searching" />
    </form>
    <p class="hint">{{ t('ingredients.usda.hint') }}</p>
    <ul v-if="results.length" class="usda-results">
      <li v-for="match in results" :key="match.fdc_id">
        <button type="button" class="usda-result" @click="pick(match)">
          <span class="usda-name">{{ match.description }}</span>
          <small class="text-muted">
            {{ match.data_type }}<template v-if="match.brand"> · {{ match.brand }}</template>
            <template v-if="match.nutrition.kcal !== null && match.nutrition.kcal !== undefined">
              · {{ Math.round(match.nutrition.kcal) }} kcal
            </template>
          </small>
        </button>
      </li>
    </ul>
    <p v-else-if="searched" class="empty-note">{{ t('ingredients.usda.none') }}</p>
    <p class="field-hint">{{ t('ingredients.usda.source') }}</p>
  </Dialog>
</template>

<style scoped lang="scss">
.usda-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.usda-search {
  display: flex;
  gap: var(--space-2);
}

.usda-results {
  display: grid;
  max-height: 50vh;
  overflow-y: auto;
  padding: 0;
  margin: var(--space-2) 0;
  list-style: none;
}

.usda-result {
  display: grid;
  width: 100%;
  min-height: 2.75rem;
  padding: var(--space-2);
  border: 0;
  border-bottom: 1px solid var(--p-content-border-color);
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    background: var(--p-content-hover-background);
  }
}

.usda-name {
  font-weight: 700;
}
</style>
