<script setup lang="ts">
/**
 * Logs a cooked meal after the fact, or changes one of the user's own
 * entries. Cook mode logs the usual case; this covers forgotten ones.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import RecipePicker from '@/shared/cookbook/RecipePicker.vue'
import type { RecipeSummaryResponse } from '@/shared/cookbook/types'
import type { Schemas } from '@/core/api/generated'

type CookEvent = Schemas['CookEventResponse']

const props = defineProps<{ date: string; editing: CookEvent | null; saving: boolean }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{
  create: [value: { recipe_id: string; cooked_on: string; servings: number; note: string }]
  update: [value: { cooked_on: string; servings: number; note: string }]
  remove: []
}>()

const { t } = useI18n()
const recipe = ref<RecipeSummaryResponse | null>(null)
const cookedOn = ref('')
const servings = ref(2)
const note = ref('')

watch(recipe, (r) => {
  if (r && typeof r === 'object') servings.value = r.base_servings
})

function onShow() {
  recipe.value = null
  cookedOn.value = props.editing?.cooked_on ?? props.date
  servings.value = props.editing?.servings ?? 2
  note.value = props.editing?.note ?? ''
}

function submit() {
  const base = { cooked_on: cookedOn.value, servings: servings.value, note: note.value.trim() }
  if (props.editing) {
    emit('update', base)
    return
  }
  if (!recipe.value || typeof recipe.value !== 'object') return
  emit('create', { recipe_id: recipe.value.id, ...base })
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="editing ? t('cooked.editEvent') : t('cooked.logEvent')"
    class="event-dialog"
    @show="onShow"
  >
    <form class="event-form" @submit.prevent="submit">
      <div v-if="!editing" class="field">
        <label for="event-recipe">{{ t('cooked.recipe') }}</label>
        <RecipePicker v-model="recipe" input-id="event-recipe" :placeholder="t('cooked.recipeSearch')" />
      </div>
      <p v-else class="event-recipe">{{ editing.recipe?.title }}</p>
      <div class="event-grid">
        <div class="field">
          <label for="event-date">{{ t('cooked.date') }}</label>
          <InputText id="event-date" v-model="cookedOn" type="date" required fluid />
        </div>
        <div class="field">
          <label for="event-servings">{{ t('cooked.servings') }}</label>
          <InputNumber v-model="servings" input-id="event-servings" :min="1" :max="99" show-buttons fluid />
        </div>
      </div>
      <div class="field">
        <label for="event-note">{{ t('cooked.note') }}</label>
        <Textarea id="event-note" v-model="note" rows="2" auto-resize fluid :placeholder="t('cooked.notePlaceholder')" />
        <small class="field-hint">{{ t('cooked.noteHint') }}</small>
      </div>
      <div class="event-actions">
        <Button
          v-if="editing"
          type="button"
          :label="t('common.delete')"
          icon="mdi mdi-delete-outline"
          severity="danger"
          text
          class="event-delete"
          @click="emit('remove')"
        />
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.event-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.event-form {
  display: grid;
  gap: var(--space-3);
}

.event-recipe {
  margin: 0;
  font-weight: 700;
}

.event-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.event-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

.event-delete {
  margin-right: auto;
}
</style>
