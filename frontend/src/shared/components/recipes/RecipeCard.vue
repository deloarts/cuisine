<script setup lang="ts">
/**
 * A recipe as a photo card: the cover, the title in the display font, time,
 * difficulty, rating and tags, with a heart to keep it. Once the reader's
 * kitchen is set up, a recipe that needs equipment it lacks says what. It
 * counts the recipe's variations and says when one of them suits the chosen
 * guests or diets better than the original. Every card says whose recipe
 * it is: the owner with their avatar, or for a recipe from a paired
 * instance its author and source. The card sizes itself
 * from the space its container gives it (a container query), so the same
 * card works in the browse grid, on the home page and in a picker.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Schemas } from '@/core/api/generated'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RecipeDuration from '@/shared/components/recipes/RecipeDuration.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import { cardDiet } from '@/shared/components/recipes/dietBadge'

type RecipeSummary = Schemas['RecipeSummaryResponse']

const props = withDefaults(
  defineProps<{
    recipe: RecipeSummary
    showFavourite?: boolean
    maxTags?: number
    /** Query the card's link carries, such as the chosen dinner guests. */
    linkQuery?: Record<string, string | string[]>
  }>(),
  { showFavourite: true, maxTags: 3, linkQuery: () => ({}) },
)
const emit = defineEmits<{ toggleFavourite: [recipe: RecipeSummary] }>()

const { t } = useI18n()

const cover = computed(() =>
  props.recipe.cover_image_id ? imageUrl(props.recipe.cover_image_id) : null,
)
const tags = computed(() => props.recipe.tags.slice(0, props.maxTags))
const diet = computed(() => cardDiet(props.recipe.diets))
// "Needs a stand mixer", or "… and 2 more"; null before the kitchen is set up.
const needs = computed(() => {
  const missing = props.recipe.missing_equipment ?? []
  const first = missing[0]
  if (!first) return null
  return missing.length === 1
    ? t('recipes.card.needs', { name: first.name })
    : t('recipes.card.needsMore', { name: first.name, n: missing.length - 1 })
})
// "by <author> · <instance>", or only the instance when no author is shown.
const source = computed(() => {
  const mirror = props.recipe.mirror
  if (!mirror) return null
  return mirror.author_name
    ? t('recipes.mirror.byAt', { name: mirror.author_name, instance: mirror.instance_name })
    : t('recipes.mirror.cardFrom', { instance: mirror.instance_name })
})
// A local recipe names its owner, unless the reader may not see who it is.
const owner = computed(() => (props.recipe.mirror ? null : props.recipe.owner))
const rating = computed(() =>
  props.recipe.rating_average === null ? null : props.recipe.rating_average.toFixed(1),
)
</script>

<template>
  <article class="recipe-card-frame">
    <RouterLink
      class="recipe-card"
      :to="{ name: 'recipe', params: { id: recipe.id }, query: linkQuery }"
      :data-testid="`recipe-card-${recipe.id}`"
    >
      <div class="recipe-card-cover" :class="{ 'recipe-card-cover--empty': !cover }">
        <img v-if="cover" :src="cover" alt="" loading="lazy" />
        <span v-else class="mdi mdi-silverware-fork-knife" aria-hidden="true" />
        <span class="recipe-card-badges">
          <span v-if="recipe.status === 'draft'" class="recipe-card-badge">
            {{ t('recipes.status.draft') }}
          </span>
          <span v-if="recipe.has_warning" class="recipe-card-warning" :title="t('recipes.card.warning')">
            <span class="mdi mdi-alert-circle" aria-hidden="true" />
            <span class="visually-hidden">{{ t('recipes.card.warning') }}</span>
          </span>
        </span>
        <span v-if="recipe.unsuitable_for_guests && recipe.variation_fits_guests" class="recipe-card-guests" data-testid="recipe-card-variation-guests">
          <span class="mdi mdi-source-branch" aria-hidden="true" />
          {{ t('recipes.variations.fitsGuests') }}
        </span>
        <span v-else-if="recipe.unsuitable_for_guests" class="recipe-card-guests">
          <span class="mdi mdi-account-alert-outline" aria-hidden="true" />
          {{ t('recipes.guests.flag') }}
        </span>
      </div>
      <div class="recipe-card-body">
        <h3 class="recipe-card-title">{{ recipe.title }}</h3>
        <p v-if="source" class="recipe-card-source" data-testid="recipe-card-source">
          <span class="mdi mdi-transit-connection-variant" aria-hidden="true" />
          {{ source }}
        </p>
        <p v-else-if="owner" class="recipe-card-source" data-testid="recipe-card-owner">
          <UserAvatar class="recipe-card-avatar" :name="owner.display_name" :avatar-id="owner.avatar_id" />
          {{ t('recipes.detail.by', { name: owner.display_name }) }}
        </p>
        <p v-if="recipe.description_text" class="recipe-card-description">
          {{ recipe.description_text }}
        </p>
        <p class="recipe-card-meta">
          <RecipeDuration v-if="recipe.total_minutes" :minutes="recipe.total_minutes" />
          <span>{{ t(`recipes.difficulty.${recipe.difficulty}`) }}</span>
          <span v-if="diet" class="recipe-card-diet">
            <span class="mdi mdi-leaf" aria-hidden="true" />
            {{ t(`diets.${diet}`) }}
          </span>
          <span v-if="rating" class="recipe-card-rating">
            <span class="mdi mdi-star" aria-hidden="true" />
            {{ t('recipes.card.rating', { avg: rating, count: recipe.rating_count }) }}
          </span>
          <span v-if="recipe.variation_count" class="recipe-card-variations" data-testid="recipe-card-variations">
            <span class="mdi mdi-source-branch" aria-hidden="true" />
            {{ t('recipes.variations.cardCount', { n: recipe.variation_count }, recipe.variation_count) }}
          </span>
        </p>
        <p v-if="recipe.variation_fits_diets" class="recipe-card-fits" data-testid="recipe-card-variation-diets">
          <span class="mdi mdi-leaf" aria-hidden="true" />
          {{ t('recipes.variations.fitsDiets') }}
        </p>
        <p v-if="needs" class="recipe-card-needs" data-testid="recipe-card-needs">
          <span class="mdi mdi-stove" aria-hidden="true" />
          {{ needs }}
        </p>
        <ul v-if="tags.length" class="recipe-card-tags">
          <li v-for="tag in tags" :key="tag.id">{{ tag.name }}</li>
        </ul>
      </div>
    </RouterLink>
    <button
      v-if="showFavourite"
      type="button"
      class="recipe-card-heart"
      :class="{ 'recipe-card-heart--on': recipe.is_favourite }"
      :aria-pressed="recipe.is_favourite"
      :aria-label="recipe.is_favourite ? t('recipes.card.unfavourite') : t('recipes.card.favourite')"
      @click="emit('toggleFavourite', recipe)"
    >
      <span
        class="mdi"
        :class="recipe.is_favourite ? 'mdi-heart' : 'mdi-heart-outline'"
        aria-hidden="true"
      />
    </button>
  </article>
</template>

<style scoped lang="scss">
.recipe-card-frame {
  --recipe-card-heart: #e11d48;

  position: relative;
  container-type: inline-size;
  height: 100%;
}

.recipe-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  color: inherit;
  text-decoration: none;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  box-shadow: var(--shadow-md);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
    outline-offset: 2px;
  }
}

@media (hover: hover) {
  .recipe-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }
}

.recipe-card-needs {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin: 0;
  color: var(--p-orange-600);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.p-dark .recipe-card-needs {
  color: var(--p-orange-400);
}

// The cover is always 4:3. The image sits out of the flow, because an
// in-flow image's own height would otherwise stretch the box past its
// aspect ratio (a square photo made its card taller than the others).
.recipe-card-cover {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  background: var(--p-surface-100);

  img {
    position: absolute;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.recipe-card-cover--empty {
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  font-size: clamp(2rem, 18cqi, 4rem);
}

.p-dark .recipe-card-cover {
  background: var(--p-surface-800);
}

.recipe-card-badges {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.recipe-card-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--p-border-radius-sm);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
}

.recipe-card-guests {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  left: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--p-border-radius-sm);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  box-shadow: var(--shadow-sm);

  .mdi {
    color: var(--p-orange-600);
  }
}

.recipe-card-diet {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-green-700);
}

.p-dark .recipe-card-diet {
  color: var(--p-green-400);
}

.recipe-card-warning {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--p-content-background);
  color: var(--p-orange-600);
  font-size: var(--font-size-xl);
}

.recipe-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
}

.recipe-card-title {
  font-family: var(--font-display);
  font-weight: 400;
  font-size: clamp(1.2rem, 9cqi, 1.6rem);
  line-height: 1.15;
}

.recipe-card-source {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
}

.recipe-card-avatar {
  --avatar-size: 1.1rem;

  flex-shrink: 0;
}

.recipe-card-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.recipe-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.recipe-card-variations {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.recipe-card-fits {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-green-700);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.p-dark .recipe-card-fits {
  color: var(--p-green-400);
}

.recipe-card-rating .mdi {
  color: var(--p-yellow-500);
}

.recipe-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: var(--space-1) 0 0;
  padding: 0;
  list-style: none;

  li {
    padding: 0 var(--space-2);
    border-radius: 1rem;
    background: var(--p-surface-100);
    font-size: var(--font-size-xs);
    line-height: 1.7;
  }
}

.p-dark .recipe-card-tags li {
  background: var(--p-surface-800);
}

// A narrow card, such as in a two-column phone grid, drops the tags and
// keeps the title and the time.
@container (width < 13rem) {
  .recipe-card-tags,
  .recipe-card-description {
    display: none;
  }

  .recipe-card-body {
    padding: var(--space-2);
  }
}

.recipe-card-heart {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
  box-shadow: var(--shadow-sm);

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.recipe-card-heart--on {
  color: var(--recipe-card-heart);
}
</style>
