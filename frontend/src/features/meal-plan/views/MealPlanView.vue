<script setup lang="ts">
/**
 * The meal plan, one week at a time. A member of a household switches between
 * the household's plan and their personal one, which only they see; everyone
 * else has only the personal plan. On a phone the days run down
 * the page, each with its four meals; on a wide screen the week becomes a
 * grid of days side by side. "To shopping list" sends every planned recipe's
 * ingredients, scaled to the planned servings, to one of the user's lists.
 * From the large breakpoint on, suggested recipes sit below the week; one is
 * dragged onto a meal (planned at once with its base servings) or planned
 * through the meal dialog.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import PageHeader from '@/shared/components/PageHeader.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import { useLargeScreen } from '@/shared/composables/useWideScreen'
import { useHousehold } from '@/shared/household/useHousehold'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { boughtFor } from '@/shared/cookbook/subRecipes'
import type { MealSlot, RecipeSummaryResponse } from '@/shared/cookbook/types'
import {
  addRangeToShoppingList,
  addRecipeToShoppingList,
  deleteEntry,
  listEntries,
  planMeal,
  updateEntry,
  type MealPlanEntry as Entry,
} from '@/features/meal-plan/api/mealPlan'
import EntryDialog, { type EntryForm } from '@/features/meal-plan/components/EntryDialog.vue'
import SuggestionsPanel from '@/features/meal-plan/components/SuggestionsPanel.vue'
import { carriesSuggestion, readSuggestion } from '@/features/meal-plan/suggestionDrag'
import ToListDialog, { type ToListValue } from '@/features/meal-plan/components/ToListDialog.vue'
import { addDays, entriesFor, isoDate, parseIsoDate, SLOTS, startOfWeek, weekDays } from '@/features/meal-plan/week'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import ContentCard from '@/shared/components/ContentCard.vue'

type Scope = Schemas['MealPlanScope']

const { t, locale } = useI18n()
const toast = useAppToast()
const { household, load: loadHousehold } = useHousehold()

const today = isoDate(new Date())
const monday = ref(startOfWeek(today))
const days = computed(() => weekDays(monday.value))
const entries = ref<Entry[]>([])
const loading = ref(false)

const dialog = ref(false)
const dialogDate = ref(today)
const dialogSlot = ref<MealSlot>('dinner')
const editing = ref<Entry | null>(null)
const preset = ref<{ recipeId: string; recipeTitle: string; servings: number } | null>(null)
const largeScreen = useLargeScreen()
// The meal a suggestion is dragged over, as "day|slot".
const dropTarget = ref<string | null>(null)
const saving = ref(false)
const toListDialog = ref(false)

const chosenScope = ref<Scope>('household')
// Without a household there is only the personal plan, so no scope is sent
// and the backend picks it.
const scope = computed<Scope | undefined>(() => (household.value ? chosenScope.value : undefined))
const scopeOptions = computed(() => [
  { label: household.value?.name ?? '', value: 'household', icon: 'mdi mdi-home-heart' },
  { label: t('mealPlan.personalPlan'), value: 'personal', icon: 'mdi mdi-account' },
])

const tag = computed(() => contentLocaleOf(locale.value))
const rangeLabel = computed(() => {
  const fmt = new Intl.DateTimeFormat(tag.value, { day: 'numeric', month: 'short' })
  return `${fmt.format(parseIsoDate(days.value[0] ?? monday.value))} – ${fmt.format(parseIsoDate(days.value[6] ?? monday.value))}`
})
const plannedRecipes = computed(() => entries.value.filter((e) => e.recipe).length)
const plannedIds = computed(() => entries.value.flatMap((e) => (e.recipe ? [e.recipe.id] : [])))
const weekRecipes = computed(() =>
  entries.value.flatMap((e) => (e.recipe ? [{ id: e.recipe.id, title: e.recipe.title }] : [])),
)

function weekdayName(day: string): string {
  return new Intl.DateTimeFormat(tag.value, { weekday: 'long' }).format(parseIsoDate(day))
}

function dayDate(day: string): string {
  return new Intl.DateTimeFormat(tag.value, { day: 'numeric', month: 'numeric' }).format(parseIsoDate(day))
}

function dayName(day: string): string {
  return new Intl.DateTimeFormat(tag.value, { weekday: 'long', day: 'numeric', month: 'numeric' }).format(parseIsoDate(day))
}

// The week and plan the shown entries belong to. While another week loads,
// every meal shows a placeholder rather than an empty week that fills in a
// moment later; a reload of the same week after a change keeps its entries.
const shownKey = ref<string | null>(null)
const currentKey = computed(() => `${monday.value}|${scope.value ?? ''}`)
const placeholders = computed(() => loading.value && shownKey.value !== currentKey.value)

async function load() {
  loading.value = true
  const key = currentKey.value
  try {
    entries.value = await listEntries({ date_from: monday.value, date_to: addDays(monday.value, 6), scope: scope.value })
    shownKey.value = key
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function shift(weeks: number) {
  monday.value = addDays(monday.value, weeks * 7)
}

function openNew(day: string, slot: MealSlot) {
  editing.value = null
  preset.value = null
  dialogDate.value = day
  dialogSlot.value = slot
  dialog.value = true
}

function openEdit(entry: Entry) {
  editing.value = entry
  preset.value = null
  dialogDate.value = entry.plan_date
  dialogSlot.value = entry.slot as MealSlot
  dialog.value = true
}

/** Plans a suggestion through the dialog, on today when the week holds it. */
function openSuggestion(recipe: RecipeSummaryResponse, slot: MealSlot | null) {
  editing.value = null
  preset.value = { recipeId: recipe.id, recipeTitle: recipe.title, servings: recipe.base_servings }
  dialogDate.value = days.value.includes(today) ? today : monday.value
  dialogSlot.value = slot ?? 'dinner'
  dialog.value = true
}

function onDragOver(day: string, slot: MealSlot, event: DragEvent) {
  if (!carriesSuggestion(event)) return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
  dropTarget.value = `${day}|${slot}`
}

function onDragLeave(day: string, slot: MealSlot, event: DragEvent) {
  const into = event.relatedTarget
  if (into instanceof Node && (event.currentTarget as HTMLElement).contains(into)) return
  if (dropTarget.value === `${day}|${slot}`) dropTarget.value = null
}

/** A suggestion dropped on a meal is planned at once with its base servings. */
async function onDrop(day: string, slot: MealSlot, event: DragEvent) {
  dropTarget.value = null
  const recipe = readSuggestion(event)
  if (!recipe) return
  event.preventDefault()
  try {
    await planMeal({
      plan_date: day,
      slot,
      recipe_id: recipe.id,
      title: recipe.title,
      servings: recipe.servings,
      scope: scope.value,
    })
    toast.success(t('mealPlan.suggestions.planned', { title: recipe.title, slot: t(`mealPlan.slots.${slot}`), day: dayName(day) }))
    await load()
  } catch (err) {
    toast.error(err)
  }
}

const editingInfo = computed(() =>
  editing.value
    ? {
        recipeTitle: editing.value.recipe?.title ?? null,
        recipeId: editing.value.recipe?.id ?? null,
        title: editing.value.title,
        servings: editing.value.servings,
      }
    : null,
)

async function submit(form: EntryForm) {
  saving.value = true
  try {
    const entry = editing.value
    if (entry) {
      await updateEntry(entry.id, form)
    } else {
      await planMeal({ ...form, scope: scope.value })
    }
    dialog.value = false
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function remove() {
  const entry = editing.value
  if (!entry) return
  try {
    await deleteEntry(entry.id)
    dialog.value = false
    await load()
  } catch (err) {
    toast.error(err)
  }
}

/**
 * Without bought sub-recipes the backend expands the whole week in one call.
 * The week endpoint takes no "I'll buy it" choice, so with one each planned
 * recipe is added on its own, scaled to its servings, with the sub-recipes
 * bought for it.
 */
async function addWeek({ listId, bought, choices }: ToListValue): Promise<number> {
  if (!bought.length) {
    const { added } = await addRangeToShoppingList({
      date_from: monday.value,
      date_to: addDays(monday.value, 6),
      list_id: listId,
      scope: scope.value,
    })
    return added
  }
  let added = 0
  for (const entry of entries.value) {
    if (!entry.recipe) continue
    const result = await addRecipeToShoppingList(listId, {
      recipe_id: entry.recipe.id,
      servings: entry.servings,
      bought_sub_recipe_ids: boughtFor(entry.recipe.id, bought, choices),
    })
    added += result.added
  }
  return added
}

async function sendToList(value: ToListValue) {
  saving.value = true
  try {
    const added = await addWeek(value)
    toListDialog.value = false
    toast.success(t('mealPlan.sent', { count: added }))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

watch([monday, scope], () => void load())
onMounted(() => {
  void load()
  loadHousehold().catch(() => undefined)
})
</script>

<template>
  <section class="meal-plan">
    <PageHeader :title="t('nav.mealPlan')">
      <Button
        :label="t('mealPlan.toList')"
        icon="mdi mdi-cart-arrow-down"
        outlined
        :disabled="!plannedRecipes"
        @click="toListDialog = true"
      />
    </PageHeader>

    <div v-if="household" class="scope">
      <SelectButton
        v-model="chosenScope"
        :options="scopeOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        :aria-label="t('mealPlan.planScope')"
      >
        <template #option="{ option }">
          <i :class="option.icon" aria-hidden="true" />
          <span>{{ option.label }}</span>
        </template>
      </SelectButton>
      <p class="scope-hint">
        <i18n-t v-if="chosenScope === 'household'" keypath="mealPlan.householdHint" tag="span" scope="global">
          <template #name>
            <RouterLink :to="{ name: 'household' }">{{ household.name }}</RouterLink>
          </template>
        </i18n-t>
        <span v-else>{{ t('mealPlan.personalHint') }}</span>
      </p>
    </div>

    <nav class="week-nav" :aria-label="t('mealPlan.weekNav')">
      <Button icon="mdi mdi-chevron-left" text rounded :aria-label="t('mealPlan.previousWeek')" @click="shift(-1)" />
      <span class="week-label">{{ rangeLabel }}</span>
      <Button icon="mdi mdi-chevron-right" text rounded :aria-label="t('mealPlan.nextWeek')" @click="shift(1)" />
      <Button
        v-if="monday !== startOfWeek(today)"
        :label="t('mealPlan.thisWeek')"
        text
        size="small"
        @click="monday = startOfWeek(today)"
      />
    </nav>

    <SkeletonRegion v-if="placeholders" class="visually-hidden" testid="meal-plan-skeleton" />
    <ol class="week" :aria-busy="loading">
      <ContentCard as="li" v-for="day in days" :key="day" class="day" :class="{ 'day--today': day === today }">
        <h3 class="day-title">
          <span>{{ weekdayName(day) }}</span>
          <span class="day-date">{{ dayDate(day) }}</span>
        </h3>
        <!-- A drop target for suggestions; the meal's add button does the same by keyboard. -->
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
          v-for="slot in SLOTS"
          :key="slot"
          class="slot"
          :class="{ 'slot--drop': dropTarget === `${day}|${slot}` }"
          @dragover="onDragOver(day, slot, $event)"
          @dragleave="onDragLeave(day, slot, $event)"
          @drop="onDrop(day, slot, $event)"
        >
          <span class="slot-name">{{ t(`mealPlan.slots.${slot}`) }}</span>
          <ul class="slot-entries">
            <li v-if="placeholders" aria-hidden="true">
              <Skeleton width="70%" height="1rem" />
            </li>
            <li v-for="entry in placeholders ? [] : entriesFor(entries, day, slot)" :key="entry.id">
              <button type="button" class="entry" @click="openEdit(entry)">
                <i
                  class="mdi"
                  :class="entry.recipe ? 'mdi-book-open-page-variant-outline' : 'mdi-text-short'"
                  aria-hidden="true"
                />
                <span class="entry-title">{{ entry.recipe?.title ?? entry.title }}</span>
                <small class="text-muted">{{ t('mealPlan.servingsShort', { count: entry.servings }) }}</small>
              </button>
            </li>
          </ul>
          <Button
            icon="mdi mdi-plus"
            text
            rounded
            size="small"
            class="slot-add"
            :aria-label="t('mealPlan.addTo', { slot: t(`mealPlan.slots.${slot}`), day: dayName(day) })"
            @click="openNew(day, slot)"
          />
        </div>
      </ContentCard>
    </ol>

    <SuggestionsPanel
      v-if="largeScreen"
      :date-from="monday"
      :date-to="addDays(monday, 6)"
      :scope="scope"
      :planned="plannedIds"
      @plan="openSuggestion"
    />

    <EntryDialog
      v-model:visible="dialog"
      :date="dialogDate"
      :meal-slot="dialogSlot"
      :saving="saving"
      :editing="editingInfo"
      :preset="preset"
      @submit="submit"
      @remove="remove"
    />
    <ToListDialog v-model:visible="toListDialog" :saving="saving" :recipes="weekRecipes" @submit="sendToList" />
  </section>
</template>

<style scoped lang="scss">
.scope {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
}

.scope-hint {
  margin: 0;
  color: var(--p-text-muted-color);
}

.week-nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.week-label {
  font-weight: 700;
  font-size: var(--font-size-lg);
}

.week {
  display: grid;
  gap: var(--space-3);
  padding: 0;
  margin: 0;
  list-style: none;
}

.day {
  display: grid;
  gap: var(--space-1);
}

.day--today {
  outline: 2px solid var(--p-primary-color);
}

.day-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 var(--space-2);
  margin: 0 0 var(--space-1);
  font-size: var(--font-size-lg);
}

.day-date {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.slot {
  display: grid;
  grid-template-columns: 6rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  border-top: 1px solid var(--p-content-border-color);
}

.slot--drop {
  border-radius: var(--p-content-border-radius);
  outline: 2px dashed var(--p-primary-color);
  outline-offset: -2px;
  background: var(--p-highlight-background);
}

.slot-name {
  font-size: var(--font-size-sm);
  color: var(--p-text-muted-color);
}

.slot-entries {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.entry {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  width: 100%;
  min-height: 2.75rem;
  padding: var(--space-1) var(--space-2);
  border: 0;
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-hover-background);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.entry-title {
  font-weight: 700;
}

// A full-size touch target on a phone and a tablet; the week grid of a
// laptop has room only for the small button.
.slot-add {
  width: 2.75rem;
  height: 2.75rem;
}

@media (min-width: $bp-lg) {
  // Seven columns whose rows line up: every day spans the week's five rows
  // (title and four slots) as a subgrid, so a slot sits at the same height
  // in every column however many entries the other days have.
  .week {
    grid-template-columns: repeat(7, minmax(0, 1fr));
    grid-template-rows: auto repeat(4, auto);
  }

  .day {
    grid-row: span 5;
    grid-template-rows: subgrid;
  }

  .day-title {
    flex-direction: column;
    gap: 0;
  }

  // The slot name and its add button share the first line; the entries take
  // the full width below.
  .slot {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: auto 1fr;
    align-content: start;
  }

  .slot-name {
    grid-row: 1;
    grid-column: 1;
  }

  .slot-add {
    grid-row: 1;
    grid-column: 2;
    width: auto;
    height: auto;
  }

  .slot-entries {
    grid-row: 2;
    grid-column: 1 / -1;
  }
}
</style>
