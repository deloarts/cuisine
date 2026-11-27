<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import PermissionsPanel from '@/features/admin-settings/components/PermissionsPanel.vue'
import { groupsApi } from '@/features/admin-settings/api/users'
import { useAppToast } from '@/core/composables/useAppToast'
import type { DirectoryUserResponse, GroupResponse } from '@/core/types/user'
import UserPicker from '@/shared/cookbook/UserPicker.vue'

const props = defineProps<{ group: GroupResponse | null; users: DirectoryUserResponse[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [] }>()

const { t } = useI18n()
const toast = useAppToast()

interface GroupForm {
  name: string
  description: string
  permissions: string[]
  member_ids: string[]
}

const form = reactive<GroupForm>({ name: '', description: '', permissions: [], member_ids: [] })
const saving = ref(false)

watch(visible, (open) => {
  if (!open) return
  Object.assign(form, {
    name: props.group?.name ?? '',
    description: props.group?.description ?? '',
    permissions: [...(props.group?.permissions ?? [])],
    member_ids: [...(props.group?.member_ids ?? [])],
  })
})

async function save() {
  saving.value = true
  try {
    if (props.group) {
      await groupsApi.update(props.group.id, { ...form })
    } else {
      await groupsApi.create({ ...form })
    }
    toast.success(t('common.saved'))
    visible.value = false
    emit('saved')
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
    :header="group ? t('groups.edit') : t('groups.create')"
    :style="{ width: 'var(--dialog-width-lg)' }"
  >
    <form id="group-form" class="form-layout" @submit.prevent="save">
      <div class="group-fields">
        <div class="field">
          <label for="group-name">{{ t('common.name') }}</label>
          <InputText id="group-name" v-model="form.name" maxlength="64" />
        </div>
        <div class="field">
          <label for="group-description">{{ t('common.description') }}</label>
          <Textarea id="group-description" v-model="form.description" rows="2" auto-resize />
        </div>
        <div class="field">
          <label id="group-members-label" for="group-members">{{ t('groups.members') }}</label>
          <UserPicker
            v-model="form.member_ids"
            input-id="group-members"
            labelledby="group-members-label"
            :people="users"
            :placeholder="t('common.none')"
          />
        </div>
      </div>
      <!-- Permissions get their own column, as in the user dialog. -->
      <PermissionsPanel v-model:permissions="form.permissions" :caption="t('groups.permissions')" id-prefix="group-perm" />
    </form>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="visible = false" />
      <Button type="submit" form="group-form" :label="t('common.save')" :loading="saving" :disabled="!form.name" />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
// Fields left, permissions right, in equal halves, since a group has few
// fields and the permissions are what it is about. The panel takes the
// fields' height, but at least enough for a few sections.
.form-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-5);
  min-height: 28rem;
}

.group-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

@media (max-width: $bp-lg) {
  .form-layout {
    grid-template-columns: 1fr;
    min-height: 0;
  }
}
</style>
