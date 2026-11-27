<script setup lang="ts">
/**
 * Creates a shopping list or changes its name and the people it is shared
 * with. Only the owner shares; members see the list and edit its items.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UserPicker from '@/shared/cookbook/UserPicker.vue'

const props = defineProps<{ name?: string; memberIds?: string[]; saving: boolean; isNew: boolean }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ submit: [value: { name: string; member_ids: string[] }] }>()

const { t } = useI18n()
const listName = ref('')
const members = ref<string[]>([])

function onShow() {
  listName.value = props.name ?? ''
  members.value = [...(props.memberIds ?? [])]
}

function submit() {
  if (!listName.value.trim()) return
  emit('submit', { name: listName.value.trim(), member_ids: members.value })
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="isNew ? t('shopping.newList') : t('shopping.editList')"
    class="list-dialog"
    @show="onShow"
  >
    <form class="list-form" @submit.prevent="submit">
      <div class="field">
        <label for="list-name">{{ t('common.name') }}</label>
        <InputText id="list-name" v-model="listName" required fluid :placeholder="t('shopping.namePlaceholder')" />
      </div>
      <div class="field">
        <label id="list-members-label" for="list-members">{{ t('shopping.sharedWith') }}</label>
        <UserPicker v-model="members" input-id="list-members" labelledby="list-members-label" />
        <small class="field-hint">{{ t('shopping.shareHint') }}</small>
      </div>
      <div class="list-actions">
        <Button type="button" :label="t('common.cancel')" text @click="visible = false" />
        <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.list-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.list-form {
  display: grid;
  gap: var(--space-3);
}

.list-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
