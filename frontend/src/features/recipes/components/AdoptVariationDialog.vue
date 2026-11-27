<script setup lang="ts">
/**
 * Adopts a variation into the original, for the recipe's editors: all its
 * changes or the chosen ones, then a preview of what the original gets
 * before the save. The original records an `adopted` revision crediting
 * the variation's author.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import { adoptVariation, type VariationResponse } from '@/features/recipes/api/recipes'
import VariationChangeSummary from '@/features/recipes/components/VariationChangeSummary.vue'
import {
  adoptableChanges,
  adoptPayload,
  chosenChanges,
  selectAll,
  toggleChange,
} from '@/features/recipes/utils/adoptSelection'
import { staleStep } from '@/features/recipes/utils/variations'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ recipeId: string; variation: VariationResponse }>()
const emit = defineEmits<{ adopted: [variation: VariationResponse] }>()

const { t } = useI18n()
const toast = useAppToast()

const mode = ref<'all' | 'choose'>('all')
const selected = ref<string[]>([])
const previewing = ref(false)
const note = ref('')
const saving = ref(false)

watch(visible, (open) => {
  if (!open) return
  mode.value = 'all'
  selected.value = selectAll(props.variation)
  previewing.value = false
  note.value = ''
})

const adoptable = computed(() => adoptableChanges(props.variation))
const chosenIds = computed(() => (mode.value === 'all' ? selectAll(props.variation) : selected.value))
const chosen = computed(() => chosenChanges(props.variation, chosenIds.value))
const modes = computed(() => [
  { value: 'all', label: t('recipes.variations.adoptDialog.all') },
  { value: 'choose', label: t('recipes.variations.adoptDialog.choose') },
])

function toggle(id: string) {
  selected.value = toggleChange(selected.value, id)
}

async function confirm() {
  saving.value = true
  try {
    const result = await adoptVariation(
      props.recipeId,
      props.variation.id,
      adoptPayload(props.variation, chosenIds.value),
      note.value.trim() || null,
    )
    toast.success(t('recipes.variations.adoptDialog.done'))
    emit('adopted', result.variation)
    visible.value = false
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('recipes.variations.adoptDialog.title', { name: variation.name })"
    :style="{ width: 'var(--dialog-width-md)' }"
  >
    <div class="adopt">
      <p class="hint">
        {{
          variation.author
            ? t('recipes.variations.adoptDialog.hint', { name: variation.author.display_name })
            : t('recipes.variations.adoptDialog.hintAnonymous')
        }}
      </p>
      <p v-if="!adoptable.length" class="hint">{{ t('recipes.variations.adoptDialog.none') }}</p>

      <template v-else-if="!previewing">
        <SelectButton
          v-model="mode"
          :options="modes"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          :aria-label="t('recipes.variations.adoptDialog.choose')"
        />
        <ul class="adopt-list">
          <li v-for="change in variation.changes" :key="change.id" class="adopt-item">
            <Checkbox
              v-if="mode === 'choose'"
              :input-id="`adopt-${change.id}`"
              :model-value="selected.includes(change.id)"
              binary
              :disabled="!change.available || !change.applies"
              :data-testid="`adopt-${change.id}`"
              @update:model-value="toggle(change.id)"
            />
            <label :for="mode === 'choose' ? `adopt-${change.id}` : undefined" class="adopt-label">
              <VariationChangeSummary :change="change" :stale="staleStep(variation, change.step)" show-step />
            </label>
          </li>
        </ul>
      </template>

      <template v-else>
        <h3 class="adopt-preview-title">{{ t('recipes.variations.adoptDialog.previewTitle') }}</h3>
        <ol class="adopt-list adopt-preview" data-testid="adopt-preview">
          <li v-for="change in chosen" :key="change.id">
            <VariationChangeSummary :change="change" show-step />
          </li>
        </ol>
        <div class="field">
          <label for="adopt-note" class="field-label">{{ t('recipes.variations.adoptDialog.revisionNote') }}</label>
          <InputText id="adopt-note" v-model="note" maxlength="500" fluid />
        </div>
      </template>

      <div class="row-actions">
        <Button
          v-if="previewing"
          :label="t('recipes.variations.adoptDialog.back')"
          text
          severity="secondary"
          @click="previewing = false"
        />
        <Button v-else :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button
          v-if="!previewing"
          :label="t('recipes.variations.adoptDialog.preview')"
          icon="mdi mdi-eye-outline"
          :disabled="!chosen.length"
          @click="previewing = true"
        />
        <Button
          v-else
          :label="t('recipes.variations.adoptDialog.confirm', { n: chosen.length }, chosen.length)"
          icon="mdi mdi-check"
          :loading="saving"
          @click="confirm"
        />
      </div>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.adopt {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.adopt-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.adopt-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.adopt-label {
  flex: 1;
  min-width: 0;
}

.adopt-preview {
  padding-left: var(--space-2);
}

.adopt-preview-title {
  font-size: var(--font-size-lg);
}
</style>
