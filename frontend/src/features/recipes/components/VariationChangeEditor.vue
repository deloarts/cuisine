<script setup lang="ts">
/**
 * One change of the variation editor, edited in place: its kind, the step
 * it belongs to, and the fields that kind needs. A swap or a removal picks
 * one of the step's lines (a swap for the whole recipe one of the recipe's
 * ingredients); a new step text or an extra step is rich text whose
 * mentions point at that step's own lines and equipment.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  searchIngredients,
  type RecipeDetailResponse,
  type UnitResponse,
  type VariationChangeKind,
} from '@/features/recipes/api/recipes'
import EquipmentSearch from '@/features/recipes/components/EquipmentSearch.vue'
import IngredientSearch from '@/features/recipes/components/IngredientSearch.vue'
import type { LineTarget } from '@/features/recipes/composables/recipeEditorState'
import {
  addExtraEquipment,
  addExtraLine,
  CHANGE_KINDS,
  changeKind,
  removeExtraEquipment,
  removeExtraLine,
  setTarget,
  type ChangeDraft,
} from '@/features/recipes/composables/variationEditorState'
import { useIngredientWeights } from '@/features/recipes/composables/useIngredientWeights'
import { lineResolver } from '@/features/recipes/utils/mentionResolver'
import { matchEquipment } from '@/features/recipes/utils/equipment'
import RichText from '@/shared/components/richText/RichText.vue'
import RichTextEditor from '@/shared/components/richText/RichTextEditor.vue'
import type { MentionRef, MentionSource } from '@/shared/components/richText/mentions'
import type { EquipmentResponse } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'

// The parent hands in its reactive change and this component edits it in
// place, except for a new kind, which replaces it through `update:change`.
const change = defineModel<ChangeDraft>('change', { required: true })
const props = defineProps<{
  index: number
  recipe: RecipeDetailResponse
  units: UnitResponse[]
  equipment: EquipmentResponse[]
  canCreateIngredient: boolean
  invalid?: boolean
}>()
const emit = defineEmits<{ remove: [] }>()

const { t } = useI18n()
const prefix = computed(() => `change-${change.value.key}`)

const kindOptions = computed(() =>
  CHANGE_KINDS.map((k) => ({ value: k, label: t(`recipes.variations.editor.kinds.${k}`) })),
)
// The unit pickers say whether the line's ingredient can be weighed in a unit.
const weights = useIngredientWeights()
function rememberWeights(target: LineTarget) {
  if (target.ingredient) weights.remember(target.id, target.ingredient)
}

// A short plain excerpt of a step, so the step picker says which one it is.
function excerpt(text: string): string {
  const plain = text
    .replace(/@\[([^\]\n]+)\]\([a-z]+:[0-9A-Fa-f-]{36}\)/g, '$1')
    .replace(/[*_#>`]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.length > 40 ? `${plain.slice(0, 40)}…` : plain
}

// The step picker; a swap for the whole recipe takes 0 here, since a
// select cannot show null as a choice.
const stepOptions = computed(() => {
  const steps = props.recipe.steps.map((s) => ({
    value: s.position,
    label:
      change.value.kind === 'extra_step'
        ? t('recipes.variations.editor.afterStep', { n: s.position, text: excerpt(s.text) })
        : t('recipes.variations.editor.stepOption', { n: s.position, text: excerpt(s.text) }),
  }))
  if (change.value.kind === 'swap') return [{ value: 0, label: t('recipes.variations.editor.wholeRecipe') }, ...steps]
  if (change.value.kind === 'extra_step') return [{ value: 0, label: t('recipes.variations.editor.atStart') }, ...steps]
  return steps
})
const stepValue = computed(() => change.value.step ?? 0)
function setStep(value: number) {
  change.value.step = change.value.kind === 'swap' && value === 0 ? null : value
  if (change.value.kind === 'step_text' && !change.value.text.trim()) prefillText()
}

const step = computed(() =>
  change.value.step ? (props.recipe.steps.find((s) => s.position === change.value.step) ?? null) : null,
)

// The lines a swap or a removal can name: the step's, or for a swap on the
// whole recipe every ingredient of the recipe. A swap only takes ingredients.
const targetOptions = computed(() => {
  const lines = step.value ? step.value.ingredients : change.value.kind === 'swap' ? props.recipe.ingredients : []
  const seen = new Set<string>()
  return lines.flatMap((line) => {
    const value = line.ingredient_id
      ? `ingredient:${line.ingredient_id}`
      : line.sub_recipe?.id && change.value.kind !== 'swap'
        ? `recipe:${line.sub_recipe.id}`
        : null
    if (!value || seen.has(value)) return []
    seen.add(value)
    return [{ value, label: line.sub_recipe?.title ?? line.name }]
  })
})
const targetValue = computed(() =>
  change.value.ingredient_id
    ? `ingredient:${change.value.ingredient_id}`
    : change.value.sub_recipe_id
      ? `recipe:${change.value.sub_recipe_id}`
      : null,
)
function pickTarget(value: string | null) {
  const option = targetOptions.value.find((o) => o.value === value)
  if (!option || !value) return
  const [kind, id] = value.split(':') as ['ingredient' | 'recipe', string]
  setTarget(change.value, { kind, id, name: option.label })
}

function pickReplacement(target: LineTarget) {
  if (target.kind === 'recipe') return
  rememberWeights(target)
  change.value.to_ingredient_id = target.id
  change.value.to_name = target.name
}

function pickAdded(target: LineTarget) {
  rememberWeights(target)
  setTarget(change.value, { kind: target.kind === 'recipe' ? 'recipe' : 'ingredient', id: target.id, name: target.name })
}

function setKind(kind: VariationChangeKind) {
  if (kind !== change.value.kind) change.value = changeKind(change.value, kind)
}

function prefillText() {
  if (step.value) change.value.text = step.value.text
}

// A new step text mentions only the step's own lines and equipment.
const stepTextMentions: MentionSource = {
  search: (query) => {
    const q = query.trim().toLowerCase()
    const refs: MentionRef[] = [
      ...(step.value?.ingredients ?? []).flatMap((line): MentionRef[] =>
        line.ingredient_id
          ? [{ kind: 'ingredient', id: line.ingredient_id, name: line.name }]
          : line.sub_recipe?.id
            ? [{ kind: 'recipe', id: line.sub_recipe.id, name: line.sub_recipe.title ?? line.name }]
            : [],
      ),
      ...(step.value?.equipment ?? []).map((e): MentionRef => ({ kind: 'equipment', id: e.equipment.id, name: e.equipment.name })),
    ]
    return Promise.resolve(refs.filter((r) => r.name.toLowerCase().includes(q)).slice(0, 12))
  },
}

// An extra step mentions its own lines and equipment; picking an ingredient
// or an item it lacks adds it to the step.
const extraMentions: MentionSource = {
  search: async (query) => {
    const q = query.trim().toLowerCase()
    const own: MentionRef[] = [
      ...change.value.lines.map((l): MentionRef => ({ kind: 'ingredient', id: l.ingredient_id, name: l.name })),
      ...change.value.equipment.map((e): MentionRef => ({ kind: 'equipment', id: e.equipment_id, name: e.name })),
    ].filter((r) => r.name.toLowerCase().includes(q))
    if (!q) return own.slice(0, 8)
    const found = await searchIngredients(q, 8).catch(() => ({ items: [] }))
    const seen = new Set(own.map((r) => `${r.kind}:${r.id}`))
    const more: MentionRef[] = [
      ...found.items.map((i): MentionRef => ({ kind: 'ingredient', id: i.id, name: i.name, alias: i.matched_alias ?? null })),
      ...matchEquipment(props.equipment, q, 5),
    ]
    return [...own, ...more.filter((r) => !seen.has(`${r.kind}:${r.id}`))].slice(0, 12)
  },
  picked: (ref) => {
    if (ref.kind === 'ingredient') addExtraLine(change.value, ref)
    else if (ref.kind === 'equipment') addExtraEquipment(change.value, ref)
  },
}

const takenEquipment = computed(() => change.value.equipment.map((e) => e.equipment_id))

function addExtra(target: LineTarget) {
  if (target.kind === 'recipe') return
  rememberWeights(target)
  addExtraLine(change.value, target)
}
</script>

<template>
  <section class="change-editor" :class="{ 'change-editor--invalid': invalid }" :data-testid="`change-${index}`">
    <header class="change-editor-head">
      <h3>{{ index + 1 }}.</h3>
      <div class="field change-editor-kind">
        <span :id="`${prefix}-kind-label`" class="visually-hidden">{{ t('recipes.variations.editor.kind') }}</span>
        <Select
          :model-value="change.kind"
          :options="kindOptions"
          option-label="label"
          option-value="value"
          fluid
          :aria-labelledby="`${prefix}-kind-label`"
          @update:model-value="setKind"
        />
      </div>
      <Button
        icon="mdi mdi-delete-outline"
        text
        rounded
        severity="danger"
        :aria-label="t('recipes.variations.editor.removeChange')"
        @click="emit('remove')"
      />
    </header>

    <div class="field">
      <span :id="`${prefix}-step-label`" class="field-label">{{ t('recipes.variations.editor.step') }}</span>
      <Select
        :model-value="stepValue"
        :options="stepOptions"
        option-label="label"
        option-value="value"
        fluid
        :aria-labelledby="`${prefix}-step-label`"
        @update:model-value="setStep"
      />
    </div>

    <template v-if="change.kind === 'swap' || change.kind === 'remove_line'">
      <div class="field">
        <span :id="`${prefix}-line-label`" class="field-label">{{ t('recipes.variations.editor.line') }}</span>
        <Select
          :model-value="targetValue"
          :options="targetOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('recipes.variations.editor.linePlaceholder')"
          fluid
          :aria-labelledby="`${prefix}-line-label`"
          @update:model-value="pickTarget"
        />
      </div>
    </template>

    <template v-if="change.kind === 'swap'">
      <div class="field">
        <label :for="`${prefix}-to`" class="field-label">{{ t('recipes.variations.editor.swapTo') }}</label>
        <p v-if="change.to_name" class="change-editor-picked">
          <span class="mdi mdi-swap-horizontal" aria-hidden="true" />
          {{ change.to_name }}
        </p>
        <IngredientSearch :input-id="`${prefix}-to`" :can-create="canCreateIngredient" :exclude-recipe-id="recipe.id" @select="pickReplacement" />
      </div>
      <div class="change-editor-switch">
        <ToggleSwitch v-model="change.keep_amount" :input-id="`${prefix}-keep`" />
        <label :for="`${prefix}-keep`">{{ t('recipes.variations.editor.keepAmount') }}</label>
      </div>
      <small v-if="change.keep_amount" class="field-hint">{{ t('recipes.variations.editor.keepAmountHint') }}</small>
      <div v-else class="change-editor-amount">
        <div class="field">
          <label :for="`${prefix}-amount`" class="field-label">{{ t('recipes.editor.amount') }}</label>
          <InputNumber v-model="change.amount" :input-id="`${prefix}-amount`" :min="0" :max-fraction-digits="3" fluid />
        </div>
        <div class="field">
          <span :id="`${prefix}-unit-label`" class="field-label">{{ t('recipes.editor.unit') }}</span>
          <UnitSelect v-model="change.unit_id" :units="units" :ingredient="weights.weightsOf(change.to_ingredient_id)" :placeholder="t('recipes.editor.unit')" show-clear fluid :aria-labelledby="`${prefix}-unit-label`" />
        </div>
        <div class="field change-editor-wide">
          <label :for="`${prefix}-note`" class="field-label">{{ t('recipes.editor.note') }}</label>
          <InputText :id="`${prefix}-note`" v-model="change.note" :placeholder="t('recipes.editor.notePlaceholder')" fluid />
        </div>
      </div>
    </template>

    <template v-else-if="change.kind === 'add_line'">
      <div class="field">
        <label :for="`${prefix}-add`" class="field-label">{{ t('recipes.variations.editor.line') }}</label>
        <p v-if="change.target_name" class="change-editor-picked">
          <span class="mdi mdi-plus-circle-outline" aria-hidden="true" />
          {{ change.target_name }}
        </p>
        <IngredientSearch :input-id="`${prefix}-add`" :can-create="canCreateIngredient" :exclude-recipe-id="recipe.id" @select="pickAdded" />
      </div>
      <div class="change-editor-amount">
        <div class="field">
          <label :for="`${prefix}-amount`" class="field-label">{{ t('recipes.editor.amount') }}</label>
          <InputNumber v-model="change.amount" :input-id="`${prefix}-amount`" :min="0" :max-fraction-digits="3" fluid />
        </div>
        <div class="field">
          <span :id="`${prefix}-unit-label`" class="field-label">{{ t('recipes.editor.unit') }}</span>
          <UnitSelect v-model="change.unit_id" :units="units" :ingredient="weights.weightsOf(change.ingredient_id)" :placeholder="t('recipes.editor.unit')" show-clear fluid :aria-labelledby="`${prefix}-unit-label`" />
        </div>
        <div class="field change-editor-wide">
          <label :for="`${prefix}-note`" class="field-label">{{ t('recipes.editor.note') }}</label>
          <InputText :id="`${prefix}-note`" v-model="change.note" :placeholder="t('recipes.editor.notePlaceholder')" fluid />
        </div>
      </div>
    </template>

    <template v-else-if="change.kind === 'step_text'">
      <div v-if="step" class="change-editor-current">
        <p class="hint">{{ t('recipes.variations.editor.currentText') }}</p>
        <RichText :text="step.text" :resolve="lineResolver(step.ingredients, { equipment: step.equipment })" />
      </div>
      <div class="field">
        <span :id="`${prefix}-text-label`" class="field-label">{{ t('recipes.variations.editor.newText') }}</span>
        <RichTextEditor
          :key="`${prefix}-${change.step}`"
          v-model="change.text"
          :labelledby="`${prefix}-text-label`"
          :rows="3"
          :invalid="invalid && !change.text.trim()"
          mentionable
          :mentions="stepTextMentions"
        />
        <small class="field-hint">{{ t('recipes.variations.editor.mentionHint') }}</small>
      </div>
    </template>

    <template v-else-if="change.kind === 'extra_step'">
      <div class="field">
        <span :id="`${prefix}-text-label`" class="field-label">{{ t('recipes.variations.editor.newText') }}</span>
        <RichTextEditor
          v-model="change.text"
          :labelledby="`${prefix}-text-label`"
          :rows="3"
          :invalid="invalid && !change.text.trim()"
          mentionable
          :mentions="extraMentions"
        />
        <small class="field-hint">{{ t('recipes.editor.mentionHint') }}</small>
      </div>
      <div class="field">
        <label :for="`${prefix}-duration`" class="field-label">{{ t('recipes.editor.duration') }}</label>
        <InputNumber v-model="change.duration_minutes" :input-id="`${prefix}-duration`" :min="1" :max="1440" :suffix="` ${t('recipes.editor.minutesSuffix')}`" fluid />
      </div>
      <div class="field">
        <span class="field-label">{{ t('recipes.variations.editor.extraLines') }}</span>
        <ul v-if="change.lines.length" class="change-editor-lines">
          <li v-for="(line, i) in change.lines" :key="line.key" class="change-editor-line">
            <span class="change-editor-line-name">{{ line.name }}</span>
            <InputNumber v-model="line.amount" :input-id="`${prefix}-l-${line.key}`" :min="0" :max-fraction-digits="3" :aria-label="t('recipes.editor.amount')" fluid />
            <UnitSelect v-model="line.unit_id" :units="units" :ingredient="weights.weightsOf(line.ingredient_id)" :placeholder="t('recipes.editor.unit')" show-clear fluid :aria-label="t('recipes.editor.unit')" />
            <InputText v-model="line.note" :placeholder="t('recipes.editor.notePlaceholder')" :aria-label="t('recipes.editor.note')" fluid />
            <Button icon="mdi mdi-close" text rounded severity="secondary" :aria-label="t('recipes.editor.removeIngredient', { name: line.name })" @click="removeExtraLine(change, i)" />
          </li>
        </ul>
        <IngredientSearch :input-id="`${prefix}-extra-add`" :can-create="canCreateIngredient" :exclude-recipe-id="recipe.id" @select="addExtra" />
      </div>
      <div class="field">
        <label :id="`${prefix}-eq-label`" :for="`${prefix}-eq-add`" class="field-label">{{ t('recipes.variations.editor.extraEquipment') }}</label>
        <ul v-if="change.equipment.length" class="change-editor-lines">
          <li v-for="(item, i) in change.equipment" :key="item.key" class="change-editor-line change-editor-line--equipment">
            <span class="change-editor-line-name">{{ item.name }}</span>
            <InputNumber v-model="item.count" :min="1" :max="99" :aria-label="t('recipes.equipment.count')" fluid />
            <Button icon="mdi mdi-close" text rounded severity="secondary" :aria-label="t('recipes.editor.removeIngredient', { name: item.name })" @click="removeExtraEquipment(change, i)" />
          </li>
        </ul>
        <EquipmentSearch
          :input-id="`${prefix}-eq-add`"
          :equipment="equipment"
          :taken="takenEquipment"
          @select="(item) => addExtraEquipment(change, item)"
        />
      </div>
    </template>
  </section>
</template>

<style scoped lang="scss">
.change-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-content-background);
}

.change-editor--invalid {
  border-color: var(--p-red-500);
}

.change-editor-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);

  h3 {
    font-size: var(--font-size-lg);
  }
}

.change-editor-kind {
  flex: 1;
  min-width: 0;
}

.change-editor-picked {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: 700;
}

.change-editor-switch {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.change-editor-amount {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.change-editor-wide {
  grid-column: 1 / -1;
}

.change-editor-current {
  padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
}

.change-editor-lines {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0 0 var(--space-2);
  padding: 0;
  list-style: none;
}

// A phone stacks the name over amount and unit; wider screens put a line in one row.
.change-editor-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
}

.change-editor-line-name {
  grid-column: 1 / -1;
  font-weight: 700;
}

.change-editor-line--equipment {
  grid-template-columns: minmax(0, 1fr) auto;
}

@media (min-width: $bp-md) {
  .change-editor-amount {
    grid-template-columns: 8rem 10rem minmax(0, 1fr);
  }

  .change-editor-wide {
    grid-column: auto;
  }

  .change-editor-line {
    grid-template-columns: minmax(8rem, 1fr) 7rem 9rem minmax(0, 1fr) auto;
  }

  .change-editor-line-name {
    grid-column: auto;
  }

  .change-editor-line--equipment {
    grid-template-columns: minmax(8rem, 1fr) 7rem auto;
  }
}
</style>
