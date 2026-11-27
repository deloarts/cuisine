<script setup lang="ts">
/**
 * Browsing the cookbook: a photo grid with search and filter chips. The
 * filters live in the URL, so going back from a recipe lands on the same
 * list.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { watchDebounced } from '@vueuse/core'

import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import {
  getMyHousehold,
  listRecipes,
  listTags,
  setFavourite,
  type RecipeListQuery,
  type RecipeSummaryResponse,
  type TagResponse,
} from '@/features/recipes/api/recipes'
import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import RecipeCard from '@/shared/components/recipes/RecipeCard.vue'
import RecipeCardSkeleton from '@/shared/components/recipes/RecipeCardSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import DietGuestFilters from '@/features/recipes/components/DietGuestFilters.vue'
import ContentCard from '@/shared/components/ContentCard.vue'

const PAGE_SIZE = 24
// The placeholder cards of a first load: enough to fill the first screen.
const SKELETON_CARDS = 8
const QUICK_MINUTES = 30

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()

const canWrite = computed(
  () =>
    currentUser.hasPermission(Permission.WRITE_RECIPES) ||
    currentUser.hasPermission(Permission.MANAGE_RECIPES),
)

const queryString = (key: string) => (typeof route.query[key] === 'string' ? route.query[key] : '')
const queryList = (key: string) => {
  const value = route.query[key]
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === 'string')
  return typeof value === 'string' && value ? [value] : []
}

const search = ref(queryString('q'))
const favourites = ref(route.query.favourites === '1')
const mine = ref(route.query.mine === '1')
const quick = ref(route.query.quick === '1')
const inSeason = ref(route.query.season === '1')
const kitchenReady = ref(route.query.kitchen === '1')
// The kitchen filter only means something once the reader's kitchen is set
// up, which the recipes say through `kitchen_ready` (null before).
const kitchenSetUp = ref(false)
const difficulty = ref(queryString('difficulty'))
const tagIds = ref<string[]>(queryList('tag'))
const diets = ref<string[]>(queryList('diet'))
const guests = ref<string[]>(queryList('guest'))
const hideUnsuitable = ref(route.query.hideUnsuitable === '1')
// Household members come to dinner by default. Once the reader removes them
// all, `noGuests` in the URL keeps it that way.
const householdIds = ref<string[]>([])
const noGuests = ref(route.query.noGuests === '1')
// The who-is-eating panel opens by itself when the URL already filters by it.
const peopleOpen = ref(diets.value.length > 0 || guests.value.length > 0)
const peopleCount = computed(() => diets.value.length + guests.value.length)
// The chosen guests travel to the recipe page, so it shows the same flag.
const cardQuery = computed(() => {
  const query: Record<string, string[]> = {}
  if (guests.value.length) query.guest = guests.value
  return query
})

const recipes = ref<RecipeSummaryResponse[]>([])
const total = ref(0)
// True from the start: the first load waits for the household preselection,
// and the skeleton grid stands in until it answers.
const loading = ref(true)
const tags = ref<TagResponse[]>([])
// A few meal tags stay one tap away as chips, plus whatever is chosen; every
// tag is in the picker, so a long tag list never becomes a wall of chips.
const MAX_TAG_CHIPS = 6
const chipTags = computed(() => {
  const meal = tags.value.filter((tag) => tag.kind === 'meal').slice(0, MAX_TAG_CHIPS)
  const chosen = tags.value.filter((tag) => tagIds.value.includes(tag.id) && !meal.includes(tag))
  return [...meal, ...chosen]
})

const difficulties = computed(() => [
  { value: '', label: t('recipes.filters.anyDifficulty') },
  { value: 'easy', label: t('recipes.difficulty.easy') },
  { value: 'medium', label: t('recipes.difficulty.medium') },
  { value: 'hard', label: t('recipes.difficulty.hard') },
])

const hasFilters = computed(
  () =>
    search.value.trim() !== '' ||
    favourites.value ||
    mine.value ||
    quick.value ||
    inSeason.value ||
    kitchenReady.value ||
    difficulty.value !== '' ||
    tagIds.value.length > 0 ||
    diets.value.length > 0 ||
    // Guests only narrow the list once their unsuitable recipes are hidden.
    (guests.value.length > 0 && hideUnsuitable.value),
)

function buildQuery(offset: number): RecipeListQuery {
  return {
    search: search.value.trim() || null,
    favourites: favourites.value,
    mine: mine.value,
    max_minutes: quick.value ? QUICK_MINUTES : null,
    in_season: inSeason.value,
    only_kitchen_ready: kitchenReady.value,
    difficulty: (difficulty.value || null) as RecipeListQuery['difficulty'],
    tag_id: tagIds.value,
    diets: diets.value as RecipeListQuery['diets'],
    guests: guests.value,
    hide_unsuitable_for_guests: guests.value.length > 0 && hideUnsuitable.value,
    status: 'published',
    sort: 'newest',
    limit: PAGE_SIZE,
    offset,
  }
}

async function load(append = false) {
  loading.value = true
  try {
    const page = await listRecipes(buildQuery(append ? recipes.value.length : 0))
    recipes.value = append ? [...recipes.value, ...page.items] : page.items
    total.value = page.total
    if (page.items.some((r) => r.kitchen_ready !== null)) kitchenSetUp.value = true
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function syncUrl() {
  const query: Record<string, string | string[]> = {}
  if (search.value.trim()) query.q = search.value.trim()
  if (favourites.value) query.favourites = '1'
  if (mine.value) query.mine = '1'
  if (quick.value) query.quick = '1'
  if (inSeason.value) query.season = '1'
  if (kitchenReady.value) query.kitchen = '1'
  if (difficulty.value) query.difficulty = difficulty.value
  if (tagIds.value.length) query.tag = tagIds.value
  if (diets.value.length) query.diet = diets.value
  if (guests.value.length) query.guest = guests.value
  if (guests.value.length && hideUnsuitable.value) query.hideUnsuitable = '1'
  if (!guests.value.length && householdIds.value.length) query.noGuests = '1'
  void router.replace({ query })
}

function refresh() {
  syncUrl()
  void load()
}

watch(
  [favourites, mine, quick, inSeason, kitchenReady, difficulty, tagIds, diets, guests, hideUnsuitable],
  refresh,
  { deep: true },
)
watchDebounced(search, refresh, { debounce: 300 })

function toggleTag(id: string) {
  tagIds.value = tagIds.value.includes(id)
    ? tagIds.value.filter((t) => t !== id)
    : [...tagIds.value, id]
}

function clearFilters() {
  search.value = ''
  favourites.value = false
  mine.value = false
  quick.value = false
  inSeason.value = false
  kitchenReady.value = false
  difficulty.value = ''
  tagIds.value = []
  diets.value = []
  // The guests stay: they say who is eating, not what to filter by.
  hideUnsuitable.value = false
}

async function toggleFavourite(recipe: RecipeSummaryResponse) {
  const next = !recipe.is_favourite
  recipe.is_favourite = next
  try {
    await setFavourite(recipe.id, next)
    if (favourites.value && !next) recipes.value = recipes.value.filter((r) => r.id !== recipe.id)
  } catch (err) {
    recipe.is_favourite = !next
    toast.error(err)
  }
}

async function preselectHousehold() {
  try {
    const { household } = await getMyHousehold()
    householdIds.value = (household?.members ?? [])
      .map((m) => m.id)
      .filter((id) => id !== currentUser.user?.id)
  } catch {
    householdIds.value = []
  }
  if (!noGuests.value && guests.value.length === 0 && householdIds.value.length) {
    // The watcher on guests reloads the list with them.
    guests.value = [...householdIds.value]
    return true
  }
  return false
}

onMounted(async () => {
  if (!(await preselectHousehold())) void load()
  try {
    tags.value = await listTags()
  } catch (err) {
    toast.error(err)
  }
})
</script>

<template>
  <section class="browse">
    <PageHeader :title="t('nav.recipes')">
      <RouterLink v-if="canWrite" :to="{ name: 'recipe-drafts' }" custom>
        <template #default="{ navigate }">
          <Button
            :label="t('recipes.drafts.title')"
            icon="mdi mdi-file-document-edit-outline"
            severity="secondary"
            outlined
            @click="navigate"
          />
        </template>
      </RouterLink>
      <RouterLink v-if="currentUser.hasPermission(Permission.WRITE_RECIPES)" :to="{ name: 'recipe-new' }" custom>
        <template #default="{ navigate }">
          <Button :label="t('recipes.newRecipe')" icon="mdi mdi-plus" @click="navigate" />
        </template>
      </RouterLink>
    </PageHeader>

    <div class="browse-filters">
      <label for="recipe-search" class="visually-hidden">{{ t('recipes.searchPlaceholder') }}</label>
      <IconField class="browse-search">
        <InputIcon class="mdi mdi-magnify" />
        <InputText
          id="recipe-search"
          v-model="search"
          type="search"
          :placeholder="t('recipes.searchPlaceholder')"
          fluid
        />
      </IconField>

      <div class="chip-row" role="group" :aria-label="t('recipes.filters.label')">
        <button
          type="button"
          class="chip"
          :class="{ 'chip--on': favourites }"
          :aria-pressed="favourites"
          @click="favourites = !favourites"
        >
          <span class="mdi mdi-heart-outline" aria-hidden="true" />
          {{ t('recipes.filters.favourites') }}
        </button>
        <button
          type="button"
          class="chip"
          :class="{ 'chip--on': quick }"
          :aria-pressed="quick"
          @click="quick = !quick"
        >
          <span class="mdi mdi-timer-outline" aria-hidden="true" />
          {{ t('recipes.filters.quick', { m: QUICK_MINUTES }) }}
        </button>
        <button
          type="button"
          class="chip"
          :class="{ 'chip--on': inSeason }"
          :aria-pressed="inSeason"
          @click="inSeason = !inSeason"
        >
          <span class="mdi mdi-sprout-outline" aria-hidden="true" />
          {{ t('recipes.filters.inSeason') }}
        </button>
        <button
          v-if="kitchenSetUp || kitchenReady"
          type="button"
          class="chip"
          :class="{ 'chip--on': kitchenReady }"
          :aria-pressed="kitchenReady"
          @click="kitchenReady = !kitchenReady"
        >
          <span class="mdi mdi-stove" aria-hidden="true" />
          {{ t('recipes.filters.kitchenReady') }}
        </button>
        <button
          v-if="canWrite"
          type="button"
          class="chip"
          :class="{ 'chip--on': mine }"
          :aria-pressed="mine"
          @click="mine = !mine"
        >
          <span class="mdi mdi-account-outline" aria-hidden="true" />
          {{ t('recipes.filters.mine') }}
        </button>
        <span id="recipe-difficulty-label" class="visually-hidden">
          {{ t('recipes.filters.difficulty') }}
        </span>
        <Select
          id="recipe-difficulty"
          v-model="difficulty"
          :options="difficulties"
          option-label="label"
          option-value="value"
          :placeholder="t('recipes.filters.difficulty')"
          class="chip-select"
          aria-labelledby="recipe-difficulty-label"
        />
        <button
          type="button"
          class="chip"
          :class="{ 'chip--on': peopleCount > 0 }"
          :aria-expanded="peopleOpen"
          aria-controls="diet-guest-panel"
          @click="peopleOpen = !peopleOpen"
        >
          <span class="mdi mdi-account-group-outline" aria-hidden="true" />
          {{ t('recipes.filters.people') }}
          <span v-if="peopleCount" class="chip-count">{{ peopleCount }}</span>
        </button>
        <span id="recipe-tags-label" class="visually-hidden">{{ t('recipes.filters.tags') }}</span>
        <MultiSelect
          v-if="tags.length"
          v-model="tagIds"
          :options="tags"
          option-label="name"
          option-value="id"
          :placeholder="t('recipes.filters.tags')"
          :max-selected-labels="0"
          :selected-items-label="t('recipes.filters.tagsChosen', { n: tagIds.length })"
          filter
          class="chip-select"
          aria-labelledby="recipe-tags-label"
        />
        <button
          v-for="tag in chipTags"
          :key="tag.id"
          type="button"
          class="chip"
          :class="{ 'chip--on': tagIds.includes(tag.id) }"
          :aria-pressed="tagIds.includes(tag.id)"
          @click="toggleTag(tag.id)"
        >
          {{ tag.name }}
        </button>
      </div>
    </div>

    <ContentCard v-show="peopleOpen" id="diet-guest-panel" class="browse-people">
      <DietGuestFilters
        v-model:diets="diets"
        v-model:guests="guests"
        v-model:hide-unsuitable="hideUnsuitable"
      />
    </ContentCard>

    <p v-if="!loading && recipes.length" class="browse-count">
      {{ t('recipes.count', { n: total }, total) }}
      <Button
        v-if="hasFilters"
        :label="t('recipes.filters.clear')"
        icon="mdi mdi-filter-remove-outline"
        text
        size="small"
        @click="clearFilters"
      />
    </p>

    <div v-if="recipes.length" class="recipe-grid">
      <RecipeCard
        v-for="recipe in recipes"
        :key="recipe.id"
        :recipe="recipe"
        :link-query="cardQuery"
        @toggle-favourite="toggleFavourite"
      />
    </div>
    <SkeletonRegion v-else-if="loading" class="recipe-grid" testid="recipes-skeleton">
      <RecipeCardSkeleton v-for="n in SKELETON_CARDS" :key="n" />
    </SkeletonRegion>
    <ContentCard v-else>
      <EmptyState
        :message="hasFilters ? t('recipes.emptyFiltered') : t('recipes.empty')"
        icon="mdi mdi-book-open-page-variant-outline"
      >
        <Button
          v-if="hasFilters"
          :label="t('recipes.filters.clear')"
          severity="secondary"
          @click="clearFilters"
        />
      </EmptyState>
    </ContentCard>

    <div v-if="recipes.length < total" class="browse-more">
      <Button
        :label="t('recipes.loadMore')"
        severity="secondary"
        outlined
        :loading="loading"
        @click="load(true)"
      />
    </div>
  </section>
</template>

<style scoped lang="scss">
.browse {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.browse-filters {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

// The chips scroll sideways on a phone instead of wrapping into a wall, and
// wrap once there is room for them.
.chip-row {
  display: flex;
  gap: var(--space-2);
  margin: 0 calc(-1 * var(--space-3));
  padding: var(--space-1) var(--space-3);
  overflow-x: auto;
  scrollbar-width: none;
}

.chip {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: 2rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  white-space: nowrap;
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }
}

.chip--on {
  border-color: var(--p-primary-color);
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.chip-count {
  display: inline-grid;
  place-items: center;
  min-width: 1.4rem;
  height: 1.4rem;
  border-radius: 1rem;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-size: var(--font-size-xs);
  font-weight: 800;
}

.browse-people {
  height: auto;
}

.chip-select {
  flex: 0 0 auto;
  border-radius: 2rem;
}

.browse-count {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

// Two cards side by side on a phone; from a tablet up as many as fit.
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.browse-more {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
}

@media (min-width: $bp-sm) {
  .browse-filters {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
  }

  .browse-search {
    flex: 1 1 18rem;
  }

  .chip-row {
    flex-wrap: wrap;
    margin: 0;
    padding: 0;
    overflow: visible;
  }

  .recipe-grid {
    grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
    gap: var(--space-4);
  }
}
</style>
