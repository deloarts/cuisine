<script setup lang="ts">
/**
 * Picks a published recipe by searching its title, for any place that needs
 * a recipe chosen from a dialog (the meal plan, a shopping list). It emits
 * the chosen summary and closes.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { watchDebounced } from '@vueuse/core'

import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import { listRecipes } from '@/shared/api/cookbook'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RecipeDuration from '@/shared/components/recipes/RecipeDuration.vue'
import ListItemSkeleton from '@/shared/components/skeleton/ListItemSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'

type RecipeSummary = Schemas['RecipeSummaryResponse']

const visible = defineModel<boolean>('visible', { required: true })
const props = withDefaults(defineProps<{ title?: string }>(), { title: undefined })
const emit = defineEmits<{ select: [recipe: RecipeSummary] }>()

const { t } = useI18n()
const toast = useAppToast()

const search = ref('')
const results = ref<RecipeSummary[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const page = await listRecipes({ search: search.value.trim() || null, status: 'published', limit: 30 })
    results.value = page.items
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

watch(visible, (open) => {
  if (open) {
    search.value = ''
    void load()
  }
})
watchDebounced(search, () => void load(), { debounce: 250 })

function choose(recipe: RecipeSummary) {
  emit('select', recipe)
  visible.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="props.title ?? t('recipes.picker.title')"
    :style="{ width: 'var(--dialog-width-md)' }"
  >
    <div class="picker">
      <label for="recipe-picker-search" class="visually-hidden">
        {{ t('recipes.picker.search') }}
      </label>
      <IconField>
        <InputIcon class="mdi mdi-magnify" />
        <InputText
          id="recipe-picker-search"
          v-model="search"
          :placeholder="t('recipes.picker.search')"
          fluid
          autofocus
        />
      </IconField>
      <SkeletonRegion v-if="loading && results.length === 0" class="picker-list" testid="recipe-picker-skeleton">
        <ListItemSkeleton v-for="n in 4" :key="n" thumb="3rem" class="picker-skeleton-item" />
      </SkeletonRegion>
      <p v-else-if="!loading && results.length === 0" class="hint">{{ t('recipes.picker.empty') }}</p>
      <ul class="picker-list">
        <li v-for="recipe in results" :key="recipe.id">
          <button type="button" class="picker-item" @click="choose(recipe)">
            <img
              v-if="recipe.cover_image_id"
              :src="imageUrl(recipe.cover_image_id)"
              alt=""
              class="picker-thumb"
            />
            <span v-else class="picker-thumb picker-thumb--empty mdi mdi-silverware-fork-knife" />
            <span class="picker-text">
              <span class="picker-title">{{ recipe.title }}</span>
              <span class="picker-meta">
                <RecipeDuration v-if="recipe.total_minutes" :minutes="recipe.total_minutes" />
                {{ t(`recipes.difficulty.${recipe.difficulty}`) }}
              </span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.picker-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.picker-skeleton-item {
  min-height: 3.5rem;
  padding: var(--space-2);
}

.picker-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  min-height: 3.5rem;
  padding: var(--space-2);
  border: none;
  border-radius: var(--p-border-radius-md);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    background: var(--p-content-hover-background);
  }
}

.picker-thumb {
  flex: 0 0 3rem;
  width: 3rem;
  height: 3rem;
  border-radius: var(--p-border-radius-sm);
  object-fit: cover;
}

.picker-thumb--empty {
  display: grid;
  place-items: center;
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
}

.picker-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.picker-title {
  font-weight: 700;
}

.picker-meta {
  display: flex;
  gap: var(--space-2);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}
</style>
