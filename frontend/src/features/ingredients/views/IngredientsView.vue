<script setup lang="ts">
/**
 * The ingredient catalogue on the shared management table: a filter in
 * every column's header row, the filters in the URL, paged on the server
 * unless a filter the backend lacks needs the browser to narrow the list.
 * Name and usage sort on the server; the other columns do not sort. A draft
 * carries a tag beside its name, and for the people who may activate drafts
 * the matching ones are pinned above the list, which then holds only the
 * active ingredients.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import PageHeader from '@/shared/components/PageHeader.vue'
import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import type { IngredientListItem } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import IngredientFilterControl, {
  type IngredientFilterField,
} from '@/features/ingredients/components/IngredientFilterControl.vue'
import {
  CLIENT_FILTER_LIMIT,
  INGREDIENT_FILTERS,
  matchesClientFilters,
  needsClientFiltering,
  serverQuery,
  serverSort,
  type IngredientFilters,
} from '@/features/ingredients/ingredientFilters'
import { formatSeason } from '@/shared/cookbook/season'
import { listIngredients } from '@/features/ingredients/api/ingredients'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const router = useRouter()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const resources = useCookbookResources()

const canCreate = computed(() => currentUser.hasPermission(Permission.WRITE_INGREDIENTS))
const canActivate = computed(() => currentUser.hasPermission(Permission.MANAGE_INGREDIENTS))

const table = useResourceTable('ingredients', INGREDIENT_FILTERS, () => load())
// The filter controls bind through v-model, which wants a writable value.
const filters = computed<IngredientFilters>({
  get: () => table.filters,
  set: (v) => Object.assign(table.filters, v),
})

const items = ref<IngredientListItem[]>([])
const drafts = ref<IngredientListItem[]>([])
const total = ref(0)
const truncated = ref(false)
const loading = ref(false)

const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'q', header: t('common.name'), filter: true, sortable: true },
  { field: 'category', header: t('ingredients.category'), filter: true },
  { field: 'family', header: t('ingredients.family'), filter: true },
  { field: 'mine', header: t('ingredients.owner'), filter: true },
  { field: 'allergens', header: t('ingredients.allergens'), filter: true },
  { field: 'diets', header: t('ingredients.dietMarkers'), filter: true },
  { field: 'season', header: t('ingredients.season.column'), filter: true },
  { field: 'kcal', header: t('ingredients.kcalPer100'), filter: true, class: 'numeric' },
  { field: 'usage', header: t('ingredients.usage'), filter: true, class: 'numeric', sortable: true },
])
const label = (field: string) => columns.value.find((c) => c.field === field)?.header ?? field

let sequence = 0

async function load() {
  const current = ++sequence
  loading.value = true
  const { first, rows } = table
  const sort = serverSort(table.sortField.value, table.sortOrder.value)
  // Pinning splits the drafts from the list, unless a status filter from an
  // older link already narrows it to one of them.
  const pin = canActivate.value && !table.filters.status
  const query = { ...serverQuery(table.filters), ...(pin ? { status: 'active' as const } : {}) }
  try {
    const pending = pin ? loadDrafts() : Promise.resolve([])
    if (needsClientFiltering(table.filters)) {
      const page = await listIngredients({ ...query, ...sort, limit: CLIENT_FILTER_LIMIT, offset: 0 })
      if (current !== sequence) return
      const matching = page.items.filter((item) => matchesClientFilters(item, table.filters))
      truncated.value = page.total > page.items.length
      total.value = matching.length
      items.value = matching.slice(first.value, first.value + rows.value)
    } else {
      const page = await listIngredients({ ...query, ...sort, limit: rows.value, offset: first.value })
      if (current !== sequence) return
      truncated.value = false
      items.value = page.items
      total.value = page.total
    }
    const pinned = await pending
    if (current === sequence) drafts.value = pinned
  } catch (err) {
    toast.error(err)
  } finally {
    if (current === sequence) loading.value = false
  }
}

/** The drafts that match the filters, for the pinned rows. */
async function loadDrafts(): Promise<IngredientListItem[]> {
  const page = await listIngredients({
    ...serverQuery(table.filters),
    status: 'draft',
    limit: CLIENT_FILTER_LIMIT,
    offset: 0,
  })
  return page.items.filter((item) => matchesClientFilters(item, table.filters))
}

function kcal(item: IngredientListItem): string {
  const value = item.nutrition.kcal
  return value === null || value === undefined ? '' : `${Math.round(value)}`
}

function months(item: IngredientListItem): string {
  return formatSeason(item.season_months, (m) => t(`ingredients.season.short.${m}`))
}

function open(item: IngredientListItem) {
  void router.push({ name: 'ingredient', params: { id: item.id } })
}

onMounted(() => {
  void load()
  resources.load().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <section class="table-page">
    <PageHeader :title="t('nav.ingredients')">
      <Button
        v-if="canCreate"
        :label="t('ingredients.create')"
        icon="mdi mdi-plus"
        @click="router.push({ name: 'ingredient-new' })"
      />
    </PageHeader>

    <ResourceTable
      :state="table"
      :value="items"
      :pinned="drafts"
      :columns="columns"
      :total="total"
      :loading="loading"
      :empty-message="t('ingredients.empty')"
      empty-icon="mdi mdi-carrot"
      clickable
      @row-click="open"
    >
      <template v-if="truncated" #header>
        <Message severity="warn" size="small" :closable="false">
          {{ t('ingredients.truncated', { count: CLIENT_FILTER_LIMIT }) }}
        </Message>
      </template>
      <template v-for="column in columns" :key="column.field" #[`filter-${column.field}`]>
        <IngredientFilterControl
          v-model="filters"
          :field="column.field as IngredientFilterField"
          :label="label(column.field)"
        />
      </template>
      <template #body-q="{ data }">
        <RouterLink :to="{ name: 'ingredient', params: { id: data.id } }" class="name-link" @click.stop>
          {{ data.name }}
        </RouterLink>
        <Tag v-if="data.status === 'draft'" :value="t('ingredients.status.draft')" severity="warn" class="tag" />
      </template>
      <template #phone="{ data }">
        {{ data.category?.name ?? t('ingredients.noCategory') }}<template v-if="kcal(data)"> · {{ kcal(data) }} kcal</template>
      </template>
      <template #body-category="{ data }">{{ data.category?.name }}</template>
      <template #body-family="{ data }">{{ data.family?.name }}</template>
      <template #body-mine="{ data }">{{ data.owner?.display_name }}</template>
      <template #body-allergens="{ data }">
        <template v-if="data.allergens.length">
          <Tag v-for="a in data.allergens" :key="a" :value="t(`allergens.${a}`)" severity="secondary" class="tag" />
        </template>
      </template>
      <template #body-diets="{ data }">
        <template v-if="data.diet_markers.length">
          <Tag v-for="m in data.diet_markers" :key="m" :value="t(`dietMarkers.${m}`)" severity="secondary" class="tag" />
        </template>
      </template>
      <template #body-season="{ data }">
        <span class="season">{{ months(data) }}</span>
      </template>
      <template #body-kcal="{ data }">{{ kcal(data) }}</template>
      <template #body-usage="{ data }">{{ data.usage_count }}</template>
    </ResourceTable>
  </section>
</template>

<style scoped lang="scss">
.name-link {
  font-weight: 700;
  color: inherit;
  text-decoration: none;
}

.tag {
  margin: 0 var(--space-1) var(--space-1) var(--space-1);
}

.season {
  font-size: var(--font-size-sm);
}
</style>
