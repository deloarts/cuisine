<script setup lang="ts">
/**
 * Deleting a recipe for good. It first asks the backend what the deletion
 * touches: a recipe another one uses as a sub-recipe cannot go, and the
 * dialog lists those recipes (the ones the reader may see, plus a count of
 * the rest). Otherwise the cook confirms by typing the recipe's name.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppToast } from '@/core/composables/useAppToast'
import {
  deleteRecipe,
  getDeletionImpact,
  type RecipeDeletionImpact,
} from '@/features/recipes/api/recipes'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ recipeId: string; title: string }>()
const emit = defineEmits<{ deleted: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const impact = ref<RecipeDeletionImpact | null>(null)
const typed = ref('')
const deleting = ref(false)

const matches = computed(() => typed.value.trim() === props.title.trim())

watch(visible, async (open) => {
  if (!open) return
  impact.value = null
  typed.value = ''
  try {
    impact.value = await getDeletionImpact(props.recipeId)
  } catch (err) {
    toast.error(err)
    visible.value = false
  }
})

async function remove() {
  if (!matches.value || impact.value?.blocked) return
  deleting.value = true
  try {
    await deleteRecipe(props.recipeId)
    toast.success(t('recipes.delete.done', { title: props.title }))
    visible.value = false
    emit('deleted')
  } catch (err) {
    toast.error(err)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('recipes.delete.title')"
    :style="{ width: 'var(--dialog-width-sm)' }"
  >
    <div
      v-if="!impact"
      class="delete-body"
      role="status"
      :aria-label="t('recipes.loading')"
      data-testid="delete-skeleton"
    >
      <Skeleton height="0.875rem" />
      <Skeleton width="60%" height="0.875rem" />
      <Skeleton height="2.75rem" />
      <div class="row-actions">
        <Skeleton width="6rem" height="2.5rem" />
        <Skeleton width="8rem" height="2.5rem" />
      </div>
    </div>
    <div v-else-if="impact.blocked" class="delete-body">
      <Message severity="warn">{{ t('recipes.delete.blocked', { title }) }}</Message>
      <ul v-if="impact.used_by.length" class="delete-users">
        <li v-for="user in impact.used_by" :key="user.id">
          <RouterLink :to="{ name: 'recipe', params: { id: user.id } }" @click="visible = false">
            {{ user.title }}
          </RouterLink>
        </li>
      </ul>
      <p v-if="impact.used_by_hidden_count" class="hint">
        {{ t('recipes.delete.hiddenUsers', { n: impact.used_by_hidden_count }, impact.used_by_hidden_count) }}
      </p>
      <div class="row-actions">
        <Button :label="t('common.close')" severity="secondary" @click="visible = false" />
      </div>
    </div>
    <form v-else class="delete-body" @submit.prevent="remove">
      <p>{{ t('recipes.delete.what') }}</p>
      <div class="field">
        <label for="delete-confirm-name" class="field-label">
          {{ t('recipes.delete.typeName', { title }) }}
        </label>
        <InputText id="delete-confirm-name" v-model="typed" fluid autocomplete="off" />
      </div>
      <div class="row-actions">
        <Button :label="t('common.cancel')" text severity="secondary" @click="visible = false" />
        <Button
          type="submit"
          :label="t('recipes.delete.confirm')"
          severity="danger"
          :disabled="!matches"
          :loading="deleting"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.delete-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.delete-users {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-5);
}
</style>
