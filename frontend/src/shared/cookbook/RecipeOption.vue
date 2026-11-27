<script setup lang="ts">
/**
 * One recipe as a suggestion row of a picker: a small cover, the title, and
 * under it the total time, the difficulty and who wrote it, so two recipes
 * with similar titles can be told apart. A recipe without a cover shows a
 * book icon in its place.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { imageUrl } from '@/shared/components/recipes/recipeImage'

import type { RecipeSummaryResponse } from './types'

type ShownRecipe = Pick<RecipeSummaryResponse, 'title' | 'cover_image_id' | 'total_minutes' | 'difficulty' | 'owner'>

const props = defineProps<{ recipe: ShownRecipe }>()

const { t, te } = useI18n()

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (!h) return t('pickers.minutes', { m })
  return m ? t('pickers.hoursMinutes', { h, m }) : t('pickers.hours', { h })
}

const details = computed(() => {
  const r = props.recipe
  const parts: string[] = []
  if (r.total_minutes) parts.push(duration(r.total_minutes))
  if (te(`pickers.difficulty.${r.difficulty}`)) parts.push(t(`pickers.difficulty.${r.difficulty}`))
  if (r.owner) parts.push(r.owner.display_name)
  return parts
})
</script>

<template>
  <span class="recipe-option">
    <img v-if="recipe.cover_image_id" :src="imageUrl(recipe.cover_image_id)" alt="" class="recipe-option-cover" />
    <span v-else class="recipe-option-cover recipe-option-cover--none" aria-hidden="true">
      <span class="mdi mdi-book-open-page-variant-outline" />
    </span>
    <span class="recipe-option-text">
      <span class="recipe-option-title">{{ recipe.title }}</span>
      <small v-if="details.length" class="recipe-option-details">{{ details.join(' · ') }}</small>
    </span>
  </span>
</template>

<style scoped lang="scss">
.recipe-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.recipe-option-cover {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--p-border-radius-sm);
  object-fit: cover;
}

.recipe-option-cover--none {
  display: grid;
  place-items: center;
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
}

.p-dark .recipe-option-cover--none {
  background: var(--p-surface-800);
}

.recipe-option-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.recipe-option-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recipe-option-details {
  color: var(--p-text-muted-color);
}
</style>
