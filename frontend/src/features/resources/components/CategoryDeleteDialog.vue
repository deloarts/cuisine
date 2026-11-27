<script setup lang="ts">
/**
 * Deleting an ingredient category. Its ingredients move to the category
 * chosen here, or to none, and shopping items fall into "Other".
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CategoryResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import { deleteCategory } from '@/features/resources/api/resources'

const visible = defineModel<boolean>('visible', { required: true })
const props = defineProps<{ category: CategoryResponse | null; categories: CategoryResponse[] }>()
const emit = defineEmits<{ done: [] }>()

const { t } = useI18n()
const toast = useAppToast()

const replacementId = ref<string | null>(null)
const busy = ref(false)

const targets = computed(() => props.categories.filter((c) => c.id !== props.category?.id))

watch(visible, (open) => {
  if (open) replacementId.value = null
})

async function remove() {
  const category = props.category
  if (!category) return
  busy.value = true
  try {
    await deleteCategory(category.id, replacementId.value)
    toast.success(t('common.done'))
    visible.value = false
    emit('done')
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('resources.categories.deleteTitle')" class="resource-dialog">
    <form class="dialog-form" @submit.prevent="remove">
      <p>{{ t('resources.categories.deleteText', { name: category?.name }) }}</p>
      <div class="field">
        <label id="category-replacement-label" for="category-replacement">
          {{ t('resources.categories.replacement') }}
        </label>
        <Select
          id="category-replacement"
          v-model="replacementId"
          :options="targets"
          option-label="name"
          option-value="id"
          aria-labelledby="category-replacement-label"
          :placeholder="t('resources.categories.noReplacement')"
          show-clear
          fluid
        />
      </div>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('common.delete')" severity="danger" :loading="busy" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
@use './resourceTab';
</style>
