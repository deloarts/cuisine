<script setup lang="ts">
/**
 * The public recipes for visitors who are not signed in: search, the tags
 * the public recipes carry and a diet filter, nothing personal. Images come
 * in display size from the public image route. While the instance does not
 * allow public recipes the list is simply empty.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  listPublicRecipes,
  listPublicTags,
  publicAuthorAvatarUrl,
  publicImageUrl,
  type PublicRecipeSummary,
  type PublicTag,
} from '@/features/recipes/api/publicRecipes'
import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import { DIETS, cardDiet } from '@/shared/components/recipes/dietBadge'
import RecipeCardSkeleton from '@/shared/components/recipes/RecipeCardSkeleton.vue'
import RecipeDuration from '@/shared/components/recipes/RecipeDuration.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import type { Schemas } from '@/core/api/generated'
import { errorStatus } from '@/core/utils/errors'

const PAGE_SIZE = 24
// The placeholder cards of a first load: enough to fill the first screen.
const SKELETON_CARDS = 8

const { t, locale } = useI18n()

const recipes = ref<PublicRecipeSummary[]>([])
const total = ref(0)
const tags = ref<PublicTag[]>([])
const search = ref('')
const chosenTags = ref<string[]>([])
const diet = ref<Schemas['Diet'] | null>(null)
const loading = ref(true)
const failed = ref<'limited' | 'error' | null>(null)

const contentLocale = computed(() => contentLocaleOf(locale.value))
const diets = computed(() => DIETS.map((d) => ({ value: d, label: t(`diets.${d}`) })))
const more = computed(() => recipes.value.length < total.value)

async function load(append = false) {
  loading.value = true
  failed.value = null
  try {
    const page = await listPublicRecipes({
      search: search.value.trim() || undefined,
      tag_id: chosenTags.value,
      diets: diet.value ? [diet.value] : [],
      limit: PAGE_SIZE,
      offset: append ? recipes.value.length : 0,
      locale: contentLocale.value,
    })
    recipes.value = append ? [...recipes.value, ...page.items] : page.items
    total.value = page.total
  } catch (err) {
    failed.value = errorStatus(err) === 429 ? 'limited' : 'error'
  } finally {
    loading.value = false
  }
}

function toggleTag(id: string) {
  chosenTags.value = chosenTags.value.includes(id)
    ? chosenTags.value.filter((t) => t !== id)
    : [...chosenTags.value, id]
}

let typing: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(typing)
  typing = setTimeout(() => void load(), 300)
})
watch([chosenTags, diet, contentLocale], () => void load())

onMounted(() => {
  void load()
  listPublicTags(contentLocale.value)
    .then((found) => (tags.value = found))
    .catch(() => (tags.value = []))
})
</script>

<template>
  <section class="public-recipes">
    <PageHeader :title="t('recipes.public.title')" />
    <p class="hint">{{ t('recipes.public.intro') }}</p>

    <div class="public-filters">
      <span class="public-search">
        <label for="public-search" class="visually-hidden">{{ t('recipes.public.search') }}</label>
        <InputText
          id="public-search"
          v-model="search"
          type="search"
          :placeholder="t('recipes.public.search')"
          maxlength="128"
        />
      </span>
      <div class="public-diet">
        <label id="public-diet-label" for="public-diet" class="visually-hidden">{{ t('recipes.public.diet') }}</label>
        <Select
          id="public-diet"
          v-model="diet"
          :options="diets"
          option-label="label"
          option-value="value"
          :placeholder="t('recipes.public.diet')"
          aria-labelledby="public-diet-label"
          show-clear
        />
      </div>
    </div>
    <div v-if="tags.length" class="public-tags" role="group" :aria-label="t('recipes.public.tags')">
      <button
        v-for="tag in tags"
        :key="tag.id"
        type="button"
        class="public-tag"
        :class="{ 'public-tag--on': chosenTags.includes(tag.id) }"
        :aria-pressed="chosenTags.includes(tag.id)"
        @click="toggleTag(tag.id)"
      >
        {{ tag.name }}
      </button>
    </div>

    <Message v-if="failed === 'limited'" severity="warn" :closable="false">{{ t('recipes.public.limited') }}</Message>
    <Message v-else-if="failed" severity="error" :closable="false">{{ t('common.error') }}</Message>

    <div v-if="recipes.length" class="public-grid">
      <RouterLink
        v-for="recipe in recipes"
        :key="recipe.id"
        :to="{ name: 'public-recipe', params: { id: recipe.id } }"
        class="public-card"
        :data-testid="`public-recipe-${recipe.id}`"
      >
        <div class="public-card-cover" :class="{ 'public-card-cover--empty': !recipe.cover_image_id }">
          <img
            v-if="recipe.cover_image_id"
            :src="publicImageUrl(recipe.id, recipe.cover_image_id)"
            alt=""
            loading="lazy"
          />
          <span v-else class="mdi mdi-silverware-fork-knife" aria-hidden="true" />
        </div>
        <div class="public-card-body">
          <h2 class="public-card-title">{{ recipe.title }}</h2>
          <p v-if="recipe.description_text" class="public-card-description">{{ recipe.description_text }}</p>
          <p class="public-card-meta">
            <RecipeDuration v-if="recipe.total_minutes" :minutes="recipe.total_minutes" />
            <span>{{ t(`recipes.difficulty.${recipe.difficulty}`) }}</span>
            <span v-if="cardDiet(recipe.diets)" class="public-card-diet">
              <span class="mdi mdi-leaf" aria-hidden="true" />
              {{ t(`diets.${cardDiet(recipe.diets)}`) }}
            </span>
          </p>
          <p v-if="recipe.author" class="public-card-author">
            <UserAvatar
              class="public-card-avatar"
              :name="recipe.author"
              :src="recipe.author_avatar ? publicAuthorAvatarUrl(recipe.id) : null"
            />
            {{ t('recipes.public.by', { name: recipe.author }) }}
          </p>
        </div>
      </RouterLink>
    </div>
    <SkeletonRegion v-else-if="loading" class="public-grid" testid="public-recipes-skeleton">
      <RecipeCardSkeleton v-for="n in SKELETON_CARDS" :key="n" author />
    </SkeletonRegion>
    <EmptyState v-else-if="!failed" :message="t('recipes.public.empty')" icon="mdi mdi-earth-off" />
    <div v-if="more" class="public-more">
      <Button :label="t('recipes.public.more')" outlined :loading="loading" @click="load(true)" />
    </div>
  </section>
</template>

<style scoped lang="scss">
.public-recipes {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.public-filters {
  display: grid;
  gap: var(--space-2);
}

.public-search :deep(input),
.public-diet {
  width: 100%;
}

.public-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.public-tag {
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: 999px;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
    outline-offset: 2px;
  }
}

.public-tag--on {
  border-color: var(--p-primary-color);
  background: var(--p-highlight-background);
  color: var(--p-highlight-color);
  font-weight: 700;
}

.public-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
  gap: var(--space-3);
}

.public-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: inherit;
  text-decoration: none;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  box-shadow: var(--shadow-md);

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
    outline-offset: 2px;
  }
}

@media (hover: hover) {
  .public-card:hover {
    box-shadow: var(--shadow-lg);
  }
}

.public-card-cover {
  aspect-ratio: 4 / 3;
  background: var(--p-surface-100);

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.p-dark .public-card-cover {
  background: var(--p-surface-800);
}

.public-card-cover--empty {
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-4xl);
}

.public-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
}

.public-card-title {
  font-size: var(--font-size-xl);
  line-height: 1.15;
}

.public-card-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.public-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.public-card-diet {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-green-700);
}

.p-dark .public-card-diet {
  color: var(--p-green-400);
}

.public-card-author {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
}

.public-card-avatar {
  --avatar-size: 1.4rem;
}

.public-more {
  display: flex;
  justify-content: center;
}

@media (min-width: $bp-sm) {
  .public-filters {
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  }
}

// The list is not printed either; the page says how to print instead.
@media print {
  .public-recipes {
    display: none;
  }
}
</style>
