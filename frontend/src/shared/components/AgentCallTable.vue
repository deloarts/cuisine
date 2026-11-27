<script setup lang="ts">
/**
 * The agent call log on the shared management table: every MCP tool call an
 * agent made with someone's token, newest first, paged on the server. With
 * `scope` "all" admins see everyone's calls, can filter by person (kept in
 * the URL as `callsUser`) and see the person's name; with "own" each user
 * sees their own.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import PersonSelect from '@/shared/components/PersonSelect.vue'
import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { listAgentCalls, listOwnAgentCalls } from '@/shared/api/activityLogs'
import { listDirectory } from '@/shared/api/directory'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'

type AgentCall = Schemas['AgentCallResponse']

const props = withDefaults(defineProps<{ scope: 'own' | 'all'; fill?: boolean }>(), { fill: false })

const { t, locale } = useI18n()
const toast = useAppToast()

const all = props.scope === 'all'
const table = useResourceTable(all ? 'agentCalls' : 'ownAgentCalls', { callsUser: 'string' }, () => load())
const calls = ref<AgentCall[]>([])
const total = ref(0)
const loading = ref(false)
const people = ref<Schemas['DirectoryUserResponse'][]>([])

const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'called_at', header: t('agents.when') },
  ...(all ? [{ field: 'user_name', header: t('agents.person'), filter: true }] : []),
  { field: 'tool', header: t('agents.tool'), phone: true },
  { field: 'token_name', header: t('agents.token') },
  { field: 'outcome', header: t('agents.outcome') },
  { field: 'duration_ms', header: t('agents.duration') },
])

let sequence = 0

async function load() {
  const current = ++sequence
  loading.value = true
  const query = { limit: table.rows.value, offset: table.first.value }
  try {
    const page = all
      ? await listAgentCalls({ ...query, user_id: table.filters.callsUser })
      : await listOwnAgentCalls(query)
    if (current !== sequence) return
    calls.value = page.items
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
    :value="calls"
    :columns="columns"
    :total="total"
    :loading="loading"
    :fill="fill"
    :empty-message="t('agents.noCalls')"
    empty-icon="mdi mdi-robot-outline"
  >
    <template #filter-user_name>
      <PersonSelect
        v-model="table.filters.callsUser"
        :people="people"
        :placeholder="t('tableFilters.all')"
        :aria-label="t('tableFilters.filterBy', { column: t('agents.person') })"
        show-clear
        filter
        size="small"
        fluid
      />
    </template>
    <template #body-called_at="{ data }">{{ formatDateTime(data.called_at, locale as AppLocale) }}</template>
    <template #body-user_name="{ data }">{{ data.user_name ?? '–' }}</template>
    <template #body-tool="{ data }"><code>{{ data.tool }}</code></template>
    <template #body-token_name="{ data }">
      {{ data.token_name }} <small class="text-muted">({{ data.token_kind }})</small>
    </template>
    <template #body-outcome="{ data }">
      <Tag :value="data.outcome" :severity="data.outcome === 'ok' ? 'success' : 'danger'" />
      <small v-if="data.error" class="text-muted"> {{ data.error }}</small>
    </template>
    <template #body-duration_ms="{ data }">{{ data.duration_ms }} ms</template>
    <template #phone="{ data }">
      {{ formatDateTime(data.called_at, locale as AppLocale) }}
      <template v-if="all && data.user_name"> · {{ data.user_name }}</template>
      · {{ data.outcome }}
    </template>
  </ResourceTable>
</template>
