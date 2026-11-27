<script setup lang="ts">
/**
 * The reader's own food restriction warnings for a recipe. They come from
 * the reader's private restrictions and are never shown to anybody else.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { RecipeDetailResponse } from '@/features/recipes/api/recipes'

const props = defineProps<{ warnings: RecipeDetailResponse['warnings'] }>()
const { t, te } = useI18n()

// Diet labels belong to the food restrictions page; until a label exists the
// diet's own name shows.
const dietLabel = (diet: string) => (te(`diets.${diet}`) ? t(`diets.${diet}`) : diet)

const KINDS = ['allergy', 'intolerance', 'diet'] as const
const kindKey = (kind: string) => (KINDS as readonly string[]).includes(kind) ? kind : 'allergy'

const lines = computed(() =>
  props.warnings.map((w) => {
    const what = w.allergen
      ? t(`allergens.${w.allergen}`)
      : w.diet
        ? dietLabel(w.diet)
        : // An ingredient or an ingredient family: the names it matched here.
          w.ingredient_names.join(', ') || t('recipes.warning.ingredient')
    return {
      id: w.restriction_id,
      text: t(`recipes.warning.${kindKey(w.kind)}`, { what, names: w.ingredient_names.join(', ') }),
    }
  }),
)
</script>

<template>
  <Message severity="warn" class="warning-banner">
    <strong>{{ t('recipes.warning.title') }}</strong>
    <ul>
      <li v-for="line in lines" :key="line.id">{{ line.text }}</li>
    </ul>
    <small>{{ t('recipes.warning.private') }}</small>
  </Message>
</template>

<style scoped lang="scss">
ul {
  margin: var(--space-1) 0;
  padding-left: var(--space-5);
}
</style>
