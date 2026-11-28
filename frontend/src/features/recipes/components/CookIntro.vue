<script setup lang="ts">
/**
 * What cook mode shows before step 1: the sub-recipes to make first, each
 * with a button that cooks it now, and the equipment to set out, marking
 * what the kitchen lacks. Step mode shows it as its own screen, flow mode at
 * the top of the column.
 */
import { useI18n } from 'vue-i18n'

import type { SubRecipeNeed } from '@/features/recipes/api/recipes'
import EquipmentList from '@/features/recipes/components/EquipmentList.vue'
import type { EquipmentNeed } from '@/features/recipes/utils/equipment'

defineProps<{ needs: SubRecipeNeed[]; setOut: EquipmentNeed[] }>()
const emit = defineEmits<{ cookFirst: [subRecipeId: string, batches: number] }>()

const { t } = useI18n()
</script>

<template>
  <div class="cook-intro">
    <h1 class="cook-heading">
      {{ needs.length ? t('recipes.cookMode.firstTitle') : t('recipes.cookMode.setOutTitle') }}
    </h1>
    <p v-if="needs.length" class="cook-intro-text">{{ t('recipes.cookMode.firstText') }}</p>
    <ul v-if="needs.length" class="cook-first">
      <li v-for="(need, i) in needs" :key="need.sub_recipe.id ?? `hidden-${i}`" class="cook-first-item">
        <span class="cook-first-title">
          {{ need.sub_recipe.accessible ? need.sub_recipe.title : t('recipes.subRecipes.hidden') }}
        </span>
        <Button
          v-if="need.sub_recipe.accessible && need.sub_recipe.id"
          :label="t('recipes.cookMode.cookFirst')"
          icon="mdi mdi-play"
          severity="secondary"
          outlined
          @click="emit('cookFirst', need.sub_recipe.id, need.batches)"
        />
      </li>
    </ul>
    <div v-if="setOut.length" class="cook-set-out" data-testid="cook-set-out">
      <h2>{{ t('recipes.cookMode.setOut') }}</h2>
      <EquipmentList :items="setOut" large />
    </div>
  </div>
</template>

<style scoped lang="scss">
.cook-intro {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cook-heading {
  font-size: clamp(2rem, 7vw, 3rem);
}

.cook-intro-text {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.cook-first {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.cook-first-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-50);
}

.p-dark .cook-first-item {
  background: var(--p-surface-900);
}

.cook-first-title {
  font-size: clamp(1.15rem, 4.5vw, 1.5rem);
  font-weight: 700;
}

.cook-set-out {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-50);

  h2 {
    font-family: var(--font-head);
    font-weight: 700;
    font-size: var(--font-size-md);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--p-text-muted-color);
  }
}

.p-dark .cook-set-out {
  background: var(--p-surface-900);
}
</style>
