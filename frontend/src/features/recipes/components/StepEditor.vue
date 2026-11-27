<script setup lang="ts">
/**
 * One step of the recipe editor: its text in the original language, an
 * optional duration for cook mode's timer, a photo, the ingredients the
 * step uses, each with amount, unit and a short note, and the equipment it
 * needs, each with an optional count and note.
 */
import { computed } from 'vue'

import { searchIngredients, searchRecipes } from '@/features/recipes/api/recipes'
import type { MentionRef, MentionSource } from '@/shared/components/richText/mentions'
import { useI18n } from 'vue-i18n'

import type { UnitResponse } from '@/features/recipes/api/recipes'
import RichTextEditor from '@/shared/components/richText/RichTextEditor.vue'
import ImageUpload from '@/features/recipes/components/ImageUpload.vue'
import EquipmentSearch from '@/features/recipes/components/EquipmentSearch.vue'
import IngredientSearch, { type FromListOption } from '@/features/recipes/components/IngredientSearch.vue'
import {
  addEquipment,
  ensureLine,
  lineMentions,
  newStepIngredient,
  removeEquipment,
  removeLine,
  type EditorStep,
  type LineTarget,
} from '@/features/recipes/composables/recipeEditorState'
import { useAmountFormat } from '@/features/recipes/composables/useAmountFormat'
import { useIngredientWeights } from '@/features/recipes/composables/useIngredientWeights'
import { matchEquipment } from '@/features/recipes/utils/equipment'
import {
  amountLabel,
  lineKey,
  listSuggestions,
  type ListSuggestion,
  type SummaryLine,
} from '@/features/recipes/utils/ingredientSummary'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import { equipmentIcon } from '@/shared/cookbook/equipment'
import type { ContentLocale, EquipmentResponse } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'

// The parent hands in its reactive step and this component edits it in place;
// the model is never replaced, so no update event is needed.
const step = defineModel<EditorStep>('step', { required: true })
const props = defineProps<{
  index: number
  count: number
  locale: ContentLocale
  units: UnitResponse[]
  canCreateIngredient: boolean
  /** The equipment catalogue the picker and the `@` suggestions offer. */
  equipment?: EquipmentResponse[]
  invalid?: boolean
  recipeId?: string | null
  /** The recipe's declared ingredient list, whose lines the picker offers first while the steps do not use them up. */
  declared?: SummaryLine[]
  /** The lines of every step, which decide how much of the declared list is used. */
  recipeLines?: SummaryLine[]
}>()
const emit = defineEmits<{ move: [direction: -1 | 1]; remove: []; insertAfter: [] }>()

const { t, locale: uiLocale } = useI18n()
const prefix = computed(() => `step-${step.value.key}`)

// Each line's unit picker says whether its ingredient can be weighed in a unit.
const weights = useIngredientWeights()

function addIngredient(target: LineTarget) {
  if (target.ingredient) weights.remember(target.id, target.ingredient)
  step.value.ingredients.push(newStepIngredient(target))
}

// Removing a line turns its chips back into plain names, in every language.
function removeIngredient(i: number) {
  removeLine(step.value, i)
}

// The picker offers the declared lines no step uses yet, with the declared
// amount, and those the steps use less of, with what is missing, so adding
// one clears the summary's hint. A line this step has already is left out:
// its amount is changed in its row instead.
const { style: amountStyle } = useAmountFormat()

function listHint(line: ListSuggestion): string {
  const locale = contentLocaleOf(uiLocale.value)
  if (line.usage.state === 'partly') {
    const { missing, unit, symbol } = line.usage
    return t('recipes.editor.fromList.left', { amount: amountLabel(missing, unit, symbol, locale, amountStyle.value) })
  }
  if (line.amount === null) return t('recipes.editor.fromList.unused')
  const unit = props.units.find((u) => u.id === line.unit_id) ?? null
  return t('recipes.editor.fromList.unusedAmount', {
    amount: amountLabel(line.amount, unit, '', locale, amountStyle.value),
  })
}

const fromList = computed<FromListOption[]>(() => {
  if (!props.declared?.length) return []
  const own = new Set(step.value.ingredients.map(lineKey))
  return listSuggestions(props.declared, props.recipeLines ?? [], props.units, weights.weightsOf)
    .filter((line) => !own.has(line.key))
    .map((line) => ({
      key: line.key,
      hint: listHint(line),
      target: {
        id: (line.sub_recipe_id ?? line.ingredient_id)!,
        name: line.ingredient_name,
        kind: line.sub_recipe_id ? 'recipe' : 'ingredient',
        amount: line.amount,
        unit_id: line.unit_id,
      },
    }))
})

// The step image library ranks its photos by what this step uses.
const library = computed(() => ({
  ingredientIds: step.value.ingredients.flatMap((row) => (row.ingredient_id ? [row.ingredient_id] : [])),
  equipmentIds: step.value.equipment.map((row) => row.equipment_id),
}))

// The picker offers the catalogue items the step does not have yet.
const takenEquipment = computed(() => step.value.equipment.map((e) => e.equipment_id))

function pickEquipment(item: EquipmentResponse) {
  addEquipment(step.value, { id: item.id, name: item.name })
}

// Removing an item turns its chips back into plain names, in every language.
function dropEquipment(i: number) {
  removeEquipment(step.value, i)
}

// `@` offers the step's own lines and equipment first, then the catalogue,
// the reader's recipes and the equipment catalogue. Picking something the
// step lacks adds it: a line with no amount, or an equipment item. A match
// on another name shows that name ("Tomate → Paradeiser").
const mentionSource: MentionSource = {
  search: async (query) => {
    const q = query.trim().toLowerCase()
    const own = lineMentions(step.value).filter((r) => r.name.toLowerCase().includes(q))
    if (!q) return own.slice(0, 8)
    const [ingredients, recipes] = await Promise.all([
      searchIngredients(q, 8).catch(() => ({ items: [] })),
      searchRecipes(q, 5).catch(() => ({ items: [] })),
    ])
    const found: MentionRef[] = [
      ...ingredients.items.map(
        (i): MentionRef => ({ kind: 'ingredient', id: i.id, name: i.name, alias: i.matched_alias ?? null }),
      ),
      ...recipes.items
        .filter((r) => r.id !== props.recipeId)
        .map((r): MentionRef => ({ kind: 'recipe', id: r.id, name: r.title })),
      ...matchEquipment(props.equipment ?? [], q, 5),
    ]
    const seen = new Set(own.map((r) => `${r.kind}:${r.id}`))
    return [...own, ...found.filter((r) => !seen.has(`${r.kind}:${r.id}`))].slice(0, 12)
  },
  picked: (ref) => ensureLine(step.value, ref),
}
</script>

<template>
  <section class="step-editor" :class="{ 'step-editor--invalid': invalid }">
    <header class="step-editor-head">
      <h3>{{ t('recipes.detail.step', { n: index + 1 }) }}</h3>
      <div class="step-editor-tools">
        <Button
          icon="mdi mdi-arrow-up"
          text
          rounded
          severity="secondary"
          :disabled="index === 0"
          :aria-label="t('recipes.editor.moveUp')"
          @click="emit('move', -1)"
        />
        <Button
          icon="mdi mdi-arrow-down"
          text
          rounded
          severity="secondary"
          :disabled="index === count - 1"
          :aria-label="t('recipes.editor.moveDown')"
          @click="emit('move', 1)"
        />
        <Button
          icon="mdi mdi-delete-outline"
          text
          rounded
          severity="danger"
          :disabled="count === 1"
          :aria-label="t('recipes.editor.removeStep')"
          @click="emit('remove')"
        />
      </div>
    </header>

    <div class="field">
      <span :id="`${prefix}-text-label`" class="field-label">{{ t('recipes.editor.stepText') }}</span>
      <RichTextEditor
        :key="`${prefix}-${locale}`"
        v-model="step.text[locale]"
        :labelledby="`${prefix}-text-label`"
        :rows="3"
        :invalid="invalid"
        mentionable
        :mentions="mentionSource"
      />
      <small class="field-hint">{{ t('recipes.editor.mentionHint') }}</small>
    </div>

    <div class="step-editor-ingredients">
      <ul v-if="step.ingredients.length" class="ingredient-rows">
        <li v-for="(row, i) in step.ingredients" :key="row.key" class="ingredient-row">
          <span class="ingredient-row-name">
            <span
              v-if="row.sub_recipe_id"
              class="mdi mdi-book-open-page-variant-outline"
              :title="t('recipes.subRecipes.recipe')"
              aria-hidden="true"
            />
            {{ row.ingredient_name || t('recipes.subRecipes.hidden') }}
            <small v-if="row.sub_recipe_id" class="visually-hidden">{{ t('recipes.subRecipes.recipe') }}</small>
          </span>
          <div class="ingredient-row-amount">
            <label :for="`${prefix}-amount-${row.key}`" class="visually-hidden">
              {{ t('recipes.editor.amount') }}
            </label>
            <InputNumber
              v-model="row.amount"
              :input-id="`${prefix}-amount-${row.key}`"
              :min-fraction-digits="0"
              :max-fraction-digits="3"
              :min="0"
              :placeholder="t('recipes.editor.amount')"
              fluid
            />
          </div>
          <div class="ingredient-row-unit">
            <span :id="`${prefix}-unit-${row.key}-label`" class="visually-hidden">
              {{ t('recipes.editor.unit') }}
            </span>
            <UnitSelect
              v-model="row.unit_id"
              :units="units"
              :ingredient="weights.weightsOf(row.ingredient_id)"
              :placeholder="t('recipes.editor.unit')"
              show-clear
              fluid
              :aria-labelledby="`${prefix}-unit-${row.key}-label`"
            />
          </div>
          <div class="ingredient-row-note">
            <label :for="`${prefix}-note-${row.key}`" class="visually-hidden">
              {{ t('recipes.editor.note') }}
            </label>
            <InputText
              :id="`${prefix}-note-${row.key}`"
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
            class="ingredient-row-remove"
            :aria-label="t('recipes.editor.removeIngredient', { name: row.ingredient_name })"
            @click="removeIngredient(i)"
          />
        </li>
      </ul>
      <label :for="`${prefix}-add`" class="visually-hidden">{{ t('recipes.editor.addIngredient') }}</label>
      <IngredientSearch
        :input-id="`${prefix}-add`"
        :can-create="canCreateIngredient"
        :exclude-recipe-id="recipeId ?? null"
        :from-list="fromList"
        @select="addIngredient"
      />
    </div>

    <div class="step-editor-ingredients">
      <ul v-if="step.equipment.length" class="ingredient-rows">
        <li v-for="(row, i) in step.equipment" :key="row.key" class="equipment-row">
          <span class="ingredient-row-name">
            <span :class="equipmentIcon(equipment?.find((e) => e.id === row.equipment_id)?.icon)" aria-hidden="true" />
            {{ row.equipment_name }}
          </span>
          <div class="equipment-row-count">
            <label :for="`${prefix}-eq-count-${row.key}`" class="visually-hidden">
              {{ t('recipes.equipment.count') }}
            </label>
            <InputNumber
              v-model="row.count"
              :input-id="`${prefix}-eq-count-${row.key}`"
              :min="1"
              :max="100"
              :placeholder="t('recipes.equipment.count')"
              fluid
            />
          </div>
          <div class="ingredient-row-note">
            <label :for="`${prefix}-eq-note-${row.key}`" class="visually-hidden">
              {{ t('recipes.editor.note') }}
            </label>
            <InputText
              :id="`${prefix}-eq-note-${row.key}`"
              v-model="row.notes[locale]"
              :placeholder="t('recipes.equipment.notePlaceholder')"
              fluid
            />
          </div>
          <Button
            icon="mdi mdi-close"
            text
            rounded
            severity="secondary"
            class="ingredient-row-remove"
            :aria-label="t('recipes.editor.removeIngredient', { name: row.equipment_name })"
            @click="dropEquipment(i)"
          />
        </li>
      </ul>
      <label :for="`${prefix}-eq-add`" class="visually-hidden">{{ t('recipes.equipment.add') }}</label>
      <EquipmentSearch
        :input-id="`${prefix}-eq-add`"
        :equipment="equipment ?? []"
        :taken="takenEquipment"
        @select="pickEquipment"
      />
    </div>

    <div class="step-editor-extras">
      <div class="field">
        <label :for="`${prefix}-duration`" class="field-label">{{ t('recipes.editor.duration') }}</label>
        <InputNumber
          v-model="step.duration_minutes"
          :input-id="`${prefix}-duration`"
          :min="0"
          :max="1440"
          :suffix="` ${t('recipes.editor.minutesSuffix')}`"
          fluid
        />
        <small class="field-hint">{{ t('recipes.editor.durationHint') }}</small>
      </div>
      <ImageUpload v-model="step.image_id" :label="t('recipes.editor.stepImage')" :library="library" compact />
    </div>

    <Button
      :label="t('recipes.editor.insertStep')"
      icon="mdi mdi-plus"
      text
      size="small"
      class="step-editor-insert"
      @click="emit('insertAfter')"
    />
  </section>
</template>

<style scoped lang="scss">
.step-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-content-background);
}

.step-editor--invalid {
  border-color: var(--p-red-400);
}

.step-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.step-editor-tools {
  display: flex;
}

.step-editor-ingredients {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ingredient-rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

// Phone first: name and remove on top, then amount and unit side by side,
// then the note; from a tablet up everything sits on one line.
.ingredient-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  grid-template-areas:
    'name name remove'
    'amount unit unit'
    'note note note';
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-50);
}

.p-dark .ingredient-row {
  background: var(--p-surface-900);
}

.ingredient-row-name {
  grid-area: name;
  font-weight: 700;
}

.ingredient-row-amount {
  grid-area: amount;
}

.ingredient-row-unit {
  grid-area: unit;
}

.ingredient-row-note {
  grid-area: note;
}

.ingredient-row-remove {
  grid-area: remove;
}

.equipment-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  grid-template-areas:
    'name name remove'
    'count note note';
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-50);
}

.p-dark .equipment-row {
  background: var(--p-surface-900);
}

.equipment-row-count {
  grid-area: count;
}

.step-editor-extras {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.step-editor-insert {
  align-self: flex-start;
}

@media (min-width: $bp-md) {
  .ingredient-row {
    grid-template-columns: minmax(8rem, 1.2fr) 7rem minmax(8rem, 1fr) minmax(8rem, 1.2fr) auto;
    grid-template-areas: 'name amount unit note remove';
  }

  .equipment-row {
    grid-template-columns: minmax(8rem, 1.2fr) 7rem minmax(8rem, 2.2fr) auto;
    grid-template-areas: 'name count note remove';
  }

  .step-editor-extras {
    flex-direction: row;
    align-items: flex-start;
    gap: var(--space-5);
  }
}
</style>
