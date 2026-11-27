<script setup lang="ts">
/**
 * Adds a line to a step: type part of a name and pick a catalogue
 * ingredient, another recipe (a sub-recipe, marked as such), or "Create …"
 * to add a missing ingredient to the catalogue on the spot. The dropdown
 * button lists the first ingredients without typing. Ingredients show their
 * category, family and draft state, recipes their cover, time and author.
 *
 * With `fromList`, the lines of the recipe's ingredient list that the steps
 * do not use up yet come first, under a heading of their own and filtered by
 * what is typed; picking one adds the line with the amount and unit it
 * carries, and the catalogue does not repeat it below.
 */
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  searchIngredients,
  searchRecipes,
  type IngredientResponse,
} from '@/features/recipes/api/recipes'
import type { LineTarget } from '@/features/recipes/composables/recipeEditorState'
import NewIngredientDialog from '@/features/recipes/components/NewIngredientDialog.vue'
import IngredientOption from '@/shared/cookbook/IngredientOption.vue'
import RecipeOption from '@/shared/cookbook/RecipeOption.vue'
import type { RecipeSummaryResponse } from '@/shared/cookbook/types'
import { matchesText } from '@/shared/composables/tableText'

/** A line of the recipe's ingredient list the picker offers first, with what it says about the amount. */
export interface FromListOption {
  key: string
  target: LineTarget
  /** The amount the pick adds or the amount still missing, shown beside the name and read out with it. */
  hint: string
}

const props = withDefaults(
  defineProps<{
    inputId: string
    canCreate: boolean
    excludeRecipeId?: string | null
    fromList?: FromListOption[]
  }>(),
  { excludeRecipeId: null, fromList: () => [] },
)
const emit = defineEmits<{ select: [target: LineTarget] }>()

const { t } = useI18n()

// `label` names the option for assistive technology and the input; a list
// line reads with its hint ("Onion, 1 pc left").
type Suggestion = { label: string } & (
  | { kind: 'ingredient'; name: string; ingredient: IngredientResponse }
  | { kind: 'recipe'; name: string; recipe: RecipeSummaryResponse }
  | { kind: 'create'; name: string }
  | { kind: 'list'; name: string; option: FromListOption }
)

interface SuggestionGroup {
  label: string
  items: Suggestion[]
}

const query = ref<string | Suggestion>('')
const suggestions = ref<Suggestion[] | SuggestionGroup[]>([])
// The dropdown groups its options only while list lines are among them.
const grouped = ref(false)
const groupProps = computed(() =>
  grouped.value ? { optionGroupLabel: 'label', optionGroupChildren: 'items' } : {},
)
const createOpen = ref(false)
const createName = ref('')

async function complete(event: { query: string }) {
  const text = event.query.trim()
  const [ingredients, recipes] = await Promise.all([
    searchIngredients(text).catch(() => ({ items: [] as IngredientResponse[] })),
    text ? searchRecipes(text).catch(() => ({ items: [] })) : Promise.resolve({ items: [] }),
  ])
  const fromList = props.fromList
    .filter((o) => matchesText(text, o.target.name))
    .map((o): Suggestion => ({ kind: 'list', name: o.target.name, label: `${o.target.name}, ${o.hint}`, option: o }))
  const listed = new Set(fromList.map((s) => (s.kind === 'list' ? s.option.target.id : '')))
  const found: Suggestion[] = [
    ...ingredients.items
      .filter((i) => !listed.has(i.id))
      .map((i): Suggestion => ({ kind: 'ingredient', name: i.name, label: i.name, ingredient: i })),
    ...recipes.items
      .filter((r) => r.id !== props.excludeRecipeId && !listed.has(r.id))
      .map((r): Suggestion => ({ kind: 'recipe', name: r.title, label: r.title, recipe: r })),
  ]
  const lower = text.toLowerCase()
  const exact = [...fromList, ...found].some(
    (s) =>
      s.name.toLowerCase() === lower ||
      (s.kind === 'ingredient' && s.ingredient.matched_alias?.toLowerCase() === lower),
  )
  const rest: Suggestion[] = text && !exact ? [...found, { kind: 'create', name: text, label: text }] : found
  grouped.value = fromList.length > 0
  suggestions.value = grouped.value
    ? [
        { label: t('recipes.editor.fromList.title'), items: fromList },
        ...(rest.length ? [{ label: t('recipes.editor.fromList.more'), items: rest }] : []),
      ]
    : rest
}

function chosen(event: { value: Suggestion }) {
  const pick = event.value
  // AutoComplete keeps the picked option as its own value before this event.
  // Clearing the model in the same tick is lost when the field was already
  // empty (an option picked from the dropdown button), since the model then
  // never changes and the option's label stays in the input. The next tick
  // lets the pick reach the model first, so the reset always lands.
  void nextTick(() => (query.value = ''))
  if (pick.kind === 'create') {
    createName.value = pick.name
    createOpen.value = true
  } else if (pick.kind === 'list') {
    emit('select', pick.option.target)
  } else if (pick.kind === 'recipe') {
    emit('select', { id: pick.recipe.id, name: pick.name, kind: 'recipe' })
  } else {
    emit('select', { id: pick.ingredient.id, name: pick.name, kind: 'ingredient', ingredient: pick.ingredient })
  }
}

function created(ingredient: IngredientResponse) {
  emit('select', { id: ingredient.id, name: ingredient.name, kind: 'ingredient', ingredient })
}
</script>

<template>
  <div class="ingredient-search">
    <AutoComplete
      v-model="query"
      :input-id="inputId"
      :suggestions="suggestions"
      option-label="label"
      v-bind="groupProps"
      :placeholder="t('recipes.editor.ingredientSearch')"
      :delay="200"
      dropdown
      fluid
      @complete="complete"
      @option-select="chosen"
    >
      <template #optiongroup="{ option }">
        <span class="suggestion-group">{{ option.label }}</span>
      </template>
      <template #option="{ option }">
        <span v-if="option.kind === 'list'" class="suggestion-list">
          <span class="suggestion-list-name">
            <span
              v-if="option.option.target.kind === 'recipe'"
              class="mdi mdi-book-open-page-variant-outline"
              :title="t('recipes.subRecipes.recipe')"
              aria-hidden="true"
            />
            {{ option.name }}
          </span>
          <small class="suggestion-meta">{{ option.option.hint }}</small>
        </span>
        <span v-else-if="option.kind === 'create' && canCreate" class="suggestion-create">
          <span class="mdi mdi-plus" aria-hidden="true" />
          {{ t('recipes.editor.createIngredient', { name: option.name }) }}
        </span>
        <span v-else-if="option.kind === 'create'" class="suggestion-missing">
          {{ t('recipes.editor.ingredientUnknown', { name: option.name }) }}
        </span>
        <span v-else-if="option.kind === 'recipe'" class="suggestion-recipe">
          <RecipeOption :recipe="option.recipe" />
          <small class="suggestion-meta">{{ t('recipes.subRecipes.recipe') }}</small>
        </span>
        <IngredientOption v-else :ingredient="option.ingredient" :meta="['category', 'family', 'draft', 'season']" />
      </template>
    </AutoComplete>
    <NewIngredientDialog v-model:visible="createOpen" :name="createName" @created="created" />
  </div>
</template>

<style scoped lang="scss">
.suggestion-create {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: 700;
  color: var(--p-primary-color);
}

.suggestion-recipe {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
}

.suggestion-group {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
}

.suggestion-list {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
}

.suggestion-list-name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.suggestion-missing {
  color: var(--p-text-muted-color);
}

.suggestion-meta {
  flex-shrink: 0;
  color: var(--p-text-muted-color);
}
</style>
