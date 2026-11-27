<script setup lang="ts">
/**
 * Who accepted the current privacy statement and who is still asked, with
 * the version each person accepted last. Service accounts are never asked,
 * so they do not appear.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import {
  acknowledgementCounts,
  acknowledgementRows,
  type AcknowledgementOverview,
  type AcknowledgementRow,
  type AcknowledgementStatus,
} from '@/features/admin-settings/privacyAcknowledgements'
import { adminLegalApi } from '@/features/admin-settings/api/legal'
import { useAppToast } from '@/core/composables/useAppToast'
import { formatDateTime } from '@/core/utils/dates'

const { t } = useI18n()
const toast = useAppToast()

const overview = ref<AcknowledgementOverview | null>(null)
const loading = ref(false)

const table = useResourceTable('privacyAcknowledgements', { ackQ: 'string', ackStatus: 'string' })
const rows = computed(() => (overview.value ? acknowledgementRows(overview.value) : []))
const filtered = computed(() =>
  rows.value.filter(
    (r) => (!table.filters.ackStatus || r.status === table.filters.ackStatus) && matchesText(table.filters.ackQ, r.name),
  ),
)
const counts = computed(() => (overview.value ? acknowledgementCounts(overview.value) : { done: 0, total: 0 }))
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('privacyAcknowledgements.person'), filter: true },
  {
    field: 'status',
    header: t('privacyAcknowledgements.status'),
    filter: true,
    sortField: (r: AcknowledgementRow) => t(`privacyAcknowledgements.statuses.${r.status}`),
  },
  { field: 'version', header: t('privacyAcknowledgements.version') },
  { field: 'acknowledgedAt', header: t('privacyAcknowledgements.when') },
])
const statuses: AcknowledgementStatus[] = ['current', 'outdated', 'never']
const statusOptions = computed(() => statuses.map((s) => ({ value: s, label: t(`privacyAcknowledgements.statuses.${s}`) })))
const severity = (s: AcknowledgementStatus) => (s === 'current' ? 'success' : s === 'outdated' ? 'warn' : 'secondary')

async function load() {
  loading.value = true
  try {
    overview.value = await adminLegalApi.privacyAcknowledgements()
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
      <h2 class="panel-title">{{ t('privacyAcknowledgements.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <p v-if="overview && overview.current_version === null" class="hint">{{ t('privacyAcknowledgements.noStatement') }}</p>
    <p v-else-if="overview" class="hint">
      {{ t('privacyAcknowledgements.summary', { version: overview.current_version, done: counts.done, total: counts.total }) }}
    </p>
    <p v-else class="hint">&nbsp;</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :empty-message="t('privacyAcknowledgements.none')"
      empty-icon="mdi mdi-account-check-outline"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.ackQ"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('privacyAcknowledgements.person') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-status>
        <Select
          v-model="table.filters.ackStatus"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('privacyAcknowledgements.status') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-status="{ data }">
        <Tag :value="t(`privacyAcknowledgements.statuses.${data.status}`)" :severity="severity(data.status)" />
      </template>
      <template #body-version="{ data }">{{ data.version }}</template>
      <template #body-acknowledgedAt="{ data }">{{ formatDateTime(data.acknowledgedAt) }}</template>
      <template #phone="{ data }">
        {{ t(`privacyAcknowledgements.statuses.${data.status}`) }}{{ data.version ? ` · ${t('privacyAcknowledgements.version')} ${data.version}` : '' }}
      </template>
    </ResourceTable>
  </section>
</template>
