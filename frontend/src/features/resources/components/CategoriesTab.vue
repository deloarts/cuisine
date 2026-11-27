<script setup lang="ts">
/**
 * The ingredient categories in their shopping order on the shared
 * management table. A writer changes the order by dragging rows, which
 * saves the new positions at once; a filtered list cannot be reordered.
 * Deleting one asks where its ingredients go.
 */
import { computed, ref, toRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import type { CategoryResponse } from '@/shared/cookbook/types'
import { saveCategory } from '@/features/resources/api/resources'

import CategoryDeleteDialog from './CategoryDeleteDialog.vue'
import { useResourceActions } from './useResourceActions'
import { USAGE_FILTERS, inUsageRange, usageRangeModel } from './useResourceUsage'

const props = defineProps<{ canWrite: boolean }>()
defineSlots<{ tabs?: () => unknown }>()

// The gap between the positions a drag writes, so a category set by hand or
// by an agent can still slot in between two others.
const ORDER_STEP = 10

const { t } = useI18n()
const { resources, usage, saving, save, apply, refresh } = useResourceActions()
const table = useResourceTable('categories', { q: 'string', ...USAGE_FILTERS })
const usageRange = usageRangeModel(table.filters)
const filtering = table.active

const dialog = ref(false)
const editing = ref<CategoryResponse | null>(null)
const texts = ref<Record<string, Record<string, string>>>({})

const sorted = computed(() => [...resources.categories.value].sort((a, b) => a.sort_order - b.sort_order))
const filtered = computed(() =>
  sorted.value.filter(
    (c) => matchesText(table.filters.q, c.name) && inUsageRange(usage.count('categories', c.id), table.filters),
  ),
)

// The order a drag produced, shown until the reload after saving it lands.
const reordered = ref<CategoryResponse[] | null>(null)
const rows = computed(() => reordered.value ?? filtered.value)
const canReorder = computed(() => props.canWrite && !filtering.value)

const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true, phone: true, sortable: false },
  {
    field: 'usage_count',
    header: t('resources.usage'),
    filter: true,
    class: 'numeric',
    sortField: (row: CategoryResponse) => usage.count('categories', row.id),
  },
])

function open(category: CategoryResponse | null) {
  editing.value = category
  // The rows are reactive proxies, which structuredClone refuses to copy.
  texts.value = structuredClone(toRaw(category?.translations ?? {}))
  dialog.value = true
}

async function submit() {
  const category = editing.value
  // A new category goes to the end of the shopping order.
  const last = Math.max(0, ...resources.categories.value.map((c) => c.sort_order))
  const body = {
    sort_order: category?.sort_order ?? last + ORDER_STEP,
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => v.name?.trim())
        .map(([locale, v]) => [locale, { name: (v.name ?? '').trim() }]),
    ),
  }
  const ok = await save(() => saveCategory(category?.id ?? null, body))
  if (ok) dialog.value = false
}

/** Saves the dragged order as 10, 20, 30, writing only the categories whose value changes. */
async function reorder(next: CategoryResponse[]) {
  const changed = next
    .map((category, index) => ({ category, sortOrder: (index + 1) * ORDER_STEP }))
    .filter(({ category, sortOrder }) => category.sort_order !== sortOrder)
  if (!changed.length) return
  reordered.value = next
  await apply(() =>
    Promise.all(
      changed.map(({ category, sortOrder }) =>
        saveCategory(category.id, { sort_order: sortOrder, translations: category.translations }),
      ),
    ),
  )
  reordered.value = null
}

const deleting = ref<CategoryResponse | null>(null)
const deleteOpen = ref(false)

function askDelete(category: CategoryResponse) {
  deleting.value = category
  deleteOpen.value = true
}

const rowMenu = (category: CategoryResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(category) },
  { label: t('common.delete'), icon: 'mdi mdi-delete-outline', command: () => askDelete(category) },
]

defineExpose({ create: () => open(null) })
</script>

<template>
  <div class="table-page">
    <ResourceTable
      :state="table"
      :value="rows"
      :columns="columns"
      :default-sort="null"
      :reorderable="canReorder"
      :clickable="canWrite"
      :menu="canWrite ? rowMenu : undefined"
      :empty-message="t('resources.categories.empty')"
      empty-icon="mdi mdi-shape-outline"
      @row-click="open"
      @reorder="reorder"
    >
      <template #header="{ wide }">
        <slot name="tabs" />
        <p class="hint">
          {{ t('resources.categories.hint') }}
          <template v-if="canWrite">
            {{
              filtering
                ? t('resources.categories.reorderFiltered')
                : t(wide ? 'resources.categories.reorderHint' : 'resources.categories.reorderHintPhone')
            }}
          </template>
        </p>
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
      <template #body-name="{ data }">
        <span class="resource-name">{{ data.name }}</span>
      </template>
      <template #filter-usage_count>
        <NumberRangeFilter v-model="usageRange" :column="t('resources.usage')" />
      </template>
      <template #body-usage_count="{ data }">{{ usage.count('categories', data.id) }}</template>
    </ResourceTable>

    <Dialog
      v-model:visible="dialog"
      modal
      :header="editing ? t('resources.categories.edit') : t('resources.categories.create')"
      class="resource-dialog"
    >
      <form class="dialog-form" @submit.prevent="submit">
        <TranslationFields
          v-model="texts"
          id-prefix="category"
          original-locale="en-GB"
          :fields="[{ key: 'name', label: t('common.name') }]"
        />
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="dialog = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
        </div>
      </form>
    </Dialog>
    <CategoryDeleteDialog
      v-model:visible="deleteOpen"
      :category="deleting"
      :categories="resources.categories.value"
      @done="refresh"
    />
  </div>
</template>

<style scoped lang="scss">
@use './resourceTab';
</style>
