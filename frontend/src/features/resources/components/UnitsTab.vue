<script setup lang="ts">
/**
 * The units on the shared management table, filtered by name and kind in
 * the browser. Deleting goes through a dialog that refuses seeded units and
 * offers a merge for one still in use.
 */
import { computed, ref, toRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import type { UnitKind, UnitResponse } from '@/shared/cookbook/types'
import { saveUnit } from '@/features/resources/api/resources'

import UnitDeleteDialog from './UnitDeleteDialog.vue'
import { useResourceActions } from './useResourceActions'
import { USAGE_FILTERS, inUsageRange, usageRangeModel } from './useResourceUsage'

defineProps<{ canWrite: boolean }>()
defineSlots<{ tabs?: () => unknown }>()

const { t, locale } = useI18n()
const { resources, usage, saving, save, refresh } = useResourceActions()
const table = useResourceTable('units', { q: 'string', kind: 'string', ...USAGE_FILTERS })
const usageRange = usageRangeModel(table.filters)

const KINDS: UnitKind[] = ['mass', 'volume', 'count', 'other']
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`resources.unitKinds.${k}`) })))

const dialog = ref(false)
const editing = ref<UnitResponse | null>(null)
const code = ref('')
const kind = ref<UnitKind>('mass')
const toBase = ref<number | null>(null)
const sortOrder = ref(0)
const texts = ref<Record<string, Record<string, string>>>({})

const filtered = computed(() =>
  resources.units.value.filter(
    (u) =>
      matchesText(table.filters.q, u.name, u.plural_name, u.abbreviation, u.code) &&
      (!table.filters.kind || u.kind === table.filters.kind) &&
      inUsageRange(usage.count('units', u.id), table.filters),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  {
    field: 'abbreviation',
    header: t('resources.units.abbreviation'),
    sortField: (unit: UnitResponse) => unit.abbreviation || unit.code,
  },
  {
    field: 'kind',
    header: t('resources.units.kind'),
    filter: true,
    sortField: (unit: UnitResponse) => t(`resources.unitKinds.${unit.kind}`),
  },
  { field: 'to_base', header: t('resources.units.factor') },
  {
    field: 'usage_count',
    header: t('resources.usage'),
    filter: true,
    class: 'numeric',
    sortField: (row: UnitResponse) => usage.count('units', row.id),
  },
])
const hasBase = computed(() => kind.value === 'mass' || kind.value === 'volume')

function baseLabel(unit: UnitResponse): string {
  if (unit.to_base === null) return ''
  // In the reader's own number format: "= 0,001 g" and "= 1.000 ml" in German.
  const amount = new Intl.NumberFormat(contentLocaleOf(locale.value), { maximumFractionDigits: 6 }).format(unit.to_base)
  return unit.kind === 'mass' ? `= ${amount} g` : `= ${amount} ml`
}

function open(unit: UnitResponse | null) {
  editing.value = unit
  code.value = unit?.code ?? ''
  kind.value = (unit?.kind as UnitKind | undefined) ?? 'mass'
  toBase.value = unit?.to_base ?? null
  sortOrder.value = unit?.sort_order ?? (resources.units.value.length + 1) * 10
  // The rows are reactive proxies, which structuredClone refuses to copy.
  texts.value = structuredClone(toRaw(unit?.translations ?? {}))
  dialog.value = true
}

async function submit() {
  const body = {
    code: code.value.trim(),
    kind: kind.value,
    to_base: hasBase.value ? toBase.value : null,
    sort_order: sortOrder.value,
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => v.name?.trim())
        .map(([locale, v]) => [
          locale,
          {
            name: (v.name ?? '').trim(),
            plural_name: (v.plural_name ?? '').trim() || (v.name ?? '').trim(),
            abbreviation: (v.abbreviation ?? '').trim(),
          },
        ]),
    ),
  }
  const unit = editing.value
  const ok = await save(() => saveUnit(unit?.id ?? null, body))
  if (ok) dialog.value = false
}

const deleting = ref<UnitResponse | null>(null)
const deleteOpen = ref(false)

function askDelete(unit: UnitResponse) {
  deleting.value = unit
  deleteOpen.value = true
}

const rowMenu = (unit: UnitResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(unit) },
  { label: t('common.delete'), icon: 'mdi mdi-delete-outline', command: () => askDelete(unit) },
]

defineExpose({ create: () => open(null) })
</script>

<template>
  <div class="table-page">
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :clickable="canWrite"
      :menu="canWrite ? rowMenu : undefined"
      :empty-message="t('resources.units.empty')"
      empty-icon="mdi mdi-scale"
      @row-click="open"
    >
      <template #header>
        <slot name="tabs" />
      </template>
      <template #filter-name>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('resources.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #filter-kind>
        <Select
          v-model="table.filters.kind"
          :options="kindOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('resources.units.kind') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <span class="resource-name">{{ data.name }}</span>
      </template>
      <template #body-abbreviation="{ data }">{{ data.abbreviation || data.code }}</template>
      <template #body-kind="{ data }">{{ t(`resources.unitKinds.${data.kind}`) }}</template>
      <template #filter-usage_count>
        <NumberRangeFilter v-model="usageRange" :column="t('resources.usage')" />
      </template>
      <template #body-usage_count="{ data }">{{ usage.count('units', data.id) }}</template>
      <template #body-to_base="{ data }">{{ baseLabel(data) }}</template>
      <template #phone="{ data }">
        {{ data.abbreviation || data.code }} · {{ t(`resources.unitKinds.${data.kind}`) }} {{ baseLabel(data) }}
      </template>
    </ResourceTable>

    <Dialog
      v-model:visible="dialog"
      modal
      :header="editing ? t('resources.units.edit') : t('resources.units.create')"
      class="resource-dialog"
    >
      <form class="dialog-form" @submit.prevent="submit">
        <div class="form-grid">
          <div class="field">
            <label for="unit-code">{{ t('resources.units.code') }}</label>
            <InputText id="unit-code" v-model="code" required fluid />
            <small class="field-hint">{{ t('resources.units.codeHint') }}</small>
          </div>
          <div class="field">
            <label id="unit-kind-label" for="unit-kind">{{ t('resources.units.kind') }}</label>
            <Select
              id="unit-kind"
              v-model="kind"
              :options="kindOptions"
              option-label="label"
              option-value="value"
              aria-labelledby="unit-kind-label"
              fluid
            />
          </div>
          <div v-if="hasBase" class="field">
            <label for="unit-base">{{ kind === 'mass' ? t('resources.units.toGrams') : t('resources.units.toMillilitres') }}</label>
            <InputNumber
              v-model="toBase"
              input-id="unit-base"
              :min-fraction-digits="0"
              :max-fraction-digits="4"
              :min="0"
              fluid
            />
          </div>
          <div class="field">
            <label for="unit-sort">{{ t('resources.sortOrder') }}</label>
            <InputNumber v-model="sortOrder" input-id="unit-sort" :use-grouping="false" fluid />
          </div>
        </div>
        <TranslationFields
          v-model="texts"
          id-prefix="unit"
          original-locale="en-GB"
          :fields="[
            { key: 'name', label: t('common.name') },
            { key: 'plural_name', label: t('resources.units.plural') },
            { key: 'abbreviation', label: t('resources.units.abbreviation') },
          ]"
        />
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="dialog = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
        </div>
      </form>
    </Dialog>
    <UnitDeleteDialog
      v-model:visible="deleteOpen"
      :unit="deleting"
      :units="resources.units.value"
      @done="refresh"
    />
  </div>
</template>

<style scoped lang="scss">
@use './resourceTab';
</style>
