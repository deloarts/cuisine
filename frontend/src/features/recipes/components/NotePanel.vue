<script setup lang="ts">
/** The reader's private notes on a recipe, which nobody else sees. */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { saveNote } from '@/features/recipes/api/recipes'

const props = defineProps<{ recipeId: string; text: string | null }>()
const { t } = useI18n()
const toast = useAppToast()

const draft = ref(props.text ?? '')
const saved = ref(props.text ?? '')
const saving = ref(false)

watch(
  () => props.text,
  (text) => {
    draft.value = text ?? ''
    saved.value = text ?? ''
  },
)

async function save() {
  saving.value = true
  try {
    const result = await saveNote(props.recipeId, draft.value.trim())
    saved.value = result.text ?? ''
    draft.value = saved.value
    toast.success(t('recipes.note.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="note">
    <p class="hint">
      <span class="mdi mdi-lock-outline" aria-hidden="true" />
      {{ t('recipes.note.hint') }}
    </p>
    <label for="recipe-note" class="visually-hidden">{{ t('recipes.note.title') }}</label>
    <Textarea
      id="recipe-note"
      v-model="draft"
      rows="3"
      auto-resize
      fluid
      :placeholder="t('recipes.note.placeholder')"
    />
    <div class="row-actions">
      <Button
        :label="t('recipes.note.save')"
        :disabled="draft.trim() === saved.trim()"
        :loading="saving"
        @click="save"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.note {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
