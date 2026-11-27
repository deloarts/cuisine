<script setup lang="ts">
/**
 * The first card of the editor's steps tab: the recipe's declared
 * ingredient list, edited in place like a step's lines, and every
 * ingredient only the steps name, which one click adds to the list. Each
 * declared line says when no step uses it, when the steps use less of it
 * ("200 g not used in any step"), or that it cannot be checked because the
 * units do not compare. The recipe's own list takes the larger of both, so
 * these are hints, never errors.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { UnitResponse } from '@/features/recipes/api/recipes'
import IngredientSearch from '@/features/recipes/components/IngredientSearch.vue'
import {
  newStepIngredient,
  type EditorForm,
  type LineTarget,
} from '@/features/recipes/composables/recipeEditorState'
import { useIngredientWeights } from '@/features/recipes/composables/useIngredientWeights'
import {
  amountLabel,
  lineKey,
  stepOnlyLines,
  usageOf,
  type LineUsage,
  type StepOnlyLine,
} from '@/features/recipes/utils/ingredientSummary'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import type { ContentLocale } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'

// The parent hands in its reactive form and this card edits its declared
// list in place, like the step editor does with a step.
const form = defineModel<EditorForm>('form', { required: true })
const props = defineProps<{
  locale: ContentLocale
  units: UnitResponse[]
  canCreateIngredient: boolean
  recipeId?: string | null
}>()

const { t, locale: uiLocale } = useI18n()
const weights = useIngredientWeights()
const numberLocale = () => contentLocaleOf(uiLocale.value)
const { style: amountStyle } = useAmountFormat()

const stepLines = computed(() => form.value.steps.flatMap((s) => s.ingredients))

// The usage of each declared line; several lines of one ingredient count
// together and only the first carries the hint.
const usages = computed<(LineUsage | null)[]>(() => {
  const seen = new Set<string>()
  return form.value.ingredients.map((row) => {
    const key = lineKey(row)
    if (key === null || seen.has(key)) return null
    seen.add(key)
    const declared = form.value.ingredients.filter((l) => lineKey(l) === key)
    const used = stepLines.value.filter((l) => lineKey(l) === key)
    return usageOf(declared, used, props.units, weights.weightsOf)
  })
})

const stepOnly = computed(() =>
  stepOnlyLines(form.value.ingredients, stepLines.value, props.units, weights.weightsOf),
)

function unitOf(id: string | null): UnitResponse | null {
  return id === null ? null : (props.units.find((u) => u.id === id) ?? null)
}

function amountText(amount: number, unit: UnitResponse | null, symbol = ''): string {
  return amountLabel(amount, unit, symbol, numberLocale(), amountStyle.value)
}

function usageText(usage: LineUsage): string {
  if (usage.state === 'unused') return t('recipes.editor.summary.unused')
  if (usage.state === 'unchecked') return t('recipes.editor.summary.unchecked')
  if (usage.state === 'partly') {
    return t('recipes.editor.summary.partly', { amount: amountText(usage.missing, usage.unit, usage.symbol) })
  }
  return ''
}

function addLine(target: LineTarget) {
  if (target.ingredient) weights.remember(target.id, target.ingredient)
  form.value.ingredients.push(newStepIngredient(target))
}

// Takes what the steps use into the list: the summed amount where it adds
// up, otherwise the line without an amount for the cook to fill in.
function addStepOnly(line: StepOnlyLine) {
  const row = newStepIngredient({
    id: (line.sub_recipe_id ?? line.ingredient_id)!,
    name: line.ingredient_name,
    kind: line.sub_recipe_id ? 'recipe' : 'ingredient',
  })
  row.amount = line.amount
  row.unit_id = line.unit_id
  form.value.ingredients.push(row)
}

function removeLine(index: number) {
  form.value.ingredients.splice(index, 1)
}
</script>

<template>
  <section class="summary-card" data-testid="ingredient-summary">
    <header class="summary-head">
      <h3>{{ t('recipes.editor.summary.title') }}</h3>
      <small class="field-hint">{{ t('recipes.editor.summary.hint') }}</small>
    </header>

    <ul v-if="form.ingredients.length || stepOnly.length" class="summary-rows">
      <li
        v-for="(row, i) in form.ingredients"
        :key="row.key"
        class="summary-row"
        data-testid="summary-line"
      >
        <span class="summary-row-name">
          <span
            v-if="row.sub_recipe_id"
            class="mdi mdi-book-open-page-variant-outline"
            :title="t('recipes.subRecipes.recipe')"
            aria-hidden="true"
          />
          {{ row.ingredient_name || t('recipes.subRecipes.hidden') }}
        </span>
        <div class="summary-row-amount">
          <label :for="`summary-amount-${row.key}`" class="visually-hidden">
            {{ t('recipes.editor.amount') }}
          </label>
          <InputNumber
            v-model="row.amount"
            :input-id="`summary-amount-${row.key}`"
            :min-fraction-digits="0"
            :max-fraction-digits="3"
            :min="0"
            :placeholder="t('recipes.editor.amount')"
            fluid
          />
        </div>
        <div class="summary-row-unit">
          <span :id="`summary-unit-${row.key}-label`" class="visually-hidden">
            {{ t('recipes.editor.unit') }}
          </span>
          <UnitSelect
            v-model="row.unit_id"
            :units="units"
            :ingredient="weights.weightsOf(row.ingredient_id)"
            :placeholder="t('recipes.editor.unit')"
            show-clear
            fluid
            :aria-labelledby="`summary-unit-${row.key}-label`"
          />
        </div>
        <div class="summary-row-note">
          <label :for="`summary-note-${row.key}`" class="visually-hidden">
            {{ t('recipes.editor.note') }}
          </label>
          <InputText
            :id="`summary-note-${row.key}`"
            v-model="row.notes[locale]"
            :placeholder="t('recipes.editor.notePlaceholder')"
            fluid
          />
        </div>
        <Button
          icon="mdi mdi-close"
          text
          rounded
          severity="secondary"
          class="summary-row-remove"
          :aria-label="t('recipes.editor.removeIngredient', { name: row.ingredient_name })"
          @click="removeLine(i)"
        />
        <small
          v-if="usages[i] && usages[i]!.state !== 'used'"
          class="summary-usage"
          :class="{ 'summary-usage--warn': usages[i]!.state !== 'unchecked' }"
          :data-usage="usages[i]!.state"
          data-testid="summary-usage"
        >
          <span
            :class="usages[i]!.state === 'unchecked' ? 'mdi mdi-information-outline' : 'mdi mdi-alert-outline'"
            aria-hidden="true"
          />
          {{ usageText(usages[i]!) }}
        </small>
      </li>
      <li v-for="line in stepOnly" :key="line.key" class="summary-only" data-testid="summary-step-only">
        <span class="summary-row-name">
          <span
            v-if="line.sub_recipe_id"
            class="mdi mdi-book-open-page-variant-outline"
            :title="t('recipes.subRecipes.recipe')"
            aria-hidden="true"
          />
          {{ line.ingredient_name || t('recipes.subRecipes.hidden') }}
        </span>
        <span class="summary-only-amount">
          <template v-if="line.amount !== null">{{ amountText(line.amount, unitOf(line.unit_id)) }}</template>
        </span>
        <span class="summary-only-badge">{{ t('recipes.editor.summary.onlyInSteps') }}</span>
        <Button
          :label="t('recipes.editor.summary.addToList')"
          :aria-label="t('recipes.editor.summary.addToListNamed', { name: line.ingredient_name })"
          icon="mdi mdi-playlist-plus"
          size="small"
          text
          data-testid="summary-add-step-only"
          @click="addStepOnly(line)"
        />
      </li>
    </ul>
    <p v-else class="summary-empty">{{ t('recipes.editor.summary.empty') }}</p>

    <label for="summary-add" class="visually-hidden">{{ t('recipes.editor.summary.add') }}</label>
    <IngredientSearch
      input-id="summary-add"
      :can-create="canCreateIngredient"
      :exclude-recipe-id="recipeId ?? null"
      @select="addLine"
    />
  </section>
</template>

<style scoped lang="scss">
.summary-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-content-background);
}

.summary-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);

  h3 {
    margin: 0;
  }
}

.summary-rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

// Laid out like a step's ingredient rows, with the usage hint underneath.
.summary-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  grid-template-areas:
    'name name remove'
    'amount unit unit'
    'note note note'
    'usage usage usage';
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-50);
}

.p-dark .summary-row {
  background: var(--p-surface-900);
}

.summary-row-name {
  grid-area: name;
  font-weight: 700;
}

.summary-row-amount {
  grid-area: amount;
}

.summary-row-unit {
  grid-area: unit;
}

.summary-row-note {
  grid-area: note;
}

.summary-row-remove {
  grid-area: remove;
}

.summary-usage {
  display: inline-flex;
  grid-area: usage;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-text-muted-color);
}

.summary-usage--warn {
  color: var(--p-orange-700);
}

.p-dark .summary-usage--warn {
  color: var(--p-orange-300);
}

// A line only the steps name: read only, with the one-click way into the list.
.summary-only {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
}

.summary-only-amount {
  font-variant-numeric: tabular-nums;
}

.summary-only-badge {
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.summary-empty {
  margin: 0;
  color: var(--p-text-muted-color);
}

@media (min-width: $bp-md) {
  .summary-row {
    grid-template-columns: minmax(8rem, 1.2fr) 7rem minmax(8rem, 1fr) minmax(8rem, 1.2fr) auto;
    grid-template-areas:
      'name amount unit note remove'
      'usage usage usage usage usage';
  }
}
</style>
