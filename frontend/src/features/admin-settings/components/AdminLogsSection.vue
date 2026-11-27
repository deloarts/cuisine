<script setup lang="ts">
/**
 * The backend's recent warnings and errors, newest first, as the worker that
 * answers keeps them in memory (redacted, gone after a restart). Enough to
 * see what went wrong without a shell on the server. The table keeps the
 * backend's order until a column header is clicked.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import type { Schemas } from '@/core/api/generated'
import { adminApi } from '@/features/admin-settings/api/admin'
import { useAppToast } from '@/core/composables/useAppToast'
import { formatDateTime } from '@/core/utils/dates'

type LogEntry = Schemas['LogEntryResponse']

const LEVELS = ['WARNING', 'ERROR', 'CRITICAL'] as const
const LIMIT = 500

const { t } = useI18n()
const toast = useAppToast()

const entries = ref<LogEntry[]>([])
const loading = ref(false)

const table = useResourceTable('logs', { level: 'string', logger: 'string', q: 'string' }, () => load())
const filtered = computed(() =>
  entries.value.filter((e) => matchesText(table.filters.logger, e.logger) && matchesText(table.filters.q, e.message)),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'time', header: t('adminArea.logs.time') },
  { field: 'level', header: t('adminArea.logs.level'), filter: true },
  { field: 'logger', header: t('adminArea.logs.logger'), filter: true },
  { field: 'message', header: t('adminArea.logs.message'), filter: true, phone: true, wrap: true },
])

function severity(level: string): 'warn' | 'danger' | 'contrast' {
  if (level === 'CRITICAL') return 'contrast'
  return level === 'ERROR' ? 'danger' : 'warn'
}

async function load() {
  loading.value = true
  try {
    entries.value = await adminApi.logs({ level: table.filters.level || 'WARNING', limit: LIMIT })
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
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.logs.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <p class="hint">{{ t('adminArea.logs.hint') }}</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      data-key="time"
      :default-sort="null"
      :empty-message="t('adminArea.logs.none')"
      empty-icon="mdi mdi-check-circle-outline"
    >
      <template #filter-level>
        <Select
          v-model="table.filters.level"
          :options="[...LEVELS]"
          :placeholder="t('adminArea.logs.fromWarning')"
          :aria-label="t('tableFilters.filterBy', { column: t('adminArea.logs.level') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #filter-logger>
        <InputText
          v-model="table.filters.logger"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('adminArea.logs.logger') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-message>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('adminArea.logs.message') })"
          size="small"
          fluid
        />
      </template>
      <template #body-time="{ data }">{{ formatDateTime(data.time) }}</template>
      <template #body-level="{ data }"><Tag :value="data.level" :severity="severity(data.level)" /></template>
      <template #body-logger="{ data }"><code>{{ data.logger }}</code></template>
      <template #body-message="{ data }"><span class="message">{{ data.message }}</span></template>
      <template #phone="{ data }">{{ formatDateTime(data.time) }} · {{ data.level }}</template>
    </ResourceTable>
  </section>
</template>

<style scoped lang="scss">
.message {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
