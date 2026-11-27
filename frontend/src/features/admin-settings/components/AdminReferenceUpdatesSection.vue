<script setup lang="ts">
/**
 * Reference data updates: the fields of the shipped catalogue (units,
 * categories, tags, families, ingredients, equipment) that were changed
 * here while the seed has a newer value. The start-up merge leaves such
 * fields alone; this view shows both values and accepts the seed's value
 * field by field. Allergens and diet markers come first and are marked,
 * since they drive the allergy and diet warnings, so the table keeps the
 * backend's order until a column header is clicked.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import {
  filterUpdates,
  isSafetyField,
  REFERENCE_KINDS,
  rowKey,
  type ReferenceUpdate,
} from '@/features/admin-settings/referenceUpdates'
import { useCatalogueFieldLabels } from '@/features/admin-settings/useCatalogueFieldLabels'
import { adminApi } from '@/features/admin-settings/api/admin'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const toast = useAppToast()
const { kindLabel, fieldLabel, valueText } = useCatalogueFieldLabels()
const currentUser = useCurrentUserStore()

const rows = ref<ReferenceUpdate[]>([])
const loading = ref(false)
const busy = ref<string | null>(null)
const canAccept = computed(() => currentUser.hasPermission(Permission.WRITE_SETTINGS))

const table = useResourceTable('referenceUpdates', { refQ: 'string', refKind: 'string' })
// The rows carry no id of their own, so the table keys them by kind, key and field.
const filtered = computed(() =>
  filterUpdates(rows.value, table.filters.refKind, (...texts) => matchesText(table.filters.refQ, ...texts)).map(
    (r) => ({ ...r, id: rowKey(r) }),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'kind', header: t('referenceUpdates.kind'), filter: true, sortField: (r: ReferenceUpdate) => kindLabel(r.kind) },
  { field: 'field', header: t('referenceUpdates.field'), sortField: (r: ReferenceUpdate) => fieldLabel(r.field) },
  { field: 'current', header: t('referenceUpdates.current'), sortField: (r: ReferenceUpdate) => show(r, r.current) },
  { field: 'seed', header: t('referenceUpdates.seed'), sortField: (r: ReferenceUpdate) => show(r, r.seed) },
])
const kindOptions = computed(() => REFERENCE_KINDS.map((k) => ({ value: k, label: t(`referenceUpdates.kinds.${k}`) })))

function show(row: ReferenceUpdate, value: unknown): string {
  return valueText(row.field, value)
}

async function load() {
  loading.value = true
  try {
    rows.value = await adminApi.referenceUpdates()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function accept(row: ReferenceUpdate) {
  const id = rowKey(row)
  busy.value = id
  try {
    await adminApi.acceptReferenceUpdate({ kind: row.kind, key: row.key, field: row.field })
    rows.value = rows.value.filter((r) => rowKey(r) !== id)
    toast.success(t('referenceUpdates.accepted', { name: row.name }))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

const updateMenu = (row: ReferenceUpdate & { id: string }): MenuItem[] =>
  canAccept.value
    ? [
        {
          label: t('referenceUpdates.accept', { name: row.name, field: fieldLabel(row.field) }),
          icon: 'mdi mdi-check',
          disabled: busy.value === row.id,
          command: () => void accept(row),
        },
      ]
    : []

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('referenceUpdates.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <p class="hint">{{ t('referenceUpdates.hint') }}</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :default-sort="null"
      :menu="updateMenu"
      :empty-message="t('referenceUpdates.none')"
      empty-icon="mdi mdi-check-all"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.refQ"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-kind>
        <Select
          v-model="table.filters.refKind"
          :options="kindOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('referenceUpdates.kind') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <span class="name">
          <Tag v-if="isSafetyField(data.field)" :value="t('referenceUpdates.safety')" severity="danger" />
          {{ data.name }}
        </span>
      </template>
      <template #body-kind="{ data }">{{ kindLabel(data.kind) }}</template>
      <template #body-field="{ data }">{{ fieldLabel(data.field) }}</template>
      <template #body-current="{ data }">{{ show(data, data.current) }}</template>
      <template #body-seed="{ data }"><strong>{{ show(data, data.seed) }}</strong></template>
      <template #phone="{ data }">
        {{ kindLabel(data.kind) }} · {{ fieldLabel(data.field) }}: {{ show(data, data.current) }} → {{ show(data, data.seed) }}
      </template>
    </ResourceTable>
  </section>
</template>

<style scoped lang="scss">
.name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
</style>
