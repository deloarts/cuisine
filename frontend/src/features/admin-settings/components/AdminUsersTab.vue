<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'
import { useConfirm } from 'openvue/useconfirm'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import UserDeletionDialog from '@/features/admin-settings/components/UserDeletionDialog.vue'
import UserDialog from '@/features/admin-settings/components/UserDialog.vue'
import { groupsApi, usersApi } from '@/features/admin-settings/api/users'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { GroupResponse, UserResponse } from '@/core/types/user'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const currentUser = useCurrentUserStore()

const users = ref<UserResponse[]>([])
const groups = ref<GroupResponse[]>([])
const loading = ref(false)
const dialog = ref(false)
const editing = ref<UserResponse | null>(null)
const deleting = ref<UserResponse | null>(null)
const deletionDialog = ref(false)

const table = useResourceTable('users', { q: 'string', group: 'string', status: 'string' })
const filtered = computed(() =>
  users.value.filter(
    (u) =>
      matchesText(table.filters.q, u.full_name, u.email) &&
      (!table.filters.group || u.group_ids.includes(table.filters.group)) &&
      (!table.filters.status || (table.filters.status === 'active') === u.is_active),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'full_name', header: t('users.fullName'), filter: true },
  { field: 'email', header: t('users.email') },
  {
    field: 'group_ids',
    header: t('users.groups'),
    filter: true,
    sortField: (u: UserResponse) => u.group_ids.map(groupName).sort().join(', '),
  },
  { field: 'is_active', header: t('users.status'), filter: true },
  { field: 'last_logged_in', header: t('users.lastLogin') },
])
const statusOptions = computed(() => [
  { value: 'active', label: t('users.active') },
  { value: 'inactive', label: t('users.inactive') },
])

async function load() {
  loading.value = true
  try {
    ;[users.value, groups.value] = await Promise.all([usersApi.list(), groupsApi.list()])
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function groupName(id: string): string {
  return groups.value.find((g) => g.id === id)?.name ?? '?'
}

function open(user: UserResponse | null) {
  editing.value = user
  dialog.value = true
}

function ask(message: string, action: () => Promise<unknown>, danger = false) {
  confirm.require({
    message,
    header: t('common.confirm'),
    acceptProps: { label: t('common.yes'), severity: danger ? 'danger' : undefined },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void (async () => {
        try {
          await action()
          toast.success(t('common.done'))
          await load()
        } catch (err) {
          toast.error(err)
        }
      })()
    },
  })
}

const resetTotp = (u: UserResponse) =>
  ask(t('users.resetTotpConfirm', { name: u.full_name }), () =>
    usersApi.resetTotp(u.id),
  )
const forceLogout = (u: UserResponse) =>
  ask(t('users.logoutConfirm', { name: u.full_name }), () =>
    usersApi.logout(u.id),
  )
function remove(u: UserResponse) {
  deleting.value = u
  deletionDialog.value = true
}

const userMenu = (u: UserResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(u) },
  {
    label: t('users.resetTotp'),
    icon: 'mdi mdi-shield-off-outline',
    visible: u.totp_enabled && !u.is_systemuser,
    command: () => resetTotp(u),
  },
  { label: t('users.logout'), icon: 'mdi mdi-logout', command: () => forceLogout(u) },
  {
    label: t('common.delete'),
    icon: 'mdi mdi-delete-outline',
    visible: !u.is_systemuser && u.id !== currentUser.user?.id,
    command: () => remove(u),
  },
]

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab">
    <div class="section-head">
      <div class="section-actions">
        <Button :label="t('users.create')" icon="mdi mdi-account-plus" @click="open(null)" />
      </div>
    </div>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :menu="userMenu"
      clickable
      empty-icon="mdi mdi-account-multiple-outline"
      @row-click="open"
    >
      <template #filter-full_name>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('users.fullName') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-group_ids>
        <Select
          v-model="table.filters.group"
          :options="groups"
          option-label="name"
          option-value="id"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('users.groups') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #filter-is_active>
        <Select
          v-model="table.filters.status"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('users.status') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-full_name="{ data }">{{ data.full_name }}</template>
      <template #body-email="{ data }">{{ data.email || '–' }}</template>
      <template #body-group_ids="{ data }">
        <Tag v-for="g in data.group_ids" :key="g" :value="groupName(g)" severity="secondary" class="tag" />
      </template>
      <template #body-is_active="{ data }">
        <Tag v-if="data.is_systemuser" :value="t('users.system')" severity="warn" class="tag" />
        <Tag
          :value="data.is_active ? t('users.active') : t('users.inactive')"
          :severity="data.is_active ? 'success' : 'danger'"
          class="tag"
        />
        <Tag v-if="data.totp_enabled" value="2FA" severity="info" class="tag" />
      </template>
      <template #body-last_logged_in="{ data }">{{ formatDateTime(data.last_logged_in, locale as AppLocale) }}</template>
      <template #phone="{ data }">
        {{ data.email }} · {{ data.is_active ? t('users.active') : t('users.inactive') }}
      </template>
    </ResourceTable>
    <UserDialog v-model:visible="dialog" :user="editing" :groups="groups" @saved="load" />
    <UserDeletionDialog v-model:visible="deletionDialog" :user="deleting" :users="users" @deleted="load" />
  </section>
</template>

<style scoped lang="scss">
.tag {
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
