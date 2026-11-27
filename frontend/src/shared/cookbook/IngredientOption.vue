<script setup lang="ts">
/**
 * One catalogue ingredient as a suggestion row of a picker: the name, led by
 * the other name the search matched ("Paradeiser → Tomate"), and under it
 * the details that tell similar ingredients apart. Each picker asks for the
 * details its choice depends on through `meta`: the shopping list wants the
 * category (the aisle), a food restriction the family and allergens, the
 * admin merge the owner and language as well.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { IngredientMeta, IngredientResponse } from './types'

type ShownIngredient = Pick<
  IngredientResponse,
  'name' | 'category' | 'family' | 'allergens' | 'status' | 'season_months' | 'owner' | 'locale'
> & { matched_alias?: string | null }

const props = withDefaults(defineProps<{ ingredient: ShownIngredient; meta?: readonly IngredientMeta[] }>(), {
  meta: () => ['category', 'family', 'draft'],
})

const { t } = useI18n()

/** Allergens shown by name before the rest collapse into "+n". */
const ALLERGEN_LIMIT = 3

const shows = (m: IngredientMeta) => props.meta.includes(m)

const details = computed(() => {
  const i = props.ingredient
  const parts: string[] = []
  if (shows('category') && i.category) parts.push(i.category.name)
  if (shows('family') && i.family) parts.push(i.family.name)
  if (shows('owner') && i.owner) parts.push(t('pickers.by', { name: i.owner.display_name }))
  if (shows('locale')) parts.push(t(i.locale === 'de-AT' ? 'contentLocales.deAT' : 'contentLocales.enGB'))
  return parts
})

const allergenNames = computed(() =>
  shows('allergens') ? props.ingredient.allergens.map((a) => t(`allergens.${a}`)) : [],
)
const draft = computed(() => shows('draft') && props.ingredient.status === 'draft')
const inSeason = computed(
  () => shows('season') && props.ingredient.season_months.includes(new Date().getMonth() + 1),
)
</script>

<template>
  <span class="ingredient-option">
    <span class="ingredient-option-main">
      <span class="ingredient-option-name">
        <template v-if="ingredient.matched_alias">
          <em>{{ ingredient.matched_alias }}</em>
          <span aria-hidden="true"> → </span>
          <span class="visually-hidden">{{ t('pickers.aliasOf') }}</span>
        </template>
        {{ ingredient.name }}
      </span>
      <span v-if="inSeason" class="mdi mdi-leaf ingredient-option-season" :title="t('pickers.inSeason')" aria-hidden="true" />
      <span v-if="inSeason" class="visually-hidden">{{ t('pickers.inSeason') }}</span>
      <Tag v-if="draft" :value="t('pickers.draft')" severity="warn" class="ingredient-option-tag" />
    </span>
    <span v-if="details.length || allergenNames.length" class="ingredient-option-meta">
      <small v-if="details.length" class="ingredient-option-details">{{ details.join(' · ') }}</small>
      <small v-if="allergenNames.length" class="ingredient-option-allergens">
        <span class="visually-hidden">{{ t('pickers.allergens', { names: allergenNames.join(', ') }) }}</span>
        <span
          v-for="name in allergenNames.slice(0, ALLERGEN_LIMIT)"
          :key="name"
          class="ingredient-option-allergen"
          aria-hidden="true"
        >{{ name }}</span>
        <span v-if="allergenNames.length > ALLERGEN_LIMIT" class="ingredient-option-allergen" aria-hidden="true">
          {{ t('pickers.moreAllergens', { n: allergenNames.length - ALLERGEN_LIMIT }) }}
        </span>
      </small>
    </span>
  </span>
</template>

<style scoped lang="scss">
.ingredient-option {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.ingredient-option-main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ingredient-option-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ingredient-option-season {
  color: var(--p-green-600);
}

.ingredient-option-tag {
  font-size: var(--font-size-xs);
}

.ingredient-option-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-1) var(--space-2);
  color: var(--p-text-muted-color);
}

.ingredient-option-allergens {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.ingredient-option-allergen {
  padding: 0 var(--space-1);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
}
</style>
