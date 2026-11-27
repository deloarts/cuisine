<script setup lang="ts">
/**
 * A public recipe as a visitor who is not signed in reads it: the photo in
 * display size, what it takes, the ingredients for the chosen servings, the
 * steps, nutrition, allergens and diets. Nothing personal and nothing to
 * take away: no download, export or print button, and printing the page
 * prints a note to sign in instead of the recipe. A sub-recipe the visitor
 * may not see stays a placeholder without title or link.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import {
  getPublicRecipe,
  publicAuthorAvatarUrl,
  publicImageUrl,
  type PublicIngredientLine,
  type PublicRecipeDetail,
} from '@/features/recipes/api/publicRecipes'
import NutritionPanel from '@/features/recipes/components/NutritionPanel.vue'
import RecipeDetailSkeleton from '@/features/recipes/components/RecipeDetailSkeleton.vue'
import ServingsStepper from '@/features/recipes/components/ServingsStepper.vue'
import { formatAmount } from '@/features/recipes/utils/scaling'
import EmptyState from '@/shared/components/EmptyState.vue'
import RecipeDuration from '@/shared/components/recipes/RecipeDuration.vue'
import RichText from '@/shared/components/richText/RichText.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import type { MentionResolver } from '@/shared/components/richText/markdown'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { formatSeason, monthName } from '@/shared/cookbook/season'
import { errorStatus } from '@/core/utils/errors'
import ContentCard from '@/shared/components/ContentCard.vue'

// The id the backend gives a mention it rewrote; a sub-recipe mention with it
// names a recipe the visitor may not see.
const HIDDEN_ID = '00000000-0000-0000-0000-000000000000'

const { t, locale } = useI18n()
const route = useRoute()

const recipe = ref<PublicRecipeDetail | null>(null)
const servings = ref(0)
const loading = ref(true)
const problem = ref<'missing' | 'limited' | 'error' | null>(null)

const id = computed(() => String(route.params.id))
const contentLocale = computed(() => contentLocaleOf(locale.value))

async function load(wanted?: number) {
  loading.value = recipe.value === null
  problem.value = null
  try {
    const found = await getPublicRecipe(id.value, {
      servings: wanted,
      locale: contentLocale.value,
    })
    recipe.value = found
    servings.value = found.servings
    document.title = found.title
  } catch (err) {
    const status = errorStatus(err)
    problem.value = status === 404 ? 'missing' : status === 429 ? 'limited' : 'error'
    if (status === 404) recipe.value = null
  } finally {
    loading.value = false
  }
}

// The backend scales, so a change of servings asks again, after a pause.
let pending: ReturnType<typeof setTimeout> | undefined
watch(servings, (value, before) => {
  if (!recipe.value || before === 0 || value === recipe.value.servings) return
  clearTimeout(pending)
  pending = setTimeout(() => void load(value), 250)
})
watch([id, contentLocale], () => void load(), { immediate: true })

const cover = computed(() =>
  recipe.value?.cover_image_id ? publicImageUrl(recipe.value.id, recipe.value.cover_image_id) : null,
)
const seasonText = computed(() =>
  recipe.value?.season_months.length
    ? formatSeason(recipe.value.season_months, (m) => monthName(m, contentLocale.value))
    : null,
)

function amountText(line: { amount: number | null; unit: PublicIngredientLine['unit'] }): string {
  if (line.amount === null) return t('recipes.detail.toTaste')
  const unit = line.unit
  const label = !unit
    ? ''
    : unit.abbreviation || (line.amount > 1 && unit.plural_name ? unit.plural_name : unit.name)
  return `${formatAmount(line.amount, contentLocale.value, unit?.kind)} ${label}`.trim()
}

function lineName(line: PublicIngredientLine): string {
  if (line.sub_recipe && !line.sub_recipe.accessible) return t('recipes.public.hiddenSubRecipe')
  return line.name
}

// Mentions already carry their current names; a hidden sub-recipe reads as
// the placeholder, and nothing links into the signed-in pages.
const resolveMention: MentionResolver = (ref) =>
  ref.kind === 'recipe' && ref.id === HIDDEN_ID
    ? { name: t('recipes.public.hiddenSubRecipe'), recipeId: null }
    : { name: ref.name, recipeId: null }
</script>

<template>
  <section class="public-recipe-page">
    <RouterLink :to="{ name: 'public-recipes' }" class="public-back">
      <i class="mdi mdi-arrow-left" aria-hidden="true" /> {{ t('recipes.public.back') }}
    </RouterLink>

    <RecipeDetailSkeleton v-if="loading" />
    <EmptyState
      v-else-if="problem === 'missing'"
      :message="t('recipes.public.missing')"
      icon="mdi mdi-earth-off"
    />
    <Message v-else-if="problem === 'limited' && !recipe" severity="warn" :closable="false">
      {{ t('recipes.public.limited') }}
    </Message>
    <Message v-else-if="problem === 'error' && !recipe" severity="error" :closable="false">
      {{ t('common.error') }}
    </Message>

    <template v-if="recipe && problem !== 'missing'">
      <p class="public-print-note" data-testid="public-print-note">
        {{ t('recipes.public.signInToPrint') }}
      </p>
      <article class="public-recipe" data-testid="public-recipe">
        <Message v-if="problem === 'limited'" severity="warn" :closable="false">
          {{ t('recipes.public.limited') }}
        </Message>
        <div v-if="cover" class="public-cover">
          <img :src="cover" :alt="recipe.title" />
        </div>
        <header class="public-head">
          <h1 class="public-title">{{ recipe.title }}</h1>
          <p v-if="recipe.author" class="public-author">
            <UserAvatar
              class="public-author-avatar"
              :name="recipe.author"
              :src="recipe.author_avatar ? publicAuthorAvatarUrl(recipe.id) : null"
            />
            {{ t('recipes.public.by', { name: recipe.author }) }}
          </p>
          <p class="public-meta">
            <RecipeDuration v-if="recipe.total_minutes" :minutes="recipe.total_minutes" />
            <span>{{ t(`recipes.difficulty.${recipe.difficulty}`) }}</span>
            <span v-if="seasonText">
              <span class="mdi mdi-calendar-month-outline" aria-hidden="true" /> {{ seasonText }}
            </span>
          </p>
          <ul v-if="recipe.tags.length" class="public-chips">
            <li v-for="tag in recipe.tags" :key="tag.id">{{ tag.name }}</li>
          </ul>
          <RichText v-if="recipe.description" :text="recipe.description" class="public-description" />
        </header>

        <div class="public-columns">
          <ContentCard as="aside" class="public-side">
            <h2 class="public-section-title">{{ t('recipes.detail.ingredients') }}</h2>
            <ServingsStepper v-model="servings" />
            <ul class="public-lines">
              <li v-for="(line, i) in recipe.ingredients" :key="`line-${i}`">
                <span class="public-amount">{{ amountText(line) }}</span>
                <span>{{ line.name }}</span>
              </li>
            </ul>
            <template v-if="recipe.needs.length">
              <h3 class="public-subtitle">{{ t('recipes.public.needs') }}</h3>
              <ul class="public-lines">
                <li v-for="(need, i) in recipe.needs" :key="`need-${i}`">
                  <span class="public-amount">{{ need.amount !== null ? amountText(need) : '' }}</span>
                  <RouterLink
                    v-if="need.sub_recipe.accessible && need.sub_recipe.id"
                    :to="{ name: 'public-recipe', params: { id: need.sub_recipe.id } }"
                  >
                    {{ need.sub_recipe.title }}
                  </RouterLink>
                  <span v-else class="public-hidden">{{ t('recipes.public.hiddenSubRecipe') }}</span>
                </li>
              </ul>
            </template>
            <template v-if="recipe.equipment.length">
              <h3 class="public-subtitle">{{ t('recipes.public.equipment') }}</h3>
              <ul class="public-lines">
                <li v-for="(item, i) in recipe.equipment" :key="`equipment-${i}`">
                  <span class="public-amount">{{ item.count && item.count > 1 ? `${item.count} ×` : '' }}</span>
                  <span>{{ item.name }}</span>
                </li>
              </ul>
            </template>
            <template v-if="recipe.allergens.length">
              <h3 class="public-subtitle">{{ t('recipes.public.allergens') }}</h3>
              <p>{{ recipe.allergens.map((a) => t(`allergens.${a}`)).join(', ') }}</p>
            </template>
            <template v-if="recipe.diets.length">
              <h3 class="public-subtitle">{{ t('recipes.public.diets') }}</h3>
              <ul class="public-chips">
                <li v-for="d in recipe.diets" :key="d">{{ t(`diets.${d}`) }}</li>
              </ul>
            </template>
          </ContentCard>

          <div class="public-main">
            <ContentCard as="section">
              <h2 class="public-section-title">{{ t('recipes.public.steps') }}</h2>
              <ol class="public-steps">
                <li v-for="step in recipe.steps" :key="step.position" class="public-step">
                  <span class="public-step-number" aria-hidden="true">{{ step.position }}</span>
                  <div class="public-step-body">
                    <ul v-if="step.ingredients.length" class="public-step-lines">
                      <li v-for="(line, i) in step.ingredients" :key="`s${step.position}-${i}`">
                        <strong>{{ amountText(line) }}</strong>
                        {{ lineName(line) }}
                        <span v-if="line.note" class="public-note">({{ line.note }})</span>
                      </li>
                    </ul>
                    <RichText :text="step.text" :resolve="resolveMention" />
                    <p v-if="step.duration_minutes" class="public-step-time">
                      <RecipeDuration :minutes="step.duration_minutes" />
                    </p>
                    <img
                      v-if="step.image_id"
                      :src="publicImageUrl(recipe.id, step.image_id)"
                      alt=""
                      loading="lazy"
                      class="public-step-image"
                    />
                  </div>
                </li>
              </ol>
            </ContentCard>
            <ContentCard as="section" v-if="recipe.tips">
              <h2 class="public-section-title">{{ t('recipes.public.tips') }}</h2>
              <RichText :text="recipe.tips" />
            </ContentCard>
            <ContentCard as="section">
              <h2 class="public-section-title">{{ t('recipes.public.nutrition') }}</h2>
              <NutritionPanel :nutrition="recipe.nutrition" />
            </ContentCard>
            <p v-if="recipe.source_name || recipe.source_url" class="hint">
              {{ t('recipes.public.source') }}
              <a
                v-if="recipe.source_url"
                :href="recipe.source_url"
                target="_blank"
                rel="noopener noreferrer nofollow"
              >{{ recipe.source_name || recipe.source_url }}</a>
              <template v-else>{{ recipe.source_name }}</template>
            </p>
          </div>
        </div>
      </article>
    </template>
  </section>
</template>

<style scoped lang="scss">
.public-recipe-page {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.public-back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  color: var(--p-primary-color);
}

.public-recipe {
  display: grid;
  gap: var(--space-4);
}

.public-cover img {
  display: block;
  width: 100%;
  max-height: 24rem;
  object-fit: cover;
  border-radius: var(--p-border-radius-lg);
}

.public-head {
  display: grid;
  gap: var(--space-2);
}

.public-title {
  font-size: var(--font-size-4xl);
  line-height: 1.1;
}

.public-author,
.public-meta {
  color: var(--p-text-muted-color);
}

.public-author {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.public-author-avatar {
  --avatar-size: 2rem;
}

.public-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
}

.public-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    padding: var(--space-1) var(--space-2);
    border-radius: 999px;
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
    font-size: var(--font-size-sm);
  }
}

.public-columns {
  display: grid;
  gap: var(--space-4);
  align-items: start;
}

.public-side,
.public-main {
  display: grid;
  gap: var(--space-3);
}

.public-section-title {
  font-size: var(--font-size-2xl);
}

.public-subtitle {
  font-size: var(--font-size-lg);
}

.public-lines {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    display: grid;
    grid-template-columns: minmax(4.5rem, auto) 1fr;
    gap: var(--space-2);
  }
}

.public-amount {
  font-weight: 700;
  text-align: right;
}

.public-hidden,
.public-note {
  color: var(--p-text-muted-color);
}

.public-hidden {
  font-style: italic;
}

.public-steps {
  display: grid;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}

.public-step {
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  gap: var(--space-3);
}

.public-step-number {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-weight: 700;
}

.public-step-body {
  display: grid;
  gap: var(--space-2);
}

.public-step-lines {
  margin: 0;
  padding-left: var(--space-4);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.public-step-time {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.public-step-image {
  width: 100%;
  max-width: 30rem;
  border-radius: var(--p-border-radius-md);
}

.public-print-note {
  display: none;
}

@media (min-width: $bp-md) {
  .public-columns {
    grid-template-columns: minmax(16rem, 1fr) minmax(0, 2fr);
  }

  .public-side {
    position: sticky;
    top: var(--space-3);
  }
}

// Printing is for signed-in readers: on paper the page says so instead of
// showing the recipe.
@media print {
  .public-recipe,
  .public-back {
    display: none;
  }

  .public-print-note {
    display: block;
    font-size: var(--font-size-xl);
  }
}
</style>
