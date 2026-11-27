<script setup lang="ts">
/**
 * One image of a recipe (its cover or a step's photo). Picking a file uploads
 * it straight away; the backend re-encodes it to WebP and strips its
 * metadata, and the field keeps only the stored file's id. A step's photo can
 * also come from the step image library, when the parent passes the step's
 * ingredients and equipment as `library`, which rank the library's photos.
 *
 * A button opens the file picker through a hidden input that never takes
 * focus. A focusable input hidden off the layout, as the `visually-hidden`
 * class does, sits where its positioned ancestor puts it, outside the
 * scrolling main area, so focusing it made the browser scroll the app shell
 * and left the header and the page shifted out of view.
 */
import { ref, useId, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { uploadImage } from '@/features/recipes/api/recipes'
import StepImageLibraryDialog from '@/features/recipes/components/StepImageLibraryDialog.vue'
import { imageUrl } from '@/shared/components/recipes/recipeImage'

const model = defineModel<string | null>({ required: true })
withDefaults(
  defineProps<{
    label: string
    compact?: boolean
    library?: { ingredientIds: string[]; equipmentIds: string[] } | null
  }>(),
  { compact: false, library: null },
)

const { t } = useI18n()
const toast = useAppToast()
const labelId = useId()
const uploading = ref(false)
const libraryOpen = ref(false)
const fileInput = useTemplateRef<HTMLInputElement>('file-input')

function choose() {
  fileInput.value?.click()
}

async function pick(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    const stored = await uploadImage(file)
    model.value = stored.id
  } catch (err) {
    toast.error(err)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div
    class="image-upload"
    :class="{ 'image-upload--compact': compact }"
    role="group"
    :aria-labelledby="labelId"
  >
    <span :id="labelId" class="field-label">{{ label }}</span>
    <div class="image-upload-preview">
      <img v-if="model" :src="imageUrl(model)" alt="" />
      <span v-else class="mdi mdi-image-outline" aria-hidden="true" />
      <ProgressSpinner v-if="uploading" class="image-upload-spinner" :aria-label="t('recipes.editor.uploading')" />
    </div>
    <div class="image-upload-actions">
      <Button
        :label="model ? t('recipes.editor.imageReplace') : t('recipes.editor.imageAdd')"
        icon="mdi mdi-camera-plus-outline"
        severity="secondary"
        outlined
        class="image-upload-pick"
        :disabled="uploading"
        data-testid="image-upload-pick"
        @click="choose"
      />
      <Button
        v-if="library"
        :label="t('recipes.editor.imageFromLibrary')"
        icon="mdi mdi-image-multiple-outline"
        severity="secondary"
        outlined
        class="image-upload-pick"
        :disabled="uploading"
        data-testid="image-upload-library"
        @click="libraryOpen = true"
      />
      <input
        ref="file-input"
        type="file"
        accept="image/*"
        hidden
        tabindex="-1"
        aria-hidden="true"
        :disabled="uploading"
        @change="pick"
      />
      <Button
        v-if="model"
        :label="t('recipes.editor.imageRemove')"
        icon="mdi mdi-delete-outline"
        severity="secondary"
        text
        size="small"
        @click="model = null"
      />
    </div>
    <StepImageLibraryDialog
      v-if="library"
      v-model:visible="libraryOpen"
      :ingredient-ids="library.ingredientIds"
      :equipment-ids="library.equipmentIds"
      :current="model"
      @pick="model = $event"
    />
  </div>
</template>

<style scoped lang="scss">
.image-upload {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.image-upload-preview {
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  aspect-ratio: 4 / 3;
  max-width: 24rem;
  overflow: hidden;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-50);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-3xl);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.image-upload--compact .image-upload-preview {
  max-width: 10rem;
}

.p-dark .image-upload-preview {
  background: var(--p-surface-900);
}

.image-upload-spinner {
  position: absolute;
  width: 2.5rem;
  height: 2.5rem;
}

.image-upload-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.image-upload-pick {
  min-height: 2.75rem;
}
</style>
