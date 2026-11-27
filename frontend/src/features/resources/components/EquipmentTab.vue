<script setup lang="ts">
/**
 * The kitchen equipment catalogue on the shared management table: name with
 * icon, other names, kind and whether it is basic. The whole catalogue loads
 * at once and is filtered in the browser. Seeded items offer no delete in
 * their menu. Drafts an agent created carry a tag beside their name; for the
 * people who may activate them they are pinned to the top, and activated
 * from their menu.
 */
import { computed, onMounted, ref, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { EQUIPMENT_KINDS, equipmentIcon } from '@/shared/cookbook/equipment'
import type { EquipmentResponse } from '@/shared/cookbook/types'
import { useAppToast } from '@/core/composables/useAppToast'
import { activateEquipment, listEquipment } from '@/features/resources/api/resources'

import EquipmentDeleteDialog from './EquipmentDeleteDialog.vue'
import EquipmentDialog from './EquipmentDialog.vue'
import { USAGE_FILTERS, inUsageRange, usageRangeModel, useResourceUsage } from './useResourceUsage'

const props = defineProps<{ canWrite: boolean }>()
const canWrite = toRef(props, 'canWrite')
defineSlots<{ tabs?: () => unknown }>()

const { t } = useI18n()
const toast = useAppToast()
const table = useResourceTable('equipment', {
  q: 'string',
  kind: 'string',
  basic: 'string',
  ...USAGE_FILTERS,
})
const usage = useResourceUsage()
const usageRange = usageRangeModel(table.filters)

const items = ref<EquipmentResponse[]>([])
const loading = ref(false)
const editing = ref<EquipmentResponse | null>(null)
const dialog = ref(false)
const deleting = ref<EquipmentResponse | null>(null)
const deleteOpen = ref(false)
const deleteMode = ref<'delete' | 'merge'>('delete')

const allAliases = (item: EquipmentResponse) => Object.values(item.aliases).flat()
const aliasText = (item: EquipmentResponse) => allAliases(item).join(', ')
const kindLabel = (item: EquipmentResponse) => t(`equipmentKinds.${item.kind}`)

const filtered = computed(() =>
  items.value.filter(
    (item) =>
      matchesText(table.filters.q, item.name, ...Object.values(item.translations).map((tr) => tr.name), ...allAliases(item)) &&
      (!table.filters.kind || item.kind === table.filters.kind) &&
      (!table.filters.basic || (table.filters.basic === 'yes') === item.basic) &&
      inUsageRange(usage.count('equipment', item.id), table.filters),
  ),
)
// The drafts waiting for someone who may activate them sit at the top for
// those people; everyone else finds them in their place in the list.
const pinned = computed(() => (canWrite.value ? filtered.value.filter((item) => item.status === 'draft') : []))
const listed = computed(() => (canWrite.value ? filtered.value.filter((item) => item.status !== 'draft') : filtered.value))

const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'aliases', header: t('resources.equipment.otherNames'), sortField: aliasText },
  { field: 'kind', header: t('resources.equipment.kind'), filter: true, sortField: kindLabel },
  { field: 'basic', header: t('resources.equipment.basicColumn'), filter: true },
  {
    field: 'usage_count',
    header: t('resources.usage'),
    filter: true,
    class: 'numeric',
    sortField: (row: EquipmentResponse) => usage.count('equipment', row.id),
  },
])
const kindOptions = computed(() => EQUIPMENT_KINDS.map((k) => ({ value: k, label: t(`equipmentKinds.${k}`) })))
const yesNoOptions = computed(() => [
  { value: 'yes', label: t('tableFilters.yes') },
  { value: 'no', label: t('tableFilters.no') },
])

async function load() {
  loading.value = true
  try {
    items.value = await listEquipment()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

/** Loads the list and its usage counts again after a change. */
async function reload() {
  await Promise.all([load(), usage.reload().catch((err: unknown) => toast.error(err))])
}

function open(item: EquipmentResponse | null) {
  editing.value = item
  dialog.value = true
}

function askDelete(item: EquipmentResponse, mode: 'delete' | 'merge') {
  deleting.value = item
  deleteMode.value = mode
  deleteOpen.value = true
}

async function activate(item: EquipmentResponse) {
  try {
    await activateEquipment(item.id)
    toast.success(t('resources.equipment.activated'))
    await reload()
  } catch (err) {
    toast.error(err)
  }
}

const rowMenu = (item: EquipmentResponse): MenuItem[] => [
  {
    label: t('resources.equipment.activate'),
    icon: 'mdi mdi-check',
    visible: item.status === 'draft',
    command: () => void activate(item),
  },
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(item) },
  { label: t('resources.equipment.mergeOpen'), icon: 'mdi mdi-call-merge', command: () => askDelete(item, 'merge') },
  {
    label: t('common.delete'),
    icon: 'mdi mdi-delete-outline',
    visible: !item.seeded,
    command: () => askDelete(item, 'delete'),
  },
]

defineExpose({ create: () => open(null) })

onMounted(() => void load())
</script>

<template>
  <div class="table-page">
    <ResourceTable
      :state="table"
      :value="listed"
      :pinned="pinned"
      :columns="columns"
      :loading="loading"
      :clickable="canWrite"
      :menu="canWrite ? rowMenu : undefined"
      :empty-message="t('resources.equipment.empty')"
      empty-icon="mdi mdi-pot-steam"
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
          :aria-label="t('tableFilters.filterBy', { column: t('resources.equipment.kind') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #filter-basic>
        <Select
          v-model="table.filters.basic"
          :options="yesNoOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('resources.equipment.basicColumn') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <span class="equipment-name">
          <i :class="equipmentIcon(data.icon)" class="equipment-icon" aria-hidden="true" />
          <span class="resource-name">{{ data.name }}</span>
          <Tag v-if="data.status === 'draft'" :value="t('resources.equipment.statuses.draft')" severity="warn" />
        </span>
      </template>
      <template #body-aliases="{ data }">
        <span v-if="aliasText(data)" class="equipment-aliases" :title="aliasText(data)">{{ aliasText(data) }}</span>
      </template>
      <template #body-kind="{ data }">{{ kindLabel(data) }}</template>
      <template #body-basic="{ data }">
        <i v-if="data.basic" class="mdi mdi-check" :aria-label="t('tableFilters.yes')" />
      </template>
      <template #filter-usage_count>
        <NumberRangeFilter v-model="usageRange" :column="t('resources.usage')" />
      </template>
      <template #body-usage_count="{ data }">{{ usage.count('equipment', data.id) }}</template>
      <template #phone="{ data }">
        {{ kindLabel(data) }}<template v-if="aliasText(data)"> · {{ aliasText(data) }}</template>
      </template>
    </ResourceTable>

    <EquipmentDialog v-model:visible="dialog" :item="editing" @saved="reload" />
    <EquipmentDeleteDialog
      v-model:visible="deleteOpen"
      :item="deleting"
      :catalogue="items"
      :mode="deleteMode"
      @done="reload"
    />
  </div>
</template>

<style scoped lang="scss">
@use './resourceTab';

.equipment-name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.equipment-icon {
  font-size: var(--font-size-xl);
  color: var(--p-text-muted-color);
}

// The other names stay on one line; a very long list ends in an ellipsis
// and shows in full in its tooltip.
.equipment-aliases {
  display: inline-block;
  max-width: 24rem;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}
</style>
