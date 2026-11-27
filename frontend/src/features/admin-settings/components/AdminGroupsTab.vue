<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'
import { useConfirm } from 'openvue/useconfirm'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import GroupDialog from '@/features/admin-settings/components/GroupDialog.vue'
import { groupsApi, usersApi } from '@/features/admin-settings/api/users'
import { useAppToast } from '@/core/composables/useAppToast'
import type { DirectoryUserResponse, GroupResponse } from '@/core/types/user'

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()

const groups = ref<GroupResponse[]>([])
const users = ref<DirectoryUserResponse[]>([])
const loading = ref(false)
const dialog = ref(false)
const editing = ref<GroupResponse | null>(null)

const table = useResourceTable('groups', { q: 'string', permission: 'string' })
const permissionOptions = computed(() => [...new Set(groups.value.flatMap((g) => g.permissions))].sort())
const filtered = computed(() =>
  groups.value.filter(
    (g) =>
      matchesText(table.filters.q, g.name, g.description) &&
      (!table.filters.permission || g.permissions.includes(table.filters.permission)),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'description', header: t('common.description') },
  { field: 'permissions', header: t('groups.permissions'), filter: true, sortField: (g: GroupResponse) => g.permissions.join(', ') },
  { field: 'member_ids', header: t('groups.members'), sortField: (g: GroupResponse) => memberNames(g) },
])

async function load() {
  loading.value = true
  try {
    ;[groups.value, users.value] = await Promise.all([
      groupsApi.list(),
      usersApi.directory(),
    ])
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

function open(group: GroupResponse | null) {
  editing.value = group
  dialog.value = true
}

function memberNames(group: GroupResponse): string {
  return group.member_ids
    .map((id) => users.value.find((u) => u.id === id)?.display_name)
    .filter(Boolean)
    .join(', ')
}

function remove(group: GroupResponse) {
  confirm.require({
    message: t('groups.deleteConfirm', { name: group.name }),
    header: t('common.confirm'),
    acceptProps: { label: t('common.delete'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void (async () => {
        try {
          await groupsApi.remove(group.id)
          await load()
        } catch (err) {
          toast.error(err)
        }
      })()
    },
  })
}

const groupMenu = (group: GroupResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(group) },
  { label: t('common.delete'), icon: 'mdi mdi-delete-outline', command: () => remove(group) },
]

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab">
    <div class="section-head">
      <p class="hint">{{ t('groups.hint') }}</p>
      <div class="section-actions">
        <Button :label="t('groups.create')" icon="mdi mdi-plus" @click="open(null)" />
      </div>
    </div>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :menu="groupMenu"
      clickable
      @row-click="open"
      :empty-message="t('groups.none')"
      empty-icon="mdi mdi-account-group-outline"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-permissions>
        <Select
          v-model="table.filters.permission"
          :options="permissionOptions"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('groups.permissions') })"
          show-clear
          filter
          size="small"
          fluid
        />
      </template>
      <template #body-description="{ data }">{{ data.description }}</template>
      <template #body-permissions="{ data }">
        <Tag v-for="p in data.permissions" :key="p" :value="p" severity="secondary" class="tag" />
      </template>
      <template #body-member_ids="{ data }">{{ memberNames(data) }}</template>
      <template #phone="{ data }">{{ memberNames(data) }}</template>
    </ResourceTable>
    <GroupDialog v-model:visible="dialog" :group="editing" :users="users" @saved="load" />
  </section>
</template>

<style scoped lang="scss">
.tag {
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
