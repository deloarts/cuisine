<script setup lang="ts">
/**
 * The "I'll buy it" switches for the sub-recipes of the recipes about to go
 * on a shopping list. A ticked sub-recipe goes on the list as one item; the
 * others are expanded into their ingredients. Shows nothing when there is
 * nothing to choose.
 */
import { useI18n } from 'vue-i18n'

import type { SubRecipeChoice } from './subRecipes'

const props = withDefaults(defineProps<{ choices: SubRecipeChoice[]; idPrefix: string; showRecipes?: boolean }>(), {
  showRecipes: false,
})
const bought = defineModel<string[]>({ default: () => [] })

const { t } = useI18n()
</script>

<template>
  <fieldset v-if="props.choices.length" class="bought">
    <legend class="field-label">{{ t('boughtSubRecipes.legend') }}</legend>
    <div v-for="choice in props.choices" :key="choice.id" class="bought-option">
      <Checkbox v-model="bought" :input-id="`${props.idPrefix}-${choice.id}`" :value="choice.id" />
      <label :for="`${props.idPrefix}-${choice.id}`">
        {{ t('boughtSubRecipes.buyIt', { title: choice.title }) }}
        <small v-if="props.showRecipes" class="text-muted">
          {{ t('boughtSubRecipes.neededBy', { recipes: choice.recipeTitles.join(', ') }) }}
        </small>
      </label>
    </div>
    <small class="field-hint">{{ t('boughtSubRecipes.hint') }}</small>
  </fieldset>
</template>

<style scoped lang="scss">
.bought {
  display: grid;
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  border: 0;
}

.bought-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;

  label {
    display: grid;
  }
}
</style>
