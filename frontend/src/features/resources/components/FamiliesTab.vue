<script setup lang="ts">
/**
 * Ingredient families, such as "Tomatoes" for fresh, tinned and passata:
 * a name per language, nothing else. Food restrictions, the ingredient
 * filter and the shopping list use them to treat the variants together.
 * Deleting a family leaves its ingredients without one.
 */
import { computed, ref, toRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import type { FamilyResponse } from '@/shared/cookbook/types'
import { deleteFamily, saveFamily } from '@/features/resources/api/resources'

import { useResourceActions } from './useResourceActions'
import { USAGE_FILTERS, inUsageRange, usageRangeModel } from './useResourceUsage'

defineProps<{ canWrite: boolean }>()
defineSlots<{ tabs?: () => unknown }>()

const { t } = useI18n()
const { resources, usage, saving, save, remove } = useResourceActions()
const table = useResourceTable('families', { q: 'string', ...USAGE_FILTERS })
const usageRange = usageRangeModel(table.filters)

const dialog = ref(false)
const editing = ref<FamilyResponse | null>(null)
const texts = ref<Record<string, Record<string, string>>>({})

// The search also matches a family's name in the other language.
const filtered = computed(() =>
  resources.families.value.filter(
    (f) =>
      matchesText(table.filters.q, f.name, ...Object.values(f.translations).map((tr) => tr.name)) &&
      inUsageRange(usage.count('families', f.id), table.filters),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  {
    field: 'usage_count',
    header: t('resources.usage'),
    filter: true,
    class: 'numeric',
    sortField: (row: FamilyResponse) => usage.count('families', row.id),
  },
])

function open(family: FamilyResponse | null) {
  editing.value = family
  // The rows are reactive proxies, which structuredClone refuses to copy.
  texts.value = structuredClone(toRaw(family?.translations ?? {}))
  dialog.value = true
}

async function submit() {
  const body = {
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => v.name?.trim())
        .map(([locale, v]) => [locale, { name: (v.name ?? '').trim() }]),
    ),
  }
  const family = editing.value
  const ok = await save(() => saveFamily(family?.id ?? null, body))
  if (ok) dialog.value = false
}

const askDelete = (family: FamilyResponse) =>
  remove(t('resources.families.deleteConfirm', { name: family.name }), () => deleteFamily(family.id))

const rowMenu = (family: FamilyResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(family) },
  { label: t('common.delete'), icon: 'mdi mdi-delete-outline', command: () => askDelete(family) },
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
      :empty-message="t('resources.families.empty')"
      empty-icon="mdi mdi-family-tree"
      @row-click="open"
    >
      <template #header>
        <slot name="tabs" />
        <p class="hint">{{ t('resources.families.hint') }}</p>
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
      <template #body-usage_count="{ data }">{{ usage.count('families', data.id) }}</template>
    </ResourceTable>

    <Dialog
      v-model:visible="dialog"
      modal
      :header="editing ? t('resources.families.edit') : t('resources.families.create')"
      class="resource-dialog"
    >
      <form class="dialog-form" @submit.prevent="submit">
        <p class="hint">{{ t('resources.families.dialogHint') }}</p>
        <TranslationFields
          v-model="texts"
          id-prefix="family"
          original-locale="de-AT"
          :fields="[{ key: 'name', label: t('common.name') }]"
        />
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="dialog = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
@use './resourceTab';
</style>
