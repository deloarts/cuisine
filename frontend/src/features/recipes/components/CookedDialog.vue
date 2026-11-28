<script setup lang="ts">
/**
 * Logs a meal: "I cooked this", with the day, the servings and an optional
 * note, naming the variation when one was cooked. A recipe is logged at most
 * once a day; a day that already has it is named in the dialog, which stays
 * open with the note so another day can be picked.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { errorCode } from '@/core/utils/errors'
import { logCookEvent, type CookEventResponse } from '@/features/recipes/api/recipes'
import { isoDay } from '@/features/recipes/utils/dates'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ recipeId: string; servings: number; variationId?: string | null }>()
const emit = defineEmits<{ logged: [event: CookEventResponse] }>()

const { t } = useI18n()
const toast = useAppToast()

const day = ref(new Date())
const servings = ref(props.servings)
const note = ref('')
const saving = ref(false)
const alreadyLogged = ref(false)

watch(visible, (open) => {
  if (open) {
    day.value = new Date()
    servings.value = props.servings
    note.value = ''
    alreadyLogged.value = false
  }
})
watch(day, () => {
  alreadyLogged.value = false
})

async function save() {
  saving.value = true
  alreadyLogged.value = false
  try {
    const event = await logCookEvent(
      props.recipeId,
      isoDay(day.value),
      servings.value,
      note.value.trim(),
      props.variationId ?? null,
    )
    toast.success(t('recipes.cooked.saved'))
    emit('logged', event)
    visible.value = false
  } catch (err) {
    if (errorCode(err) === 'CookEventExistsError') alreadyLogged.value = true
    else toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('recipes.cooked.dialogTitle')"
    :style="{ width: 'var(--dialog-width-sm)' }"
  >
    <form class="cooked-form" @submit.prevent="save">
      <div class="field">
        <label for="cooked-day" class="field-label">{{ t('recipes.cooked.date') }}</label>
        <DatePicker
          v-model="day"
          input-id="cooked-day"
          :max-date="new Date()"
          show-icon
          fluid
          date-format="dd.mm.yy"
        />
        <Message v-if="alreadyLogged" severity="warn" size="small" variant="simple" data-testid="cooked-exists">
          {{ t('errors.CookEventExistsError') }}
        </Message>
      </div>
      <div class="field">
        <label for="cooked-servings" class="field-label">{{ t('recipes.cooked.servings') }}</label>
        <InputNumber
          v-model="servings"
          input-id="cooked-servings"
          :min="1"
          :max="99"
          show-buttons
          fluid
        />
      </div>
      <div class="field">
        <label for="cooked-note" class="field-label">{{ t('recipes.cooked.note') }}</label>
        <Textarea
          id="cooked-note"
          v-model="note"
          rows="2"
          auto-resize
          fluid
          :placeholder="t('recipes.cooked.notePlaceholder')"
        />
        <small class="field-hint">{{ t('recipes.cooked.noteHint') }}</small>
      </div>
      <div class="row-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button type="submit" :label="t('recipes.cooked.save')" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.cooked-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
</style>
