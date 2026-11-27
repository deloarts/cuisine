<script setup lang="ts">
/**
 * Says that an editor brought back the user's unsaved changes from this
 * device, and when they were made, with a button that drops them and puts
 * the saved version back. When the saved version changed after the draft was
 * stored, it says so, so the user checks the changes before saving over it.
 * It also says when images of the draft were gone and had to be removed.
 */
import { useI18n } from 'vue-i18n'

import { formatDateTime } from '@/core/utils/dates'
import type { RestoredDraft } from '@/features/recipes/composables/useEditorDraft'

defineProps<{ draft: RestoredDraft }>()
defineEmits<{ discard: [] }>()

const { t } = useI18n()
</script>

<template>
  <Message :severity="draft.serverChanged ? 'warn' : 'info'" data-testid="draft-notice">
    <div class="draft-notice">
      <span>
        {{
          draft.serverChanged
            ? t('recipes.editorDraft.restoredChanged', { time: formatDateTime(draft.savedAt) })
            : t('recipes.editorDraft.restored', { time: formatDateTime(draft.savedAt) })
        }}
        <template v-if="draft.droppedImages">
          {{ t('recipes.editorDraft.imagesDropped', draft.droppedImages) }}
        </template>
      </span>
      <Button
        :label="t('recipes.editorDraft.discard')"
        size="small"
        text
        data-testid="draft-discard"
        @click="$emit('discard')"
      />
    </div>
  </Message>
</template>

<style scoped lang="scss">
.draft-notice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
</style>
