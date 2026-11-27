<script setup lang="ts">
/**
 * What everyone cooked, month by month. Each day shows who cooked (as
 * their avatars on a phone, with the recipe names on a wide screen); tapping a
 * day lists its meals below the calendar. Filters narrow it to one person
 * or one recipe, so "what did I cook a year ago" is two taps away.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import PageHeader from '@/shared/components/PageHeader.vue'
import PersonSelect from '@/shared/components/PersonSelect.vue'
import ListItemSkeleton from '@/shared/components/skeleton/ListItemSkeleton.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import RecipePicker from '@/shared/cookbook/RecipePicker.vue'
import type { DirectoryUserResponse, RecipeSummaryResponse } from '@/shared/cookbook/types'
import CookEventDialog from '@/features/cooked/components/CookEventDialog.vue'
import { byDate, monthGrid, monthOf, monthRange, shiftMonth, weekdayNames } from '@/features/cooked/month'
import { isoDate, parseIsoDate } from '@/shared/cookbook/dates'
import {
  createCookEvent,
  deleteCookEvent,
  listCookEvents,
  listPeople,
  updateCookEvent,
  type CookEvent,
} from '@/features/cooked/api/cooked'
import { useAppToast } from '@/core/composables/useAppToast'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t, locale } = useI18n()
const toast = useAppToast()

const today = isoDate(new Date())
const month = ref(monthOf(today))
const selected = ref(today)
const events = ref<CookEvent[]>([])
const loading = ref(false)
const people = ref<DirectoryUserResponse[]>([])
const userId = ref<string | null>(null)
const recipe = ref<RecipeSummaryResponse | null>(null)

const dialog = ref(false)
const editing = ref<CookEvent | null>(null)
const saving = ref(false)

const tag = computed(() => contentLocaleOf(locale.value))
const grid = computed(() => monthGrid(month.value))
const eventsByDate = computed(() => byDate(events.value))
const weekdays = computed(() => weekdayNames(tag.value))
const monthLabel = computed(() =>
  new Intl.DateTimeFormat(tag.value, { month: 'long', year: 'numeric' }).format(parseIsoDate(`${month.value}-01`)),
)
const selectedEvents = computed(() => eventsByDate.value.get(selected.value) ?? [])
const selectedLabel = computed(() =>
  new Intl.DateTimeFormat(tag.value, { dateStyle: 'full' }).format(parseIsoDate(selected.value)),
)
const recipeId = computed(() => (recipe.value && typeof recipe.value === 'object' ? recipe.value.id : null))

// The month and filters the shown events belong to. While another month or
// filter loads, the calendar shows placeholders rather than an empty month
// that fills in a moment later; a reload of the same month keeps its events.
const shownKey = ref<string | null>(null)
const currentKey = computed(() => `${month.value}|${userId.value ?? ''}|${recipeId.value ?? ''}`)
const placeholders = computed(() => loading.value && shownKey.value !== currentKey.value)

async function load() {
  loading.value = true
  const key = currentKey.value
  const { from, to } = monthRange(month.value)
  try {
    events.value = await listCookEvents({ date_from: from, date_to: to, user_id: userId.value, recipe_id: recipeId.value })
    shownKey.value = key
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function shift(by: number) {
  month.value = shiftMonth(month.value, by)
  selected.value = `${month.value}-01`
}

function goToday() {
  month.value = monthOf(today)
  selected.value = today
}

function sameDayLastYear() {
  const d = parseIsoDate(selected.value)
  d.setFullYear(d.getFullYear() - 1)
  selected.value = isoDate(d)
  month.value = monthOf(selected.value)
}

function select(date: string) {
  selected.value = date
  if (monthOf(date) !== month.value) month.value = monthOf(date)
}

function cellLabel(date: string): string {
  const count = eventsByDate.value.get(date)?.length ?? 0
  const day = new Intl.DateTimeFormat(tag.value, { dateStyle: 'long' }).format(parseIsoDate(date))
  return count ? t('cooked.cellLabel', { day, count }) : day
}

function openNew() {
  editing.value = null
  dialog.value = true
}

function openEdit(event: CookEvent) {
  editing.value = event
  dialog.value = true
}

async function run(action: () => Promise<unknown>) {
  saving.value = true
  try {
    await action()
    dialog.value = false
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

const create = (value: { recipe_id: string; cooked_on: string; servings: number; note: string }) =>
  run(() => createCookEvent(value))
const update = (value: { cooked_on: string; servings: number; note: string }) =>
  run(() => updateCookEvent(editing.value?.id ?? '', value))
const remove = () => run(() => deleteCookEvent(editing.value?.id ?? ''))

watch([month, userId, recipeId], () => void load())
onMounted(async () => {
  void load()
  try {
    people.value = await listPeople()
  } catch {
    people.value = []
  }
})
</script>

<template>
  <section class="cooked">
    <PageHeader :title="t('nav.cooked')">
      <Button :label="t('cooked.logEvent')" icon="mdi mdi-plus" @click="openNew" />
    </PageHeader>

    <div class="filters">
      <PersonSelect
        v-model="userId"
        :people="people"
        :placeholder="t('cooked.everyone')"
        :aria-label="t('cooked.person')"
        show-clear
        fluid
      />
      <RecipePicker v-model="recipe" input-id="cooked-recipe" :placeholder="t('cooked.anyRecipe')" />
    </div>

    <ContentCard class="calendar" :aria-busy="loading">
      <nav class="month-nav" :aria-label="t('cooked.monthNav')">
        <Button icon="mdi mdi-chevron-left" text rounded :aria-label="t('cooked.previousMonth')" @click="shift(-1)" />
        <h2 class="month-label">{{ monthLabel }}</h2>
        <Button icon="mdi mdi-chevron-right" text rounded :aria-label="t('cooked.nextMonth')" @click="shift(1)" />
        <Button v-if="month !== monthOf(today)" :label="t('cooked.today')" text size="small" @click="goToday" />
      </nav>
      <div class="grid" role="grid" :aria-label="monthLabel">
        <div class="grid-row grid-head" role="row">
          <span v-for="name in weekdays" :key="name" role="columnheader" class="weekday">{{ name }}</span>
        </div>
        <div v-for="(week, wi) in grid" :key="wi" class="grid-row" role="row">
          <button
            v-for="cell in week"
            :key="cell.date"
            type="button"
            role="gridcell"
            class="cell"
            :class="{
              'cell--out': !cell.inMonth,
              'cell--today': cell.date === today,
              'cell--selected': cell.date === selected,
            }"
            :aria-selected="cell.date === selected"
            :aria-label="cellLabel(cell.date)"
            @click="select(cell.date)"
          >
            <span class="cell-day">{{ Number(cell.date.slice(8)) }}</span>
            <span class="cell-badges">
              <Skeleton v-if="placeholders && cell.inMonth" size="1.4rem" shape="circle" />
              <UserAvatar
                v-for="event in (eventsByDate.get(cell.date) ?? []).slice(0, 3)"
                :key="event.id"
                class="badge"
                :class="{ 'badge--own': event.is_own }"
                :name="event.user?.display_name ?? '?'"
                :avatar-id="event.user?.avatar_id"
              />
            </span>
            <span class="cell-titles">
              <span v-for="event in (eventsByDate.get(cell.date) ?? []).slice(0, 2)" :key="event.id" class="cell-title">
                {{ event.recipe?.title }}
              </span>
            </span>
          </button>
        </div>
      </div>
    </ContentCard>

    <ContentCard class="day">
      <div class="day-head">
        <h3 class="day-title">{{ selectedLabel }}</h3>
        <Button :label="t('cooked.lastYear')" icon="mdi mdi-history" text size="small" @click="sameDayLastYear" />
      </div>
      <SkeletonRegion v-if="placeholders" class="day-events" testid="cooked-skeleton">
        <ListItemSkeleton v-for="n in 2" :key="n" thumb="2rem" round />
      </SkeletonRegion>
      <p v-else-if="!selectedEvents.length" class="empty-note">{{ t('cooked.nothing') }}</p>
      <ul v-else class="day-events">
        <li v-for="event in selectedEvents" :key="event.id" class="day-event">
          <UserAvatar
            class="badge badge--large"
            :class="{ 'badge--own': event.is_own }"
            :name="event.user?.display_name ?? '?'"
            :avatar-id="event.user?.avatar_id"
          />
          <span class="day-event-text">
            <RouterLink v-if="event.recipe" :to="`/recipes/${event.recipe.id}`" class="day-event-recipe">
              {{ event.recipe.title }}
            </RouterLink>
            <small class="text-muted">
              {{ event.user?.display_name }} · {{ t('cooked.servingsShort', { count: event.servings }) }}
            </small>
            <span v-if="event.note" class="day-event-note">{{ event.note }}</span>
          </span>
          <Button
            v-if="event.is_own"
            icon="mdi mdi-pencil"
            text
            rounded
            :aria-label="t('common.edit')"
            @click="openEdit(event)"
          />
        </li>
      </ul>
    </ContentCard>

    <CookEventDialog
      v-model:visible="dialog"
      :date="selected"
      :editing="editing"
      :saving="saving"
      @create="create"
      @update="update"
      @remove="remove"
    />
  </section>
</template>

<style scoped lang="scss">
.cooked {
  // The hairline between calendar cells and inside the small badges.
  --calendar-hairline: 2px;
}

.filters {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.calendar {
  margin-bottom: var(--space-3);
  padding: var(--space-2);
}

.month-nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.month-label {
  margin: 0;
  font-size: var(--font-size-2xl);
}

.grid {
  display: grid;
  gap: var(--calendar-hairline);
}

.grid-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: var(--calendar-hairline);
}

.weekday {
  padding: var(--space-1) 0;
  font-size: var(--font-size-xs);
  text-align: center;
  color: var(--p-text-muted-color);
}

.cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--calendar-hairline);
  min-height: 3rem;
  padding: var(--space-1) var(--calendar-hairline);
  border: 1px solid transparent;
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-hover-background);
  color: inherit;
  font: inherit;
  cursor: pointer;
  overflow: hidden;
}

.cell--out {
  opacity: 0.45;
}

.cell--today .cell-day {
  color: var(--p-primary-color);
  font-weight: 800;
}

.cell--selected {
  border-color: var(--p-primary-color);
}

.cell-day {
  font-size: var(--font-size-sm);
}

.cell-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--calendar-hairline);
}

// Each cook's avatar, or their initials without one. The viewer's own
// entries keep the primary colour and get a ring, so they stand out even
// behind a photo.
.badge {
  --avatar-size: 1.4rem;
  --avatar-background: var(--p-content-border-color);
  --avatar-color: var(--p-text-color);
}

.badge--large {
  --avatar-size: 2rem;
}

.badge--own {
  --avatar-background: var(--p-primary-color);
  --avatar-color: var(--p-primary-contrast-color);
  box-shadow: 0 0 0 var(--calendar-hairline) var(--p-primary-color);
}

.cell-titles {
  display: none;
}

.day {
  display: grid;
  gap: var(--space-2);
}

.day-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.day-title {
  margin: 0;
}

.day-events {
  display: grid;
  gap: var(--space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.day-event {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.day-event-text {
  display: grid;
}

.day-event-recipe {
  font-weight: 700;
  color: inherit;
}

.day-event-note {
  font-style: italic;
}

@media (min-width: $bp-sm) {
  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cell {
    align-items: stretch;
    min-height: 5.5rem;
    text-align: left;
  }

  .cell-badges {
    justify-content: flex-start;
  }

  .cell-titles {
    display: grid;
  }

  .cell-title {
    overflow: hidden;
    font-size: var(--font-size-xs);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
