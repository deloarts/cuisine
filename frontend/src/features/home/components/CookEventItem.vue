<script setup lang="ts">
/** One logged meal on the home page: the recipe and its variation, who cooked it and when. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CookEventResponse } from '@/features/home/api/home'
import { formatDay } from '@/features/recipes/utils/dates'
import { imageUrl } from '@/shared/components/recipes/recipeImage'

const props = defineProps<{ event: CookEventResponse }>()
const { t, locale } = useI18n()

const who = computed(() =>
  props.event.is_own ? t('home.you') : (props.event.user?.display_name ?? t('home.someone')),
)
</script>

<template>
  <component
    :is="event.recipe ? 'RouterLink' : 'div'"
    class="cook-event"
    v-bind="
      event.recipe
        ? {
            to: {
              name: 'recipe',
              params: { id: event.recipe.id },
              query: event.variation ? { variation: event.variation.id } : {},
            },
          }
        : {}
    "
  >
    <img
      v-if="event.recipe?.cover_image_id"
      :src="imageUrl(event.recipe.cover_image_id)"
      alt=""
      class="cook-event-thumb"
    />
    <span v-else class="cook-event-thumb cook-event-thumb--empty mdi mdi-silverware-fork-knife" aria-hidden="true" />
    <span class="cook-event-text">
      <span class="cook-event-title">{{ event.recipe?.title ?? t('home.deletedRecipe') }}</span>
      <span v-if="event.variation" class="cook-event-meta">
        <span class="mdi mdi-source-branch" aria-hidden="true" />
        {{ event.variation.name }}
      </span>
      <span class="cook-event-meta">
        {{ who }} · {{ formatDay(event.cooked_on, locale) }}
      </span>
      <span v-if="event.note" class="cook-event-note">„{{ event.note }}“</span>
    </span>
  </component>
</template>

<style scoped lang="scss">
.cook-event {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 3.5rem;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-md);
  color: inherit;
  text-decoration: none;
}

a.cook-event:hover,
a.cook-event:focus-visible {
  background: var(--p-content-hover-background);
}

.cook-event-thumb {
  flex: 0 0 3.25rem;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: var(--p-border-radius-md);
  object-fit: cover;
}

.cook-event-thumb--empty {
  display: grid;
  place-items: center;
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
}

.p-dark .cook-event-thumb--empty {
  background: var(--p-surface-800);
}

.cook-event-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.cook-event-title {
  font-weight: 700;
}

.cook-event-meta {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.cook-event-note {
  overflow: hidden;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
  font-style: italic;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
