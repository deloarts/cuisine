<script setup lang="ts">
/**
 * Deleting or merging a catalogue ingredient. The dialog first asks the
 * backend what a deletion would touch: a seeded ingredient cannot be
 * deleted, one that recipes use is blocked (the dialog names the recipes the
 * reader may see) and can only be merged into another ingredient, which
 * needs manage:ingredients. Merging repoints recipe lines, shopping items
 * and food restrictions and keeps the merged names as aliases of the
 * target. An unused ingredient is deleted after a confirmation.
 *
 * `mode` "merge" opens straight at the merge step, for the editor's own
 * merge action.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import IngredientPicker from '@/shared/cookbook/IngredientPicker.vue'
import type { IngredientResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import {
  deleteIngredient,
  ingredientDeletionImpact,
  mergeIngredient,
  type IngredientDeletionImpact,
  type IngredientDetail,
} from '@/features/ingredients/api/ingredients'
import DialogBodySkeleton from '@/shared/components/skeleton/DialogBodySkeleton.vue'

const visible = defineModel<boolean>('visible', { required: true })
const props = withDefaults(
  defineProps<{ ingredientId: string; name: string; mode?: 'delete' | 'merge' }>(),
  { mode: 'delete' },
)
const emit = defineEmits<{ deleted: []; merged: [target: IngredientDetail] }>()

const { t } = useI18n()
const toast = useAppToast()

const impact = ref<IngredientDeletionImpact | null>(null)
const merging = ref(false)
const target = ref<IngredientResponse | null>(null)
const busy = ref(false)

const sameAsSelf = computed(() => target.value?.id === props.ingredientId)
const hiddenRecipes = computed(() => (impact.value ? impact.value.recipe_count - impact.value.recipes.length : 0))
const header = computed(() => (merging.value ? t('ingredients.merge.title') : t('ingredients.delete.title')))

watch(visible, async (open) => {
  if (!open) return
  impact.value = null
  target.value = null
  merging.value = props.mode === 'merge'
  try {
    impact.value = await ingredientDeletionImpact(props.ingredientId)
  } catch (err) {
    toast.error(err)
    visible.value = false
  }
})

async function remove() {
  busy.value = true
  try {
    await deleteIngredient(props.ingredientId)
    toast.success(t('ingredients.delete.done', { name: props.name }))
    visible.value = false
    emit('deleted')
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function merge() {
  const into = target.value
  if (!into || sameAsSelf.value) return
  busy.value = true
  try {
    const result = await mergeIngredient(props.ingredientId, into.id)
    toast.success(t('ingredients.merge.done', { name: props.name, target: result.name }))
    visible.value = false
    emit('merged', result)
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="header" class="ingredient-dialog">
    <DialogBodySkeleton v-if="!impact" :label="t('ingredients.loading')" />

    <form v-else-if="merging" class="dialog-body" @submit.prevent="merge">
      <p>{{ t('ingredients.merge.what', { name }) }}</p>
      <Message v-if="impact.seeded" severity="info" :closable="false">{{ t('ingredients.merge.seeded') }}</Message>
      <div class="field">
        <label for="ingredient-merge-target">{{ t('ingredients.merge.into') }}</label>
        <IngredientPicker v-model="target" input-id="ingredient-merge-target" />
        <small v-if="sameAsSelf" class="field-hint">{{ t('ingredients.merge.notSelf') }}</small>
      </div>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button
          type="submit"
          :label="t('ingredients.merge.confirm')"
          icon="mdi mdi-call-merge"
          severity="danger"
          :disabled="!target || sameAsSelf || impact.seeded"
          :loading="busy"
        />
      </div>
    </form>

    <div v-else-if="impact.seeded" class="dialog-body">
      <Message severity="info" :closable="false">{{ t('ingredients.delete.seeded', { name }) }}</Message>
      <div class="dialog-actions">
        <Button :label="t('common.close')" severity="secondary" @click="visible = false" />
      </div>
    </div>

    <div v-else-if="impact.recipe_count > 0" class="dialog-body">
      <Message severity="warn" :closable="false">
        {{ t('ingredients.delete.inUse', { name, count: impact.recipe_count }, impact.recipe_count) }}
      </Message>
      <ul v-if="impact.recipes.length" class="recipe-list">
        <li v-for="recipe in impact.recipes" :key="recipe.id">
          <RouterLink :to="{ name: 'recipe', params: { id: recipe.id } }" @click="visible = false">
            {{ recipe.title }}
          </RouterLink>
        </li>
      </ul>
      <p v-if="hiddenRecipes > 0" class="hint">
        {{ t('ingredients.delete.hidden', { count: hiddenRecipes }, hiddenRecipes) }}
      </p>
      <p class="hint">
        {{ impact.can_merge ? t('ingredients.delete.mergeOffer') : t('ingredients.delete.askManager') }}
      </p>
      <div class="dialog-actions">
        <Button :label="t('common.close')" text severity="secondary" @click="visible = false" />
        <Button
          v-if="impact.can_merge"
          :label="t('ingredients.merge.open')"
          icon="mdi mdi-call-merge"
          @click="merging = true"
        />
      </div>
    </div>

    <div v-else class="dialog-body">
      <p>{{ t('ingredients.delete.confirm', { name }) }}</p>
      <div class="dialog-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button
          v-if="impact.can_merge"
          :label="t('ingredients.merge.open')"
          icon="mdi mdi-call-merge"
          text
          @click="merging = true"
        />
        <Button :label="t('common.delete')" icon="mdi mdi-delete-outline" severity="danger" :loading="busy" @click="remove" />
      </div>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.ingredient-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.dialog-body {
  display: grid;
  gap: var(--space-3);
}

.recipe-list {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-5);
}

.dialog-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
