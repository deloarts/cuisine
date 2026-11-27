<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import PermissionsPanel from '@/features/admin-settings/components/PermissionsPanel.vue'
import { usersApi } from '@/features/admin-settings/api/users'
import { useAppToast } from '@/core/composables/useAppToast'
import type { GroupResponse, Language, UserResponse } from '@/core/types/user'
import UserAvatar from '@/shared/components/UserAvatar.vue'

const props = defineProps<{ user: UserResponse | null; groups: GroupResponse[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [] }>()

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()

interface UserForm {
  full_name: string
  nickname: string
  show_nickname: boolean
  email: string
  password: string
  permissions: string[]
  group_ids: string[]
  language: Language
  is_active: boolean
}

const form = reactive<UserForm>({
  full_name: '',
  nickname: '',
  show_nickname: false,
  email: '',
  password: '',
  permissions: [],
  group_ids: [],
  language: 'enGB',
  is_active: true,
})
const saving = ref(false)
// The account as last returned by the backend. The avatar and the
// two-factor reset save at once, apart from the form, and update it.
const current = ref<UserResponse | null>(null)

watch(visible, (open) => {
  if (!open) return
  const u = props.user
  current.value = u
  Object.assign(form, {
    full_name: u?.full_name ?? '',
    nickname: u?.nickname ?? '',
    show_nickname: u?.show_nickname ?? false,
    email: u?.email ?? '',
    password: '',
    permissions: [...(u?.permissions ?? [])],
    group_ids: [...(u?.group_ids ?? [])],
    language: u?.language ?? 'enGB',
    is_active: u?.is_active ?? true,
  })
})

/** Every permission the selected groups grant, with the names of the groups granting it. */
const inherited = computed(() => {
  const byPermission = new Map<string, string[]>()
  for (const id of form.group_ids) {
    const group = props.groups.find((g) => g.id === id)
    if (!group) continue
    for (const perm of group.permissions) byPermission.set(perm, [...(byPermission.get(perm) ?? []), group.name])
  }
  return byPermission
})

const languages = [
  { value: 'deAT', label: 'Deutsch' },
  { value: 'enGB', label: 'English' },
]

const busy = ref(false)
const avatarInput = useTemplateRef<HTMLInputElement>('avatar-input')

/** Runs an immediate change, keeps the returned account and refreshes the list behind the dialog. */
async function applyNow(action: () => Promise<UserResponse>) {
  busy.value = true
  try {
    current.value = await action()
    emit('saved')
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function changeAvatar(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  const id = current.value?.id
  input.value = ''
  if (!file || !id) return
  await applyNow(() => usersApi.uploadAvatar(id, file))
}

function clearAvatar() {
  const id = current.value?.id
  if (id) void applyNow(() => usersApi.removeAvatar(id))
}

function resetTotp() {
  const u = current.value
  if (!u) return
  confirm.require({
    message: t('users.resetTotpConfirm', { name: u.full_name }),
    header: t('common.confirm'),
    acceptProps: { label: t('common.yes'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void applyNow(() => usersApi.resetTotp(u.id)),
  })
}

async function save() {
  saving.value = true
  try {
    if (props.user) {
      await usersApi.update(props.user.id, {
        full_name: form.full_name,
        // An empty string clears the nickname.
        nickname: form.nickname,
        show_nickname: form.show_nickname,
        email: form.email,
        // An empty field keeps the current password.
        password: form.password || null,
        permissions: props.user.is_systemuser ? null : form.permissions,
        group_ids: form.group_ids,
        language: form.language,
        is_active: props.user.is_systemuser ? null : form.is_active,
      })
    } else {
      await usersApi.create({ ...form })
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
    :header="user ? t('users.edit') : t('users.create')"
    :style="{ width: 'var(--dialog-width-lg)' }"
  >
    <form id="user-form" class="form-layout" @submit.prevent="save">
      <div class="form-grid">
        <div v-if="current" class="wide avatar-row">
          <UserAvatar class="avatar-preview" :name="current.full_name" :avatar-id="current.avatar_id" />
          <div class="avatar-actions">
            <span id="user-avatar-label" class="field-label">{{ t('users.avatar') }}</span>
            <div class="avatar-buttons">
              <Button
                type="button"
                :label="t('users.avatarUpload')"
                icon="mdi mdi-upload"
                severity="secondary"
                text
                aria-describedby="user-avatar-label"
                :disabled="busy"
                data-testid="user-avatar-upload"
                @click="avatarInput?.click()"
              />
              <input
                ref="avatar-input"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                hidden
                tabindex="-1"
                aria-hidden="true"
                data-testid="user-avatar-input"
                @change="changeAvatar"
              />
              <Button
                v-if="current.avatar_id"
                type="button"
                :label="t('users.avatarRemove')"
                icon="mdi mdi-delete-outline"
                severity="secondary"
                text
                :disabled="busy"
                data-testid="user-avatar-remove"
                @click="clearAvatar"
              />
            </div>
            <small class="field-hint">{{ t('users.avatarHint') }}</small>
          </div>
        </div>
        <div class="field">
          <label for="user-fullname">{{ t('users.fullName') }}</label>
          <InputText id="user-fullname" v-model="form.full_name" />
        </div>
        <div class="field">
          <label for="user-nickname">{{ t('users.nickname') }}</label>
          <InputText id="user-nickname" v-model="form.nickname" maxlength="64" />
        </div>
        <div class="field toggle-field wide">
          <ToggleSwitch v-model="form.show_nickname" input-id="user-show-nickname" />
          <label for="user-show-nickname">{{ t('users.showNickname') }}</label>
        </div>
        <div class="field">
          <label for="user-email">{{ t('users.email') }}</label>
          <InputText id="user-email" v-model="form.email" type="email" />
        </div>
        <div class="field">
          <label for="user-password">{{ t('users.password') }}</label>
          <Password v-model="form.password" input-id="user-password" toggle-mask autocomplete="new-password" />
          <small v-if="user" class="field-hint">{{ t('users.passwordKeep') }}</small>
        </div>
        <div class="field">
          <label id="user-language-label" for="user-language">{{ t('users.language') }}</label>
          <Select
            id="user-language"
            v-model="form.language"
            :options="languages"
            option-label="label"
            option-value="value"
            aria-labelledby="user-language-label"
          />
        </div>
        <div class="field toggle-field">
          <ToggleSwitch v-model="form.is_active" input-id="user-active" :disabled="user?.is_systemuser" />
          <label for="user-active">{{ t('users.active') }}</label>
        </div>
        <div v-if="current" class="field wide two-factor" data-testid="user-two-factor">
          <span class="field-label">{{ t('users.twoFactor') }}</span>
          <div class="two-factor-row">
            <small class="field-hint">
              <template v-if="!current.totp_enabled">{{ t('users.twoFactorOff') }}</template>
              <template v-else-if="current.is_systemuser">{{ t('users.twoFactorSystem') }}</template>
              <template v-else>{{ t('users.twoFactorOn') }}</template>
            </small>
            <Button
              v-if="current.totp_enabled && !current.is_systemuser"
              type="button"
              :label="t('users.resetTotp')"
              icon="mdi mdi-shield-off-outline"
              severity="danger"
              outlined
              size="small"
              :disabled="busy"
              data-testid="user-reset-totp"
              @click="resetTotp"
            />
          </div>
        </div>
        <div class="field wide">
          <label for="user-groups">{{ t('users.groups') }}</label>
          <MultiSelect
            v-model="form.group_ids"
            input-id="user-groups"
            :options="groups"
            option-label="name"
            option-value="id"
            display="chip"
            :placeholder="t('common.none')"
          />
        </div>
      </div>
      <!-- Permissions get their own column, since the list is long. -->
      <PermissionsPanel
        v-model:permissions="form.permissions"
        :caption="t('users.permissions')"
        id-prefix="user-perm"
        :inherited="inherited"
        :replacement="user?.is_systemuser ? t('users.systemHint') : null"
      />
    </form>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="visible = false" />
      <Button
        type="submit"
        form="user-form"
        :label="t('common.save')"
        :loading="saving"
        :disabled="!form.full_name || !form.email || (!user && !form.password)"
      />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
// Fields left, permissions right; the panel takes the fields' height.
.form-layout {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: var(--space-5);
}

.form-grid {
  align-content: start;
}

@media (max-width: $bp-lg) {
  .form-layout {
    grid-template-columns: 1fr;
  }
}

.wide {
  grid-column: 1 / -1;
}

.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
  align-self: end;

  > :first-child {
    flex-shrink: 0;
  }
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.avatar-preview {
  --avatar-size: 4rem;

  flex-shrink: 0;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.avatar-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.field-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.two-factor-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
</style>
