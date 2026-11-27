<script setup lang="ts">
/**
 * The security log on the shared management table, newest first and paged
 * on the server. With `scope` "all" it lists the whole instance and filters
 * by person (kept in the URL as `logUser`); with "own" it lists the signed-in
 * user's own events for the account page.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import PersonSelect from '@/shared/components/PersonSelect.vue'
import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { listOwnSecurityEvents, listSecurityEvents } from '@/shared/api/activityLogs'
import { listDirectory } from '@/shared/api/directory'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import type { SecurityEventResponse } from '@/core/types/user'
import { formatDateTime } from '@/core/utils/dates'

const props = withDefaults(defineProps<{ scope: 'own' | 'all'; fill?: boolean }>(), { fill: false })

const { t, te, locale } = useI18n()
const toast = useAppToast()

const all = props.scope === 'all'
const table = useResourceTable(all ? 'securityLog' : 'ownSecurityLog', { logUser: 'string' }, () => load())
const events = ref<SecurityEventResponse[]>([])
const total = ref(0)
const loading = ref(false)
const people = ref<Schemas['DirectoryUserResponse'][]>([])

const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'created', header: t('securityLog.time') },
  { field: 'event_type', header: t('securityLog.event'), phone: true },
  { field: 'actor_name', header: t('securityLog.actor'), filter: all },
  { field: 'target_name', header: t('securityLog.target') },
  { field: 'client_ip', header: t('securityLog.address') },
  { field: 'detail', header: t('securityLog.details') },
])

function eventLabel(type: string): string {
  const key = `securityLog.events.${type}`
  return te(key) ? t(key) : type
}

function detail(event: SecurityEventResponse): string {
  const entries = Object.entries(event.detail ?? {})
  return entries.map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`).join(', ')
}

let sequence = 0

async function load() {
  const current = ++sequence
  loading.value = true
  const query = { limit: table.rows.value, offset: table.first.value }
  try {
    const page = all
      ? await listSecurityEvents({ ...query, user_id: table.filters.logUser })
      : await listOwnSecurityEvents(query)
    if (current !== sequence) return
    events.value = page.items
    total.value = page.total
  } catch (err) {
    toast.error(err)
  } finally {
    if (current === sequence) loading.value = false
  }
}

onMounted(async () => {
  void load()
  if (!all) return
  try {
    people.value = await listDirectory()
  } catch {
    people.value = []
  }
})
</script>

<template>
  <ResourceTable
    :state="table"
    :value="events"
    :columns="columns"
    :total="total"
    :loading="loading"
    :fill="fill"
    empty-icon="mdi mdi-shield-search"
  >
    <template #filter-actor_name>
      <PersonSelect
        v-model="table.filters.logUser"
        :people="people"
        :placeholder="t('tableFilters.all')"
        :aria-label="t('tableFilters.filterBy', { column: t('securityLog.actor') })"
        show-clear
        filter
        size="small"
        fluid
      />
    </template>
    <template #body-created="{ data }">{{ formatDateTime(data.created, locale as AppLocale) }}</template>
    <template #body-event_type="{ data }">
      <Tag :value="eventLabel(data.event_type)" :severity="data.outcome === 'failure' ? 'danger' : 'secondary'" />
    </template>
    <template #body-actor_name="{ data }">{{ data.actor_name ?? '–' }}</template>
    <template #body-target_name="{ data }">{{ data.target_name ?? '–' }}</template>
    <template #body-client_ip="{ data }">{{ data.client_ip ?? '–' }}</template>
    <template #body-detail="{ data }">
      <span class="detail">{{ detail(data) }}</span>
    </template>
    <template #phone="{ data }">
      {{ formatDateTime(data.created, locale as AppLocale) }}
      <template v-if="data.actor_name"> · {{ data.actor_name }}</template>
      <template v-if="data.client_ip"> · {{ data.client_ip }}</template>
    </template>
  </ResourceTable>
</template>

<style scoped lang="scss">
.detail {
  font-size: var(--font-size-sm);
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
</style>
