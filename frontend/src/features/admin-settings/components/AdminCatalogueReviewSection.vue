<script setup lang="ts">
/**
 * The review queue for draft ingredients: the ones an agent created, the ones
 * added inline in the recipe editor and the ones a typed intolerance named.
 * Each row shows the near-duplicates the catalogue already has, so a draft
 * is either merged into the existing ingredient (its names become aliases
 * there) or checked in the editor and activated.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import IngredientPicker from '@/shared/cookbook/IngredientPicker.vue'
import type { IngredientResponse } from '@/shared/cookbook/types'
import { mergeSuggestions, type DuplicateCandidate } from '@/features/admin-settings/catalogueReview'
import { catalogueApi } from '@/features/admin-settings/api/catalogue'
import { useAppToast } from '@/core/composables/useAppToast'
import { formatDateTime } from '@/core/utils/dates'

const LIMIT = 200

const { t } = useI18n()
const toast = useAppToast()

const drafts = ref<IngredientResponse[]>([])
const suggestions = ref<Record<string, DuplicateCandidate[]>>({})
const loading = ref(false)
const busy = ref<string | null>(null)

const merging = ref<IngredientResponse | null>(null)
const mergeDialog = ref(false)
const target = ref<string | null>(null)
const otherTarget = ref<IngredientResponse | null>(null)

const table = useResourceTable('catalogueReview', { q: 'string' })
const filtered = computed(() => drafts.value.filter((d) => matchesText(table.filters.q, d.name)))
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'duplicates', header: t('adminArea.review.duplicates'), sortable: false },
  { field: 'category', header: t('adminArea.review.category'), sortField: (d: IngredientResponse) => d.category?.name ?? '' },
  { field: 'changed', header: t('adminArea.review.changed') },
])
const mergeChoices = computed(() => (merging.value ? (suggestions.value[merging.value.id] ?? []) : []))
const mergeTarget = computed(() => {
  if (target.value && target.value !== 'other') return target.value
  return otherTarget.value && typeof otherTarget.value === 'object' && otherTarget.value.id !== merging.value?.id
    ? otherTarget.value.id
    : null
})

async function findDuplicates(draft: IngredientResponse) {
  try {
    const found = await catalogueApi.duplicates(draft.name)
    suggestions.value = { ...suggestions.value, [draft.id]: mergeSuggestions(draft.id, found) }
  } catch {
    suggestions.value = { ...suggestions.value, [draft.id]: [] }
  }
}

async function load() {
  loading.value = true
  try {
    drafts.value = (await catalogueApi.ingredients({ status: 'draft', limit: LIMIT })).items
    suggestions.value = {}
    await Promise.all(drafts.value.map(findDuplicates))
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function activate(draft: IngredientResponse) {
  busy.value = draft.id
  try {
    await catalogueApi.activate(draft.id)
    toast.success(t('adminArea.review.activated', { name: draft.name }))
    drafts.value = drafts.value.filter((d) => d.id !== draft.id)
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

function openMerge(draft: IngredientResponse, into: string | null = null) {
  merging.value = draft
  const first = suggestions.value[draft.id]?.[0]?.id ?? null
  target.value = into ?? first ?? 'other'
  otherTarget.value = null
  mergeDialog.value = true
}

async function merge() {
  const draft = merging.value
  const into = mergeTarget.value
  if (!draft || !into) return
  busy.value = draft.id
  try {
    const result = await catalogueApi.merge(draft.id, into)
    toast.success(t('adminArea.review.merged', { name: draft.name, into: result.name }))
    mergeDialog.value = false
    drafts.value = drafts.value.filter((d) => d.id !== draft.id)
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

const draftMenu = (draft: IngredientResponse): MenuItem[] => [
  {
    label: t('adminArea.review.activate', { name: draft.name }),
    icon: 'mdi mdi-check',
    disabled: busy.value === draft.id,
    command: () => void activate(draft),
  },
  { label: t('adminArea.review.merge', { name: draft.name }), icon: 'mdi mdi-call-merge', command: () => openMerge(draft) },
]

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.review.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <p class="hint">{{ t('adminArea.review.hint') }}</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :menu="draftMenu"
      :empty-message="t('adminArea.review.none')"
      empty-icon="mdi mdi-check-all"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <RouterLink :to="{ name: 'ingredient', params: { id: data.id } }">{{ data.name }}</RouterLink>
      </template>
      <template #body-duplicates="{ data }">
        <span v-if="!suggestions[data.id]?.length" class="text-muted">{{ t('adminArea.review.noDuplicates') }}</span>
        <span v-else class="candidates">
          <Button
            v-for="c in suggestions[data.id]"
            :key="c.id"
            v-tooltip.top="c.matched !== c.name ? t('adminArea.review.matchedBy', { name: c.matched }) : undefined"
            :label="c.name"
            :icon="c.exact ? 'mdi mdi-equal' : 'mdi mdi-approximately-equal'"
            size="small"
            outlined
            :aria-label="t('adminArea.review.mergeInto', { name: data.name, into: c.name })"
            @click="openMerge(data, c.id)"
          />
        </span>
      </template>
      <template #body-category="{ data }">{{ data.category?.name }}</template>
      <template #body-changed="{ data }">{{ formatDateTime(data.changed) }}</template>
      <template #phone="{ data }">
        {{ suggestions[data.id]?.length ? t('adminArea.review.duplicateCount', { count: suggestions[data.id]?.length ?? 0 }, suggestions[data.id]?.length ?? 0) : '' }}
      </template>
    </ResourceTable>

    <Dialog
      v-model:visible="mergeDialog"
      modal
      :header="t('adminArea.review.mergeTitle', { name: merging?.name ?? '' })"
      class="merge-dialog"
    >
      <form class="merge-form" @submit.prevent="merge">
        <p class="hint">{{ t('adminArea.review.mergeHint') }}</p>
        <fieldset class="targets">
          <legend class="field-label">{{ t('adminArea.review.target') }}</legend>
          <div v-for="c in mergeChoices" :key="c.id" class="target">
            <RadioButton v-model="target" :input-id="`merge-${c.id}`" :value="c.id" />
            <label :for="`merge-${c.id}`">
              {{ c.name }}
              <small v-if="c.matched !== c.name" class="text-muted">{{ t('adminArea.review.matchedBy', { name: c.matched }) }}</small>
            </label>
          </div>
          <div class="target">
            <RadioButton v-model="target" input-id="merge-other" value="other" />
            <label for="merge-other">{{ t('adminArea.review.otherTarget') }}</label>
          </div>
          <IngredientPicker
            v-if="target === 'other'"
            v-model="otherTarget"
            input-id="merge-other-picker"
            :placeholder="t('adminArea.review.searchTarget')"
          />
        </fieldset>
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="mergeDialog = false" />
          <Button
            type="submit"
            :label="t('adminArea.review.mergeAction')"
            icon="mdi mdi-call-merge"
            :disabled="!mergeTarget"
            :loading="busy === merging?.id"
          />
        </div>
      </form>
    </Dialog>
  </section>
</template>

<style scoped lang="scss">
.candidates {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.merge-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.merge-form {
  display: grid;
  gap: var(--space-3);
}

.targets {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  border: 0;
}

.target {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;

  label {
    display: grid;
  }
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
