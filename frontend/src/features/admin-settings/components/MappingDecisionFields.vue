<script setup lang="ts">
/**
 * The decision for one catalogue entry of a paired instance: map it to a
 * local entry, create it here from the peer's data, keep it as plain text,
 * or leave it out, as the entry's kind allows. Mapping an ingredient uses the
 * ingredient picker; units, tags and equipment pick from their lists. A new
 * ingredient may get a category, else it stays uncategorised.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { ACTIONS, type DecisionState, type EntryKind } from '@/features/admin-settings/incomingRecipes'
import IngredientPicker from '@/shared/cookbook/IngredientPicker.vue'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'
import type { EquipmentResponse, IngredientResponse } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'

const props = withDefaults(
  defineProps<{
    kind: EntryKind
    /** Unique per row, for the ids of the controls. */
    idBase: string
    equipment?: EquipmentResponse[]
    invalid?: boolean
  }>(),
  { equipment: () => [], invalid: false },
)
const model = defineModel<DecisionState>({ required: true })

const { t } = useI18n()
const resources = useCookbookResources()

const actions = computed(() =>
  ACTIONS[props.kind].map((value) => ({ value, label: t(`adminArea.incoming.actions.${value}`) })),
)
// Units, tags and equipment pick from a list; ingredients search the catalogue.
const listed = computed(() => {
  if (props.kind === 'unit') return resources.units.value.map((u) => ({ id: u.id, name: `${u.name} (${u.code})` }))
  if (props.kind === 'tag') return resources.tags.value.map((tag) => ({ id: tag.id, name: tag.name }))
  if (props.kind === 'equipment') return props.equipment.map((e) => ({ id: e.id, name: e.name }))
  return []
})
const categories = computed(() => resources.categories.value.map((c) => ({ id: c.id, name: c.name })))
// The ingredient chosen in the picker, kept apart from the decision so the
// picker shows what was picked.
const picked = ref<IngredientResponse | null>(null)

function setAction(action: DecisionState['action']) {
  model.value = { ...model.value, action }
}

function setTarget(id: string | null) {
  const found = listed.value.find((o) => o.id === id)
  model.value = { ...model.value, target_id: id, target_name: found?.name ?? null }
}

function pickIngredient(ingredient: IngredientResponse | null) {
  picked.value = ingredient
  if (ingredient) model.value = { ...model.value, target_id: ingredient.id, target_name: ingredient.name }
}

function setCategory(id: string | null) {
  model.value = { ...model.value, category_id: id }
}
</script>

<template>
  <div class="decision" :class="{ 'decision--invalid': invalid }">
    <div class="field">
      <label :id="`${idBase}-action-label`" :for="`${idBase}-action`" class="visually-hidden">
        {{ t('adminArea.incoming.decision') }}
      </label>
      <Select
        :id="`${idBase}-action`"
        :model-value="model.action"
        :options="actions"
        option-label="label"
        option-value="value"
        :aria-labelledby="`${idBase}-action-label`"
        :invalid="invalid"
        fluid
        @update:model-value="setAction"
      />
    </div>
    <template v-if="model.action === 'map'">
      <div v-if="kind === 'ingredient'" class="field">
        <label :for="`${idBase}-target`" class="field-label">
          {{ model.target_name ? t('adminArea.incoming.mappedTo', { name: model.target_name }) : t('adminArea.incoming.pickTarget') }}
        </label>
        <IngredientPicker
          :model-value="picked"
          :input-id="`${idBase}-target`"
          :placeholder="t('adminArea.incoming.searchIngredient')"
          @update:model-value="pickIngredient"
        />
      </div>
      <div v-else class="field">
        <label :id="`${idBase}-target-label`" :for="`${idBase}-target`" class="field-label">
          {{ t('adminArea.incoming.pickTarget') }}
        </label>
        <UnitSelect
          v-if="kind === 'unit'"
          :id="`${idBase}-target`"
          :model-value="model.target_id"
          :units="resources.units.value"
          :placeholder="model.target_name ?? t('adminArea.incoming.pickTarget')"
          :aria-labelledby="`${idBase}-target-label`"
          :invalid="invalid && !model.target_id"
          fluid
          @update:model-value="setTarget"
        />
        <Select
          v-else
          :id="`${idBase}-target`"
          :model-value="model.target_id"
          :options="listed"
          option-label="name"
          option-value="id"
          filter
          :placeholder="model.target_name ?? t('adminArea.incoming.pickTarget')"
          :aria-labelledby="`${idBase}-target-label`"
          :invalid="invalid && !model.target_id"
          fluid
          @update:model-value="setTarget"
        />
      </div>
    </template>
    <div v-if="model.action === 'create' && kind === 'ingredient'" class="field">
      <label :id="`${idBase}-category-label`" :for="`${idBase}-category`" class="field-label">
        {{ t('adminArea.incoming.category') }}
      </label>
      <Select
        :id="`${idBase}-category`"
        :model-value="model.category_id"
        :options="categories"
        option-label="name"
        option-value="id"
        show-clear
        filter
        :placeholder="t('adminArea.incoming.uncategorised')"
        :aria-labelledby="`${idBase}-category-label`"
        fluid
        @update:model-value="setCategory"
      />
    </div>
    <small v-if="model.action === 'create'" class="field-hint">{{ t(`adminArea.incoming.createHint.${kind}`) }}</small>
    <small v-else-if="model.action === 'plain'" class="field-hint">{{ t('adminArea.incoming.plainHint') }}</small>
    <small v-else-if="model.action === 'none'" class="field-hint">{{ t(`adminArea.incoming.noneHint.${kind}`) }}</small>
  </div>
</template>

<style scoped lang="scss">
.decision {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.decision--invalid {
  padding: var(--space-2);
  border: 1px solid var(--p-red-500);
  border-radius: var(--p-border-radius-md);
}
</style>
