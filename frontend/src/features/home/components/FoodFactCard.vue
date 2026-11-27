<script setup lang="ts">
/**
 * The food fact of the day, the first card of the start page: a short fact
 * about one base ingredient, a link to that ingredient and the Wikipedia
 * article that backs the fact. Everyone sees the same fact on the same day.
 */
import { useI18n } from 'vue-i18n'

import type { FoodFactResponse } from '@/features/home/api/home'
import ContentCard from '@/shared/components/ContentCard.vue'

defineProps<{ fact: FoodFactResponse }>()

const { t } = useI18n()
</script>

<template>
  <ContentCard as="section" class="food-fact" data-testid="home-foodFact">
    <h2 class="food-fact-title">
      <span class="mdi mdi-lightbulb-on-outline" aria-hidden="true" />
      {{ t('home.foodFact.title') }}
    </h2>
    <p class="food-fact-text" :lang="fact.locale">{{ fact.text }}</p>
    <div class="food-fact-links">
      <RouterLink
        :to="{ name: 'ingredient', params: { id: fact.ingredient_id } }"
        class="food-fact-ingredient"
        data-testid="food-fact-ingredient"
      >
        {{ fact.ingredient_name }}
        <span class="mdi mdi-arrow-right" aria-hidden="true" />
      </RouterLink>
      <a
        :href="fact.source_url"
        target="_blank"
        rel="noopener noreferrer"
        class="food-fact-source"
        data-testid="food-fact-source"
      >
        {{ t('home.foodFact.source', { title: fact.source_title }) }}
        <span class="mdi mdi-open-in-new" aria-hidden="true" />
      </a>
    </div>
  </ContentCard>
</template>

<style scoped lang="scss">
.food-fact {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: auto;
  border-left: 4px solid var(--p-primary-color);
}

.food-fact-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--p-primary-color);
  font-size: var(--font-size-lg);
}

.food-fact-text {
  font-size: var(--font-size-lg);
  line-height: 1.5;
}

.food-fact-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-1) var(--space-4);
}

.food-fact-ingredient,
.food-fact-source {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  text-decoration: none;
}

.food-fact-ingredient {
  color: var(--p-primary-color);
  font-weight: 700;
}

.food-fact-source {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}
</style>
