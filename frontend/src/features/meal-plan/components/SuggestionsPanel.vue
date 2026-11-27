<script setup lang="ts">
/**
 * Recipes worth planning in the shown week, ranked by the backend from the
 * plan's cooking history, the favourites and the season, each with the
 * reason that carried it. A suggestion is dragged onto a meal of the week or
 * planned through the meal dialog. The list reloads when the week, the plan
 * or the planned recipes change, so a recipe just planned drops out. The
 * frame and its skeleton cards render at once, so loading never moves
 * the page.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { imageUrl } from '@/shared/components/recipes/recipeImage'
import ListItemSkeleton from '@/shared/components/skeleton/ListItemSkeleton.vue'
import type { MealSlot, RecipeSummaryResponse } from '@/shared/cookbook/types'
import { getSuggestions, type MealPlanSuggestion } from '@/features/meal-plan/api/mealPlan'
import { writeSuggestion } from '@/features/meal-plan/suggestionDrag'
import { SLOTS } from '@/features/meal-plan/week'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import ContentCard from '@/shared/components/ContentCard.vue'

const LIMIT = 12

const props = defineProps<{
  dateFrom: string
  dateTo: string
  scope?: Schemas['MealPlanScope']
  /** The recipes already planned in the week; they never show. */
  planned: string[]
}>()
const emit = defineEmits<{ plan: [recipe: RecipeSummaryResponse, slot: MealSlot | null] }>()

const { t } = useI18n()
const toast = useAppToast()

const suggestions = ref<MealPlanSuggestion[]>([])
const loaded = ref(false)
const loading = ref(false)
const slot = ref<MealSlot | 'any'>('any')
const slotOptions = computed(() => [
  { value: 'any', label: t('mealPlan.suggestions.anyMeal') },
  ...SLOTS.map((s) => ({ value: s, label: t(`mealPlan.slots.${s}`) })),
])
const chosenSlot = computed<MealSlot | null>(() => (slot.value === 'any' ? null : slot.value))

// A recipe planned a moment ago leaves at once, before the reload answers.
const shown = computed(() => suggestions.value.filter((s) => !props.planned.includes(s.recipe.id)))

let request = 0
async function load() {
  const mine = ++request
  loading.value = true
  try {
    const result = await getSuggestions({
      date_from: props.dateFrom,
      date_to: props.dateTo,
      scope: props.scope,
      slot: chosenSlot.value ?? undefined,
      limit: LIMIT,
    })
    // An older answer that arrives late must not replace a newer one.
    if (mine !== request) return
    suggestions.value = result
  } catch (err) {
    if (mine === request) toast.error(err)
  } finally {
    if (mine === request) {
      loading.value = false
      loaded.value = true
    }
  }
}

watch(
  () => [props.dateFrom, props.dateTo, props.scope, chosenSlot.value, [...props.planned].sort().join()],
  () => void load(),
  { immediate: true },
)

function onDragStart(recipe: RecipeSummaryResponse, event: DragEvent) {
  writeSuggestion(event, { id: recipe.id, title: recipe.title, servings: recipe.base_servings })
}
</script>

<template>
  <ContentCard as="section" class="suggestions" :aria-busy="loading" aria-labelledby="suggestions-title">
    <header class="suggestions-head">
      <div>
        <h2 id="suggestions-title" class="suggestions-title">
          {{ t('mealPlan.suggestions.title') }}
        </h2>
        <p class="suggestions-hint">{{ t('mealPlan.suggestions.hint') }}</p>
      </div>
      <div class="suggestions-filter">
        <label id="suggestions-slot-label" for="suggestions-slot">{{ t('mealPlan.suggestions.forMeal') }}</label>
        <Select
          id="suggestions-slot"
          v-model="slot"
          :options="slotOptions"
          option-label="label"
          option-value="value"
          aria-labelledby="suggestions-slot-label"
          size="small"
        />
      </div>
    </header>

    <ul v-if="!loaded" class="suggestion-list" aria-hidden="true" data-testid="suggestions-skeleton">
      <li v-for="n in LIMIT" :key="n" class="suggestion suggestion--placeholder">
        <ListItemSkeleton thumb="3.25rem" action />
      </li>
    </ul>
    <p v-else-if="!shown.length" class="suggestions-empty">{{ t('mealPlan.suggestions.empty') }}</p>
    <ul v-else class="suggestion-list">
      <!-- Dragging is a pointer shortcut; the plan button does the same by keyboard. -->
      <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
      <li
        v-for="s in shown"
        :key="s.recipe.id"
        class="suggestion"
        draggable="true"
        :data-recipe-id="s.recipe.id"
        @dragstart="onDragStart(s.recipe, $event)"
      >
        <img v-if="s.recipe.cover_image_id" :src="imageUrl(s.recipe.cover_image_id)" alt="" class="suggestion-cover" />
        <span v-else class="suggestion-cover suggestion-cover--none" aria-hidden="true">
          <i class="mdi mdi-book-open-page-variant-outline" />
        </span>
        <span class="suggestion-text">
          <RouterLink :to="{ name: 'recipe', params: { id: s.recipe.id } }" class="suggestion-name" draggable="false">
            {{ s.recipe.title }}
          </RouterLink>
          <small class="suggestion-reason">
            {{ t(`mealPlan.suggestions.reasons.${s.reason}`) }}
          </small>
        </span>
        <Button
          icon="mdi mdi-calendar-plus"
          text
          rounded
          size="small"
          :aria-label="t('mealPlan.suggestions.planRecipe', { title: s.recipe.title })"
          @click="emit('plan', s.recipe, chosenSlot)"
        />
      </li>
    </ul>
  </ContentCard>
</template>

<style scoped lang="scss">
.suggestions {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.suggestions-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
}

.suggestions-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-size: var(--font-size-lg);
}

.suggestions-hint,
.suggestions-empty {
  margin: 0;
  color: var(--p-text-muted-color);
}

.suggestions-filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
}

// Fixed-height cards in a wrapping grid: the placeholders take exactly the
// room of the real cards, so nothing moves when they arrive.
.suggestion-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.suggestion {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 4.75rem;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-2);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-background);
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

.suggestion--placeholder {
  cursor: default;
}

.suggestion-cover {
  flex-shrink: 0;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: var(--p-content-border-radius);
  object-fit: cover;
}

.suggestion-cover--none {
  display: grid;
  place-items: center;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.suggestion-text {
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
}

.suggestion-name {
  overflow: hidden;
  color: inherit;
  font-weight: 700;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover {
    text-decoration: underline;
  }
}

.suggestion-reason {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  overflow: hidden;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
</style>
