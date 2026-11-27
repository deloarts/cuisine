<script setup lang="ts">
/**
 * Drafts waiting for review: recipes written but not yet published, and the
 * ones an agent imported. A cook opens one, checks it in the editor and
 * publishes it; nothing an agent creates reaches the cookbook before that.
 * Importing a `.cui` file lands its recipes here as well.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  listRecipes,
  publishRecipe,
  type RecipeSummaryResponse,
} from '@/features/recipes/api/recipes'
import { formatDay } from '@/features/recipes/utils/dates'
import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { imageUrl } from '@/shared/components/recipes/recipeImage'
import RichText from '@/shared/components/richText/RichText.vue'
import RecipeImport from '@/shared/cookbook/RecipeImport.vue'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, locale } = useI18n()
const toast = useAppToast()

const drafts = ref<RecipeSummaryResponse[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    drafts.value = (await listRecipes({ status: 'drafts', sort: 'changed', limit: 100 })).items
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function publish(recipe: RecipeSummaryResponse) {
  try {
    await publishRecipe(recipe.id)
    toast.success(t('recipes.detail.published'))
    drafts.value = drafts.value.filter((r) => r.id !== recipe.id)
  } catch (err) {
    toast.error(err)
  }
}

onMounted(load)
</script>

<template>
  <section class="drafts">
    <PageHeader :title="t('recipes.drafts.title')" />
    <p class="hint">{{ t('recipes.drafts.hint') }}</p>
    <RecipeImport outlined @imported="load" />

    <ul v-if="drafts.length" class="draft-list">
      <ContentCard as="li" v-for="recipe in drafts" :key="recipe.id" class="draft">
        <img
          v-if="recipe.cover_image_id"
          :src="imageUrl(recipe.cover_image_id)"
          alt=""
          class="draft-thumb"
        />
        <span v-else class="draft-thumb draft-thumb--empty mdi mdi-silverware-fork-knife" aria-hidden="true" />
        <div class="draft-text">
          <RouterLink :to="{ name: 'recipe', params: { id: recipe.id } }" class="draft-title">
            {{ recipe.title }}
          </RouterLink>
          <RichText v-if="recipe.description" class="draft-description" :text="recipe.description" />
          <p class="draft-meta">
            <Tag
              v-if="recipe.created_via === 'mcp'"
              :value="t('recipes.createdViaMcp')"
              severity="secondary"
              icon="mdi mdi-robot-outline"
            />
            <span v-if="recipe.owner">{{ recipe.owner.display_name }}</span>
            <span>{{ t('recipes.drafts.changed', { date: formatDay(recipe.changed, locale) }) }}</span>
          </p>
        </div>
        <div class="draft-actions">
          <RouterLink v-if="recipe.can_edit" :to="{ name: 'recipe-edit', params: { id: recipe.id } }" custom>
            <template #default="{ navigate }">
              <Button
                :label="t('recipes.drafts.review')"
                icon="mdi mdi-pencil-outline"
                severity="secondary"
                outlined
                @click="navigate"
              />
            </template>
          </RouterLink>
          <Button
            v-if="recipe.can_edit"
            :label="t('recipes.detail.publish')"
            icon="mdi mdi-earth"
            @click="publish(recipe)"
          />
        </div>
      </ContentCard>
    </ul>
    <SkeletonRegion v-else-if="loading" class="draft-list" testid="drafts-skeleton">
      <ContentCard v-for="n in 3" :key="n" class="draft">
        <Skeleton size="4rem" />
        <div class="draft-skeleton-text">
          <Skeleton width="55%" height="1.25rem" />
          <SkeletonLines :lines="2" height="0.75rem" />
          <Skeleton width="40%" height="0.75rem" />
        </div>
        <div class="draft-actions">
          <Skeleton width="8rem" height="2.75rem" />
          <Skeleton width="7rem" height="2.75rem" />
        </div>
      </ContentCard>
    </SkeletonRegion>
    <ContentCard v-else>
      <EmptyState :message="t('recipes.drafts.empty')" icon="mdi mdi-check-all" />
    </ContentCard>
  </section>
</template>

<style scoped lang="scss">
.drafts {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

// Phone first: picture and text side by side, the actions underneath.
.draft {
  display: grid;
  grid-template-columns: 4rem minmax(0, 1fr);
  gap: var(--space-3);
  align-items: center;
  height: auto;
}

.draft-thumb {
  width: 4rem;
  height: 4rem;
  border-radius: var(--p-border-radius-md);
  object-fit: cover;
}

.draft-thumb--empty {
  display: grid;
  place-items: center;
  background: var(--p-surface-100);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-2xl);
}

.draft-title {
  font-weight: 700;
  font-size: var(--font-size-lg);
  color: inherit;
}

// A long imported description shows its first lines only.
.draft-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.draft-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-3);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.draft-skeleton-text {
  display: grid;
  gap: var(--space-2);
}

.draft-actions {
  display: flex;
  flex-wrap: wrap;
  grid-column: 1 / -1;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .draft {
    grid-template-columns: 4rem minmax(0, 1fr) auto;
  }

  .draft-actions {
    grid-column: auto;
  }
}
</style>
