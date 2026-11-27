<script setup lang="ts">
/**
 * The start page: a greeting, the food fact of the day, what the others
 * cooked lately, the reader's
 * shopping lists, then the newest recipes, what is in season now and the
 * reader's favourites. One request fills the cooking and recipe sections and
 * a second one the shopping lists; until they answer, the sections stand with
 * their titles and skeleton rows and cards.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import {
  getHome,
  getShoppingLists,
  setFavourite,
  type HomeResponse,
  type ShoppingListSummary,
} from '@/features/home/api/home'
import CookEventItem from '@/features/home/components/CookEventItem.vue'
import FoodFactCard from '@/features/home/components/FoodFactCard.vue'
import ShoppingListItem from '@/features/home/components/ShoppingListItem.vue'
import EmptyState from '@/shared/components/EmptyState.vue'
import RecipeCard from '@/shared/components/recipes/RecipeCard.vue'
import RecipeCardSkeleton from '@/shared/components/recipes/RecipeCardSkeleton.vue'
import ListItemSkeleton from '@/shared/components/skeleton/ListItemSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import type { RecipeSummaryResponse } from '@/shared/cookbook/types'
import { useHousehold } from '@/shared/household/useHousehold'

import { appLoadPick } from '@/features/home/homeQuestion'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
// The nickname when the user goes by it, otherwise the first word of the full name.
const firstName = computed(() => {
  const user = currentUser.user
  if (!user) return ''
  return user.show_nickname && user.nickname ? user.nickname : (user.full_name.split(' ')[0] ?? '')
})

// One of the subtitles under the greeting, drawn once per app load so it
// stays put while the user moves around and changes on the next visit.
const QUESTIONS = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10', 'q11', 'q12'] as const
const QUESTION = QUESTIONS[appLoadPick(QUESTIONS.length)]!

const greeting = computed(() => {
  const hour = new Date().getHours()
  const part = hour < 11 ? 'morning' : hour < 18 ? 'day' : 'evening'
  return t(`home.greeting.${part}`, { name: firstName.value })
})

const home = ref<HomeResponse | null>(null)
const loading = ref(true)
// How many placeholder cards a recipe row shows while the page loads.
const SKELETON_CARDS = 4

async function load() {
  try {
    home.value = await getHome()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

// The shopping lists load on their own, so a slow or failing list request
// never holds back the recipes. The household's list comes first, then the
// most recently used ones.
const SHOPPING_LISTS_SHOWN = 3
const shoppingLists = ref<ShoppingListSummary[] | null>(null)
const { shoppingListId, load: loadHousehold } = useHousehold()
const shownLists = computed(() =>
  [...(shoppingLists.value ?? [])]
    .sort(
      (a, b) =>
        Number(b.id === shoppingListId.value) - Number(a.id === shoppingListId.value) ||
        b.last_activity_at.localeCompare(a.last_activity_at),
    )
    .slice(0, SHOPPING_LISTS_SHOWN),
)

async function loadShopping() {
  try {
    shoppingLists.value = await getShoppingLists()
  } catch (err) {
    shoppingLists.value = []
    toast.error(err)
  }
}

async function toggleFavourite(recipe: RecipeSummaryResponse) {
  const next = !recipe.is_favourite
  // The same recipe can sit in several rows, so every copy flips together.
  const copies = [
    ...(home.value?.favourites ?? []),
    ...(home.value?.in_season ?? []),
    ...(home.value?.newest ?? []),
  ].filter((r) => r.id === recipe.id)
  copies.forEach((r) => (r.is_favourite = next))
  try {
    await setFavourite(recipe.id, next)
    if (home.value && !next) {
      home.value.favourites = home.value.favourites.filter((r) => r.id !== recipe.id)
    }
  } catch (err) {
    copies.forEach((r) => (r.is_favourite = !next))
    toast.error(err)
  }
}

onMounted(() => {
  void load()
  void loadShopping()
  loadHousehold().catch(() => undefined)
})
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>{{ greeting }}</h1>
      <p class="hero-question">{{ t(`home.questions.${QUESTION}`) }}</p>
      <div class="hero-actions">
        <RouterLink :to="{ name: 'recipes' }" custom>
          <template #default="{ navigate }">
            <Button
              :label="t('home.browse')"
              @click="navigate"
            />
          </template>
        </RouterLink>
        <RouterLink :to="{ name: 'meal-plan' }" custom>
          <template #default="{ navigate }">
            <Button
              :label="t('home.plan')"
              severity="secondary"
              outlined
              @click="navigate"
            />
          </template>
        </RouterLink>
      </div>
    </section>

    <FoodFactCard v-if="home?.food_fact" :fact="home.food_fact" />

    <div v-if="home || loading" class="home-columns">
      <ContentCard as="section" class="home-section" data-testid="home-recentlyCooked">
        <h2 class="section-title">
          {{ t('home.sections.recentlyCooked') }}
        </h2>
        <SkeletonRegion v-if="!home" class="event-list event-list--skeleton" testid="home-skeleton">
          <ListItemSkeleton v-for="n in 3" :key="n" thumb="3.25rem" />
        </SkeletonRegion>
        <div v-else-if="home.recently_cooked.length" class="event-list">
          <CookEventItem v-for="event in home.recently_cooked" :key="event.id" :event="event" />
        </div>
        <EmptyState
          v-else
          :message="t('home.sections.recentlyCookedEmpty')"
          icon="mdi mdi-pot-steam-outline"
        />
        <RouterLink :to="{ name: 'cooked' }" class="section-more">
          {{ t('home.sections.toCalendar') }}
          <span class="mdi mdi-arrow-right" aria-hidden="true" />
        </RouterLink>
      </ContentCard>

      <ContentCard as="section" class="home-section" data-testid="home-shopping">
        <h2 class="section-title">
          {{ t('home.sections.shopping') }}
        </h2>
        <SkeletonRegion v-if="!shoppingLists" class="event-list event-list--skeleton" silent>
          <ListItemSkeleton v-for="n in 2" :key="n" thumb="3.25rem" />
        </SkeletonRegion>
        <div v-else-if="shownLists.length" class="event-list">
          <ShoppingListItem
            v-for="list in shownLists"
            :key="list.id"
            :list="list"
            :household="list.id === shoppingListId"
          />
        </div>
        <EmptyState v-else :message="t('home.sections.shoppingEmpty')" icon="mdi mdi-cart-outline" />
        <RouterLink :to="{ name: 'shopping' }" class="section-more">
          {{ t('home.sections.toShopping') }}
          <span class="mdi mdi-arrow-right" aria-hidden="true" />
        </RouterLink>
      </ContentCard>
    </div>

    <section v-if="home || loading" class="home-row" data-testid="home-newest">
      <h2 class="section-title">
        {{ t('home.sections.newest') }}
      </h2>
      <SkeletonRegion v-if="!home" class="card-row" silent>
        <RecipeCardSkeleton v-for="n in SKELETON_CARDS" :key="n" />
      </SkeletonRegion>
      <div v-else-if="home.newest.length" class="card-row">
        <RecipeCard
          v-for="recipe in home.newest"
          :key="recipe.id"
          :recipe="recipe"
          :max-tags="2"
          @toggle-favourite="toggleFavourite"
        />
      </div>
      <p v-else class="hint">{{ t('home.sections.newestEmpty') }}</p>
    </section>

    <section v-if="home?.in_season.length" class="home-row" data-testid="home-inSeason">
      <h2 class="section-title">
        {{ t('home.sections.inSeason') }}
      </h2>
      <div class="card-row">
        <RecipeCard
          v-for="recipe in home.in_season"
          :key="recipe.id"
          :recipe="recipe"
          :max-tags="2"
          @toggle-favourite="toggleFavourite"
        />
      </div>
      <RouterLink :to="{ name: 'recipes', query: { season: '1' } }" class="section-more">
        {{ t('home.sections.inSeasonMore') }}
        <span class="mdi mdi-arrow-right" aria-hidden="true" />
      </RouterLink>
    </section>

    <section v-if="home || loading" class="home-row" data-testid="home-favourites">
      <h2 class="section-title">
        {{ t('home.sections.favourites') }}
      </h2>
      <SkeletonRegion v-if="!home" class="card-row" silent>
        <RecipeCardSkeleton v-for="n in SKELETON_CARDS" :key="n" />
      </SkeletonRegion>
      <div v-else-if="home.favourites.length" class="card-row">
        <RecipeCard
          v-for="recipe in home.favourites"
          :key="recipe.id"
          :recipe="recipe"
          :max-tags="2"
          @toggle-favourite="toggleFavourite"
        />
      </div>
      <p v-else class="hint">{{ t('home.sections.favouritesEmpty') }}</p>
    </section>
  </div>
</template>

<style scoped lang="scss">
.home {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) 0 0;

  h1 {
    font-size: clamp(2rem, 7vw, 2.75rem);
  }
}

.hero-question {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-lg);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.home-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-4);
}

.home-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: auto;
}

.section-title {
  font-size: var(--font-size-2xl);
}

.event-list {
  display: flex;
  flex-direction: column;
  margin: 0 calc(-1 * var(--space-2));
}

.section-more {
  display: inline-flex;
  align-self: flex-start;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  color: var(--p-primary-color);
  font-weight: 700;
  text-decoration: none;
}

.home-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

// Phone first: the recipes scroll sideways, each card a bit narrower than
// the screen so the next one peeks in; from a tablet up they form a grid.
.card-row {
  display: grid;
  grid-auto-columns: minmax(11rem, 70%);
  grid-auto-flow: column;
  gap: var(--space-3);
  margin: 0 calc(-1 * var(--space-3));
  padding: var(--space-1) var(--space-3) var(--space-3);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  // The snap keeps the page gutter instead of pulling a card to the edge.
  scroll-padding-inline: var(--space-3);
  scrollbar-width: thin;

  > * {
    scroll-snap-align: start;
  }
}

// Each placeholder row takes the padding of a real event row.
.event-list--skeleton > * {
  padding: var(--space-2);
}

@media (min-width: $bp-sm) {
  .home-columns {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .card-row {
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    grid-auto-flow: row;
    margin: 0;
    padding: 0;
    overflow: visible;
  }
}
</style>
