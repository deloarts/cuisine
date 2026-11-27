<script setup lang="ts">
/**
 * Who lives in which household. Administrators see the membership only; the
 * households' meal plans and shopping lists stay private to their members.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import type { Schemas } from '@/core/api/generated'
import { adminApi } from '@/features/admin-settings/api/admin'
import { useAppToast } from '@/core/composables/useAppToast'

type Membership = Schemas['HouseholdMembershipResponse']

const { t } = useI18n()
const toast = useAppToast()

const households = ref<Membership[]>([])
const loading = ref(false)

const table = useResourceTable('households', { household: 'string', member: 'string' })
const filtered = computed(() =>
  households.value.filter(
    (h) =>
      matchesText(table.filters.household, h.name) &&
      (!table.filters.member || h.members.some((m) => matchesText(table.filters.member, m.display_name))),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'members', header: t('adminArea.households.members'), filter: true, sortField: (h: Membership) => names(h) },
  {
    field: 'count',
    header: t('adminArea.households.count'),
    class: 'numeric',
    sortField: (h: Membership) => h.members.length,
  },
])

function names(h: Membership): string {
  return h.members.map((m) => m.display_name).join(', ')
}

async function load() {
  loading.value = true
  try {
    households.value = await adminApi.households()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab">
    <h2 class="panel-title">{{ t('adminArea.households.title') }}</h2>
    <p class="hint">{{ t('adminArea.households.hint') }}</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :empty-message="t('adminArea.households.none')"
      empty-icon="mdi mdi-home-heart"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.household"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-members>
        <InputText
          v-model="table.filters.member"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('adminArea.households.members') })"
          size="small"
          fluid
        />
      </template>
      <template #body-members="{ data }">
        <Tag v-for="m in data.members" :key="m.id" :value="m.display_name" severity="secondary" class="member" />
      </template>
      <template #body-count="{ data }">{{ data.members.length }}</template>
      <template #phone="{ data }">{{ names(data) }}</template>
    </ResourceTable>
  </section>
</template>

<style scoped lang="scss">
.member {
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
