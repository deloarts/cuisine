<script setup lang="ts">
/**
 * The catalogue file: exports the whole catalogue (units, tags, categories,
 * families, ingredients, equipment) as one JSON file, and imports such a
 * file from another Cuisine in two steps. The preview names the entries the
 * import creates and, for entries that already exist here, every field whose
 * value differs, with allergen and diet marker changes first. Nothing of an
 * existing entry changes unless its field is accepted here, one by one or a
 * whole entry at once through a row's menu; new entries are created active.
 * The differences keep the preview's order, safety fields first, until a
 * column header is clicked.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { downloadBlob, pickFiles } from '@/shared/composables/fileTransfer'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import {
  CATALOGUE_FILE_TYPES,
  exportCatalogue,
  importCatalogue,
  previewCatalogueImport,
  type CatalogueImportReport,
  type CataloguePreview,
} from '@/features/admin-settings/api/catalogueFile'
import {
  CATALOGUE_KINDS,
  catalogueFileName,
  differenceRows,
  entryKeys,
  filterRows,
  newEntries,
  toggleAll,
  type DifferenceRow,
} from '@/features/admin-settings/catalogueFile'
import { isSafetyField } from '@/features/admin-settings/referenceUpdates'
import { useCatalogueFieldLabels } from '@/features/admin-settings/useCatalogueFieldLabels'
import { useAppToast } from '@/core/composables/useAppToast'

const { t } = useI18n()
const toast = useAppToast()
const { kindLabel, fieldLabel, valueText } = useCatalogueFieldLabels()

const exporting = ref(false)
const busy = ref(false)
const file = ref<File | null>(null)
const preview = ref<CataloguePreview | null>(null)
const accepted = ref<string[]>([])
const report = ref<CatalogueImportReport | null>(null)

const rows = computed(() => (preview.value ? differenceRows(preview.value) : []))
const created = computed(() => (preview.value ? newEntries(preview.value) : []))
const newCount = computed(() => created.value.reduce((sum, group) => sum + group.names.length, 0))
const skipped = computed(() => preview.value?.kinds.filter((k) => k.skipped && k.total > 0) ?? [])

const table = useResourceTable('catalogueFile', { catQ: 'string', catKind: 'string' })
const filtered = computed(() =>
  filterRows(rows.value, table.filters.catKind, (...texts) => matchesText(table.filters.catQ, ...texts)),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'kind', header: t('referenceUpdates.kind'), filter: true, sortField: (r: DifferenceRow) => kindLabel(r.kind) },
  { field: 'field', header: t('referenceUpdates.field'), sortField: (r: DifferenceRow) => fieldLabel(r.field) },
  {
    field: 'current',
    header: t('referenceUpdates.current'),
    sortField: (r: DifferenceRow) => valueText(r.field, r.current),
  },
  {
    field: 'incoming',
    header: t('catalogueFile.incoming'),
    sortField: (r: DifferenceRow) => valueText(r.field, r.incoming),
  },
])
const kindOptions = computed(() => CATALOGUE_KINDS.map((k) => ({ value: k, label: kindLabel(k) })))

function isAccepted(row: DifferenceRow): boolean {
  return accepted.value.includes(row.id)
}

function setAccepted(row: DifferenceRow, value: boolean) {
  const others = accepted.value.filter((k) => k !== row.id)
  accepted.value = value ? [...others, row.id] : others
}

function toggleEntry(row: DifferenceRow) {
  accepted.value = toggleAll(accepted.value, entryKeys(rows.value, row.kind, row.sourceId))
}

function entryAccepted(row: DifferenceRow): boolean {
  return entryKeys(rows.value, row.kind, row.sourceId).every((k) => accepted.value.includes(k))
}

// One item takes over or drops every difference of the row's entry at once.
const differenceMenu = (row: DifferenceRow): MenuItem[] => {
  const all = entryAccepted(row)
  return [
    {
      label: t(all ? 'catalogueFile.acceptEntryNone' : 'catalogueFile.acceptEntry', { name: row.name }),
      icon: all ? 'mdi mdi-checkbox-multiple-blank-outline' : 'mdi mdi-checkbox-multiple-marked',
      command: () => toggleEntry(row),
    },
  ]
}

function acceptEverything(value: boolean) {
  accepted.value = value ? rows.value.map((r) => r.id) : []
}

async function exportFile() {
  exporting.value = true
  try {
    downloadBlob(await exportCatalogue(), catalogueFileName(new Date()))
  } catch (err) {
    toast.error(err)
  } finally {
    exporting.value = false
  }
}

async function pick() {
  const [picked] = await pickFiles(CATALOGUE_FILE_TYPES)
  if (!picked) return
  busy.value = true
  report.value = null
  try {
    preview.value = await previewCatalogueImport(picked)
    file.value = picked
    accepted.value = []
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function apply() {
  if (!file.value) return
  busy.value = true
  try {
    const result = await importCatalogue(file.value, accepted.value)
    report.value = result
    cancel()
    toast.success(t('catalogueFile.imported', { created: result.created.length, updated: result.updated.length }))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

function cancel() {
  file.value = null
  preview.value = null
  accepted.value = []
}
</script>

<template>
  <section class="settings-tab">
    <h2 class="panel-title">{{ t('catalogueFile.title') }}</h2>
    <p class="hint">{{ t('catalogueFile.hint') }}</p>

    <div class="actions">
      <Button
        :label="t('catalogueFile.export')"
        icon="mdi mdi-file-download-outline"
        :loading="exporting"
        @click="exportFile"
      />
      <Button
        v-if="!preview"
        :label="t('catalogueFile.import')"
        icon="mdi mdi-file-upload-outline"
        severity="secondary"
        outlined
        :loading="busy"
        @click="pick"
      />
    </div>

    <div v-if="preview" class="preview" role="group" :aria-label="t('catalogueFile.previewTitle', { name: file?.name ?? '' })">
      <h3 class="block-title">{{ t('catalogueFile.previewTitle', { name: file?.name ?? '' }) }}</h3>
      <ul class="summary">
        <li v-for="k in preview.kinds.filter((x) => x.total > 0)" :key="k.kind">
          <strong>{{ kindLabel(k.kind) }}:</strong>
          {{ t('catalogueFile.counts', { new: k.new, matched: k.matched, different: k.different }) }}
          <Tag v-if="k.skipped" :value="t('catalogueFile.skipped')" severity="secondary" />
        </li>
      </ul>
      <Message v-if="skipped.length" severity="info" :closable="false">
        {{ t('catalogueFile.skippedHint', { kinds: skipped.map((k) => kindLabel(k.kind)).join(', ') }) }}
      </Message>

      <div class="block">
        <h4 class="block-title">{{ t('catalogueFile.newTitle', { count: newCount }, newCount) }}</h4>
        <p v-if="!created.length" class="hint">{{ t('catalogueFile.noNew') }}</p>
        <p v-for="group in created" :key="group.kind" class="new-group">
          <strong>{{ kindLabel(group.kind) }} ({{ group.names.length }}):</strong> {{ group.names.join(', ') }}
        </p>
      </div>

      <div class="block">
        <div class="section-head">
          <h4 class="block-title">{{ t('catalogueFile.differencesTitle') }}</h4>
          <div class="section-actions">
            <Button
              :label="t('catalogueFile.acceptAll')"
              icon="mdi mdi-check-all"
              text
              :disabled="!rows.length"
              @click="acceptEverything(true)"
            />
            <Button
              :label="t('catalogueFile.acceptNone')"
              icon="mdi mdi-close"
              text
              :disabled="!accepted.length"
              @click="acceptEverything(false)"
            />
          </div>
        </div>
        <p class="hint">{{ t('catalogueFile.differencesHint') }}</p>
        <ResourceTable
          :state="table"
          :value="filtered"
          :columns="columns"
          :fill="false"
          :default-sort="null"
          :menu="differenceMenu"
          :empty-message="t('catalogueFile.noDifferences')"
          empty-icon="mdi mdi-check-all"
        >
          <template #filter-name>
            <InputText
              v-model="table.filters.catQ"
              :placeholder="t('tableFilters.search')"
              :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
              size="small"
              fluid
            />
          </template>
          <template #filter-kind>
            <Select
              v-model="table.filters.catKind"
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
              <Checkbox
                :model-value="isAccepted(data)"
                binary
                :input-id="`accept-${data.id}`"
                :aria-label="t('catalogueFile.acceptField', { name: data.name, field: fieldLabel(data.field) })"
                @update:model-value="(value: boolean) => setAccepted(data, value)"
              />
              <Tag v-if="isSafetyField(data.field)" :value="t('referenceUpdates.safety')" severity="danger" />
              {{ data.name }}
            </span>
          </template>
          <template #body-kind="{ data }">{{ kindLabel(data.kind) }}</template>
          <template #body-field="{ data }">{{ fieldLabel(data.field) }}</template>
          <template #body-current="{ data }">{{ valueText(data.field, data.current) }}</template>
          <template #body-incoming="{ data }"><strong>{{ valueText(data.field, data.incoming) }}</strong></template>
          <template #phone="{ data }">
            {{ kindLabel(data.kind) }} · {{ fieldLabel(data.field) }}: {{ valueText(data.field, data.current) }} →
            {{ valueText(data.field, data.incoming) }}
          </template>
        </ResourceTable>
      </div>

      <Message v-if="preview.conflicts.length" severity="warn" :closable="false">
        <p class="conflicts-title">{{ t('catalogueFile.conflicts') }}</p>
        <ul class="list">
          <li v-for="(c, i) in preview.conflicts" :key="i">
            <strong>{{ kindLabel(c.kind) }}: {{ c.name }}</strong> {{ c.detail }}
          </li>
        </ul>
      </Message>

      <div class="actions">
        <Button
          :label="t('catalogueFile.apply', { created: newCount, accepted: accepted.length })"
          icon="mdi mdi-check"
          :loading="busy"
          @click="apply"
        />
        <Button :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="cancel" />
      </div>
    </div>

    <div v-if="report" class="report" role="status">
      <p>
        <strong>{{ t('catalogueFile.imported', { created: report.created.length, updated: report.updated.length }) }}</strong>
      </p>
      <ul v-if="report.created.length || report.updated.length" class="list">
        <li v-for="c in report.created" :key="`c-${c.kind}-${c.id}`">
          {{ kindLabel(c.kind) }}: {{ c.name }} <span class="muted">({{ t('catalogueFile.created') }})</span>
        </li>
        <li v-for="u in report.updated" :key="`u-${u.kind}-${u.id}`">
          {{ kindLabel(u.kind) }}: {{ u.name }}
          <span class="muted">({{ u.fields.map(fieldLabel).join(', ') }})</span>
        </li>
      </ul>
      <p v-if="report.skipped.length" class="hint">
        {{ t('catalogueFile.skippedHint', { kinds: report.skipped.map(kindLabel).join(', ') }) }}
      </p>
      <Message v-if="report.conflicts.length" severity="warn" :closable="false">
        <p class="conflicts-title">{{ t('catalogueFile.notWritten') }}</p>
        <ul class="list">
          <li v-for="(c, i) in report.conflicts" :key="i">
            <strong>{{ kindLabel(c.kind) }}: {{ c.name }}</strong> {{ c.detail }}
          </li>
        </ul>
      </Message>
    </div>
  </section>
</template>

<style scoped lang="scss">
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.preview,
.block,
.report {
  display: grid;
  gap: var(--space-2);

  p {
    margin: 0;
  }
}

.block-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.summary,
.list {
  margin: 0;
  padding-left: var(--space-5);
}

.summary li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}

.name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.new-group {
  overflow-wrap: anywhere;
}

.muted {
  color: var(--p-text-muted-color);
}

.conflicts-title {
  font-weight: 700;
}
</style>
