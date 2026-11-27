<script setup lang="ts">
/**
 * Plans one meal: a recipe from the cookbook or just a line of text such as
 * "Leftovers" or "Pizza out", with the servings to cook. A new meal may start
 * with a recipe already chosen (`preset`), as when a suggestion is planned.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import RecipePicker from '@/shared/cookbook/RecipePicker.vue'
import type { MealSlot, RecipeSummaryResponse } from '@/shared/cookbook/types'
import { SLOTS } from '@/features/meal-plan/week'

export interface EntryForm {
  plan_date: string
  slot: MealSlot
  recipe_id: string | null
  title: string
  servings: number
}

const props = defineProps<{
  date: string
  mealSlot: MealSlot
  saving: boolean
  editing: { recipeTitle: string | null; recipeId: string | null; title: string; servings: number } | null
  preset?: { recipeTitle: string; recipeId: string; servings: number } | null
}>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ submit: [value: EntryForm]; remove: [] }>()

const { t } = useI18n()
const mode = ref<'recipe' | 'text'>('recipe')
const recipe = ref<RecipeSummaryResponse | null>(null)
const keptRecipeId = ref<string | null>(null)
const title = ref('')
const servings = ref(2)
const slotValue = ref<MealSlot>('dinner')
const dateValue = ref('')

const modeOptions = computed(() => [
  { value: 'recipe', label: t('mealPlan.fromRecipe') },
  { value: 'text', label: t('mealPlan.freeText') },
])
const slotOptions = computed(() => SLOTS.map((s) => ({ value: s, label: t(`mealPlan.slots.${s}`) })))

watch(recipe, (r) => {
  if (r && typeof r === 'object') servings.value = r.base_servings
})

function onShow() {
  dateValue.value = props.date
  slotValue.value = props.mealSlot
  const e = props.editing
  const preset = e ? null : props.preset
  recipe.value = null
  keptRecipeId.value = e?.recipeId ?? preset?.recipeId ?? null
  mode.value = e && !e.recipeId ? 'text' : 'recipe'
  title.value = e?.recipeId ? '' : (e?.title ?? '')
  servings.value = e?.servings ?? preset?.servings ?? 2
}

const recipeLabel = computed(() => props.editing?.recipeTitle ?? (props.editing ? '' : props.preset?.recipeTitle) ?? '')

function submit() {
  const picked = recipe.value && typeof recipe.value === 'object' ? recipe.value : null
  if (mode.value === 'recipe') {
    const recipeId = picked?.id ?? keptRecipeId.value
    if (!recipeId) return
    emit('submit', {
      plan_date: dateValue.value,
      slot: slotValue.value,
      recipe_id: recipeId,
      title: picked?.title ?? recipeLabel.value,
      servings: servings.value,
    })
  } else {
    if (!title.value.trim()) return
    emit('submit', { plan_date: dateValue.value, slot: slotValue.value, recipe_id: null, title: title.value.trim(), servings: servings.value })
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="editing ? t('mealPlan.editEntry') : t('mealPlan.addEntry')"
    class="entry-dialog"
    @show="onShow"
  >
    <form class="entry-form" @submit.prevent="submit">
      <SelectButton
        v-model="mode"
        :options="modeOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        :aria-label="t('mealPlan.kind')"
      />
      <div v-if="mode === 'recipe'" class="field">
        <label for="entry-recipe">{{ t('mealPlan.recipe') }}</label>
        <RecipePicker
          v-model="recipe"
          input-id="entry-recipe"
          :placeholder="keptRecipeId ? recipeLabel : t('mealPlan.recipeSearch')"
        />
      </div>
      <div v-else class="field">
        <label for="entry-title">{{ t('mealPlan.what') }}</label>
        <InputText id="entry-title" v-model="title" :placeholder="t('mealPlan.whatPlaceholder')" fluid />
      </div>
      <div class="entry-grid">
        <div class="field">
          <label for="entry-date">{{ t('mealPlan.date') }}</label>
          <InputText id="entry-date" v-model="dateValue" type="date" required fluid />
        </div>
        <div class="field">
          <label id="entry-slot-label" for="entry-slot">{{ t('mealPlan.slot') }}</label>
          <Select
            id="entry-slot"
            v-model="slotValue"
            :options="slotOptions"
            option-label="label"
            option-value="value"
            aria-labelledby="entry-slot-label"
            fluid
          />
        </div>
        <div class="field">
          <label for="entry-servings">{{ t('mealPlan.servings') }}</label>
          <InputNumber v-model="servings" input-id="entry-servings" :min="1" :max="99" show-buttons fluid />
        </div>
      </div>
      <div class="entry-actions">
        <Button
          v-if="editing"
          type="button"
          :label="t('common.delete')"
          icon="mdi mdi-delete-outline"
          severity="danger"
          text
          class="entry-delete"
          @click="emit('remove')"
        />
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.entry-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.entry-form {
  display: grid;
  gap: var(--space-3);
}

.entry-grid {
  display: grid;
  gap: var(--space-2);
}

.entry-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

.entry-delete {
  margin-right: auto;
}

@media (min-width: $bp-sm) {
  .entry-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
