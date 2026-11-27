<script setup lang="ts">
/**
 * The tags on the shared management table, filtered by name and kind in the
 * browser. Deleting a tag removes it from every recipe; nothing blocks it,
 * and a seeded tag never comes back.
 */
import { computed, ref, toRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import NumberRangeFilter from '@/shared/components/table-filters/NumberRangeFilter.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import TranslationFields from '@/shared/cookbook/TranslationFields.vue'
import type { TagKind, TagResponse } from '@/shared/cookbook/types'
import { deleteTag, saveTag } from '@/features/resources/api/resources'

import { useResourceActions } from './useResourceActions'
import { USAGE_FILTERS, inUsageRange, usageRangeModel } from './useResourceUsage'

defineProps<{ canWrite: boolean }>()
defineSlots<{ tabs?: () => unknown }>()

const { t, te } = useI18n()

// A kind the backend no longer offers still shows by its raw value.
const kindLabel = (kind: string) => (te(`resources.tagKinds.${kind}`) ? t(`resources.tagKinds.${kind}`) : kind)
const { resources, usage, saving, save, remove } = useResourceActions()

const KINDS: TagKind[] = ['meal', 'cuisine', 'occasion', 'other']
const kindOptions = computed(() => KINDS.map((k) => ({ value: k, label: t(`resources.tagKinds.${k}`) })))

const table = useResourceTable('tags', { q: 'string', kind: 'string', ...USAGE_FILTERS })
const usageRange = usageRangeModel(table.filters)

const dialog = ref(false)
const editing = ref<TagResponse | null>(null)
const kind = ref<TagKind>('meal')
const color = ref('')
const texts = ref<Record<string, Record<string, string>>>({})

const filtered = computed(() =>
  resources.tags.value.filter(
    (tag) =>
      matchesText(table.filters.q, tag.name) &&
      (!table.filters.kind || tag.kind === table.filters.kind) &&
      inUsageRange(usage.count('tags', tag.id), table.filters),
  ),
)
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'kind', header: t('resources.tags.kind'), filter: true, sortField: (tag: TagResponse) => kindLabel(tag.kind) },
  {
    field: 'usage_count',
    header: t('resources.usage'),
    filter: true,
    class: 'numeric',
    sortField: (row: TagResponse) => usage.count('tags', row.id),
  },
])

function open(tag: TagResponse | null) {
  editing.value = tag
  kind.value = (tag?.kind as TagKind | undefined) ?? 'meal'
  color.value = tag?.color ?? ''
  // The rows are reactive proxies, which structuredClone refuses to copy.
  texts.value = structuredClone(toRaw(tag?.translations ?? {}))
  dialog.value = true
}

async function submit() {
  const body = {
    kind: kind.value,
    color: color.value || null,
    translations: Object.fromEntries(
      Object.entries(texts.value)
        .filter(([, v]) => v.name?.trim())
        .map(([locale, v]) => [locale, { name: (v.name ?? '').trim() }]),
    ),
  }
  const tag = editing.value
  const ok = await save(() => saveTag(tag?.id ?? null, body))
  if (ok) dialog.value = false
}

const askDelete = (tag: TagResponse) =>
  remove(t('resources.tags.deleteConfirm', { name: tag.name }), () => deleteTag(tag.id))

const rowMenu = (tag: TagResponse): MenuItem[] => [
  { label: t('common.edit'), icon: 'mdi mdi-pencil', command: () => open(tag) },
  { label: t('common.delete'), icon: 'mdi mdi-delete-outline', command: () => askDelete(tag) },
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
      :empty-message="t('resources.tags.empty')"
      empty-icon="mdi mdi-tag-outline"
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
          :aria-label="t('tableFilters.filterBy', { column: t('resources.tags.kind') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <span class="tag-name">
          <span class="swatch" :style="data.color ? { background: data.color } : undefined" aria-hidden="true" />
          <span class="resource-name">{{ data.name }}</span>
        </span>
      </template>
      <template #filter-usage_count>
        <NumberRangeFilter v-model="usageRange" :column="t('resources.usage')" />
      </template>
      <template #body-usage_count="{ data }">{{ usage.count('tags', data.id) }}</template>
      <template #body-kind="{ data }">{{ kindLabel(data.kind) }}</template>
      <template #phone="{ data }">{{ kindLabel(data.kind) }}</template>
    </ResourceTable>

    <Dialog
      v-model:visible="dialog"
      modal
      :header="editing ? t('resources.tags.edit') : t('resources.tags.create')"
      class="resource-dialog"
    >
      <form class="dialog-form" @submit.prevent="submit">
        <div class="field">
          <label id="tag-kind-label" for="tag-kind">{{ t('resources.tags.kind') }}</label>
          <Select
            id="tag-kind"
            v-model="kind"
            :options="kindOptions"
            option-label="label"
            option-value="value"
            aria-labelledby="tag-kind-label"
            fluid
          />
        </div>
        <div class="field">
          <label for="tag-color">{{ t('resources.tags.color') }}</label>
          <InputText id="tag-color" v-model="color" placeholder="#2f855a" fluid />
          <small class="field-hint">{{ t('resources.tags.colorHint') }}</small>
        </div>
        <TranslationFields
          v-model="texts"
          id-prefix="tag"
          original-locale="en-GB"
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

.tag-name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
