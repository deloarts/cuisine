<script setup lang="ts">
/**
 * What an import of recipes did: the recipes it created or updated, the
 * catalogue entries it matched and created, and everything it could not
 * place as it was.
 */
import { useI18n } from 'vue-i18n'

import type { RecipeImportReport } from '@/shared/api/recipeImport'

defineProps<{ report: RecipeImportReport }>()

const { t } = useI18n()
</script>

<template>
  <div class="report" role="status">
    <p>
      <strong>{{ t('recipeImport.imported', { count: report.recipes.length }, report.recipes.length) }}</strong>
      {{ t('recipeImport.matched', { ingredients: report.matched_ingredients, equipment: report.matched_equipment }) }}
    </p>
    <ul v-if="report.recipes.length" class="list">
      <li v-for="r in report.recipes" :key="r.id">
        <RouterLink :to="{ name: 'recipe', params: { id: r.id } }">{{ r.title }}</RouterLink>
        <span v-if="r.updated" class="muted"> ({{ t('recipeImport.updated') }})</span>
      </li>
    </ul>
    <p v-if="report.created_ingredients.length || report.created_equipment.length">
      {{ t('recipeImport.created', { names: [...report.created_ingredients, ...report.created_equipment].join(', ') }) }}
    </p>
    <Message v-if="report.conflicts.length" severity="warn" :closable="false">
      <p class="conflicts-title">{{ t('recipeImport.conflicts') }}</p>
      <ul class="list">
        <li v-for="(c, i) in report.conflicts" :key="i">
          <strong>{{ t(`recipeImport.conflictKinds.${c.kind}`) }}: {{ c.name }}</strong>
          <span v-if="c.recipe"> ({{ c.recipe }})</span> {{ c.detail }}
        </li>
      </ul>
    </Message>
  </div>
</template>

<style scoped lang="scss">
.report {
  display: grid;
  gap: var(--space-2);

  p {
    margin: 0;
  }
}

.list {
  margin: 0;
  padding-left: var(--space-5);
}

.muted {
  color: var(--p-text-muted-color);
}

.conflicts-title {
  font-weight: 700;
}
</style>
