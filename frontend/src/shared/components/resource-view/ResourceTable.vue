<script setup lang="ts" generic="T extends object">
/**
 * The one management table every data table of the app is built on. It
 * brings a filter in each column's header row, a numbered and sortable
 * grid, a context menu per row, paging with a rows-per-page choice
 * remembered per table, and, in `fill` mode from the small breakpoint up,
 * a table that fills the rest of the page with a sticky header and its own
 * scrolling body. A table inside a stacked section passes `fill` false and
 * scrolls inside a capped height instead. Cells never wrap: a table wider
 * than its card scrolls sideways.
 *
 * There is no toolbar around the table. A page puts its create action in
 * its header, and the `header` slot renders inside the card above the grid
 * (for tabs or a notice). Clearing the filters is a button in the filter row
 * of the number column, shown while a filter is active.
 *
 * The row actions live in a context menu that `menu` builds per row: a right
 * click opens it, and so does a trailing button in each row, which keeps the
 * actions in reach of the keyboard and screen readers. With `clickable` a
 * click on a row emits `rowClick`, usually to open the row's edit dialog.
 *
 * A client table sorts itself by any column, by default by the first one in
 * ascending order. A lazy table (one with `total`) sorts only the columns
 * marked `sortable` and reads the order from its state when it loads.
 * `reorderable` swaps sorting for a drag handle (on a phone, where dragging a
 * row does not work with touch, a column of move up and move down buttons)
 * and emits the rows in their
 * new order.
 *
 * On a phone the table shows only its phone columns (the first one unless
 * a column says otherwise) with the `phone` slot under the first cell, and
 * the filters stack in a panel that a button in the card's top line opens.
 *
 * `pinned` rows sit above the others, outside sorting and paging, with a
 * pin in place of their number: the drafts waiting for someone to check and
 * activate them, for the people who may. The owner leaves them out of `value`.
 *
 * While `loading` and without rows, such as on the first load, the grid shows
 * skeleton rows instead of the empty state; a reload of a table that already
 * shows rows dims them under the grid's loading overlay.
 *
 * Slots: `body-<field>` and `filter-<field>` per column (the cell and the
 * filter control, both receive `wide`), `phone` for the extra lines of a
 * stacked row, `header` above the grid, and `empty`.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import EmptyState from '@/shared/components/EmptyState.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import type { ResourceTableState } from '@/shared/composables/useResourceTable'
import { useWideScreen } from '@/shared/composables/useWideScreen'

export interface ResourceTableColumn {
  /** The row's property shown by default, and the name of the column's slots. */
  field: string
  header: string
  /** The column has a `filter-<field>` slot. */
  filter?: boolean
  /** Shown on a phone too; without any, the first column is. */
  phone?: boolean
  /** Extra classes for the column's cells, such as `numeric`. */
  class?: string
  /**
   * Whether the column sorts. Defaults to true on a client table and false on
   * a lazy one, whose owner must support the field on the server.
   */
  sortable?: boolean
  /**
   * What the column sorts by when the shown text is not the row's `field`:
   * another property, or a function of the row (typed on `never` so a
   * function of any row type fits).
   */
  sortField?: string | ((row: never) => string | number)
  /** Lets long text wrap instead of widening the table. */
  wrap?: boolean
}

const props = withDefaults(
  defineProps<{
    state: ResourceTableState
    value: T[]
    columns: ResourceTableColumn[]
    /** The number of matching rows on the server; makes the table lazy. */
    total?: number
    loading?: boolean
    dataKey?: string
    emptyMessage?: string
    emptyIcon?: string
    /** Fill the page's height (the page is a `.table-page`) or scroll in a capped box. */
    fill?: boolean
    /** Rows are clickable and emit `rowClick`. */
    clickable?: boolean
    /** The actions of a row's context menu; no items means no menu for that row. */
    menu?: (row: T) => MenuItem[]
    /** Show the row number column. */
    rowNumbers?: boolean
    /** The field sorted by first; null keeps the given order. Defaults to the first sortable column. */
    defaultSort?: string | null
    /** Rows get a drag handle and emit `reorder`; sorting and paging are off. */
    reorderable?: boolean
    /** Rows kept at the top whatever the sort and page, such as drafts to check. */
    pinned?: T[]
  }>(),
  {
    total: undefined,
    loading: false,
    dataKey: 'id',
    emptyMessage: undefined,
    emptyIcon: undefined,
    fill: true,
    clickable: false,
    menu: undefined,
    rowNumbers: true,
    defaultSort: undefined,
    reorderable: false,
    pinned: () => [],
  },
)
const emit = defineEmits<{ rowClick: [row: T]; reorder: [rows: T[]] }>()

defineSlots<
  {
    [key: `body-${string}`]: (props: { data: T; wide: boolean }) => unknown
    [key: `filter-${string}`]: (props: { wide: boolean }) => unknown
  } & {
    phone?: (props: { data: T }) => unknown
    header?: (props: { wide: boolean }) => unknown
    empty?: () => unknown
  }
>()

const { t } = useI18n()
const wide = useWideScreen()
const { rows, first, rowOptions, active, sortField, sortOrder } = props.state
const showPhoneFilters = ref(false)
// The paginator fills in its own placeholders, so they pass through the
// translation as values.
const pageReport = computed(() =>
  t('tableFilters.pageReport', { from: '{first}', to: '{last}', total: '{totalRecords}' }),
)

const lazy = computed(() => props.total !== undefined)
const count = computed(() => props.total ?? props.value.length)
const showPaginator = computed(() => !props.reorderable && (count.value > rowOptions[0]! || first.value > 0))

const phoneColumns = computed(() => {
  const marked = props.columns.filter((c) => c.phone)
  return marked.length ? marked : props.columns.slice(0, 1)
})
const visibleColumns = computed(() => (wide.value ? props.columns : phoneColumns.value))
const leadColumn = computed(() => visibleColumns.value[0])
const filterColumns = computed(() => props.columns.filter((c) => c.filter))
// OpenVue renders a column's row filter only for a field in the filters model.
const tableFilters = computed(() =>
  Object.fromEntries(filterColumns.value.map((c) => [c.field, { value: null, matchMode: 'equals' }])),
)
const showFilterRow = computed(() => wide.value && filterColumns.value.length > 0)

function sortable(column: ResourceTableColumn): boolean {
  if (props.reorderable) return false
  return column.sortable ?? !lazy.value
}

// The first sortable column orders the rows until the user picks another.
onMounted(() => {
  if (sortField.value !== undefined || props.reorderable) return
  const initial = props.defaultSort === undefined ? props.columns.find(sortable)?.field : props.defaultSort
  if (initial) sortField.value = initial
})

// The state names the sorted column by its field; the grid gets what that
// column sorts by, which may be a function of the row.
const gridSortField = computed(() => {
  const field = sortField.value
  if (!field) return undefined
  return (props.columns.find((c) => c.field === field)?.sortField ?? field) as string | ((row: T) => string)
})

function onSort(event: { sortField?: unknown; sortOrder?: number | null }) {
  const raw = event.sortField
  const column = props.columns.find((c) => (c.sortField ?? c.field) === raw)
  props.state.onSort({ sortField: column?.field ?? (raw as string | undefined), sortOrder: event.sortOrder === -1 ? -1 : 1 })
}

function cell(row: T, field: string): unknown {
  return (row as Record<string, unknown>)[field] ?? ''
}

function onRowClick(event: { data: T; originalEvent: Event }) {
  // A click on a control inside the row (a link, a button, the drag handle) is its own.
  const target = event.originalEvent.target as HTMLElement | null
  if (target?.closest('a, button, input, [data-pc-section="reorderablerowhandle"], .resource-table-menu-cell, .resource-table-move')) return
  if (props.clickable) emit('rowClick', event.data)
}

// What the context menu reads of the event that opens it: where to appear.
type MenuAnchor = Pick<MouseEvent, 'pageX' | 'pageY' | 'preventDefault' | 'stopPropagation'>

const contextMenu = ref<{ show: (event: MenuAnchor) => void; hide: () => void } | null>(null)
const menuItems = ref<MenuItem[]>([])
const hasMenu = computed(() => props.menu !== undefined)
// The row button that opened the menu, focused again when the menu closes.
let menuTrigger: HTMLElement | null = null

function openMenu(event: MenuAnchor, row: T) {
  const items = props.menu?.(row) ?? []
  if (!items.length) return
  menuItems.value = items
  event.preventDefault()
  contextMenu.value?.show(event)
}

/**
 * Opens the menu from a row's button. A click from the keyboard carries no
 * pointer position, so the menu then appears below the button instead of in
 * the page's top left corner.
 */
function openMenuFromButton(event: MouseEvent, row: T) {
  const button = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  menuTrigger = button
  if (!button || event.detail !== 0) {
    openMenu(event, row)
    return
  }
  const rect = button.getBoundingClientRect()
  openMenu(
    {
      pageX: rect.left + window.scrollX,
      pageY: rect.bottom + window.scrollY,
      preventDefault: () => event.preventDefault(),
      stopPropagation: () => event.stopPropagation(),
    },
    row,
  )
}

function onMenuHide() {
  const trigger = menuTrigger
  menuTrigger = null
  if (trigger?.isConnected) trigger.focus()
}

function onRowContextMenu(event: { originalEvent: Event; data: T }) {
  menuTrigger = null
  openMenu(event.originalEvent as MouseEvent, event.data)
}

function onRowReorder(event: { value: T[] }) {
  emit('reorder', event.value)
}

// The phone's buttons move a row one place within the rows as given, which
// a reorderable table shows unsorted and unpaged.
function move(index: number, by: -1 | 1) {
  const target = index + by
  if (target < 0 || target >= props.value.length) return
  const next = [...props.value]
  const [row] = next.splice(index, 1)
  next.splice(target, 0, row!)
  emit('reorder', next)
}
</script>

<template>
  <div class="resource-table" :class="{ 'resource-table-fill': fill }">
    <div class="resource-table-card" :class="{ card: fill }">
      <div v-if="$slots.header || (!wide && filterColumns.length) || (!wide && active)" class="resource-table-header">
        <slot name="header" :wide="wide" />
        <div v-if="!wide && (filterColumns.length || active)" class="resource-table-phone-tools">
          <Button
            v-if="filterColumns.length"
            :label="t('tableFilters.filters')"
            icon="mdi mdi-filter-variant"
            text
            size="small"
            :aria-expanded="showPhoneFilters"
            @click="showPhoneFilters = !showPhoneFilters"
          />
          <Button
            v-if="active"
            :label="t('tableFilters.clearAll', { count: active })"
            icon="mdi mdi-filter-remove-outline"
            text
            size="small"
            @click="state.clear"
          />
        </div>
        <div v-if="!wide && showPhoneFilters && filterColumns.length" class="resource-table-phone-filters">
          <div v-for="column in filterColumns" :key="column.field" class="field">
            <span class="field-label">{{ column.header }}</span>
            <slot :name="`filter-${column.field}`" :wide="false" />
          </div>
        </div>
      </div>

      <DataTable
        :value="value"
        :frozen-value="pinned.length ? pinned : undefined"
        :loading="loading && value.length > 0"
        :filters="tableFilters"
        :filter-display="showFilterRow ? 'row' : undefined"
        :data-key="dataKey"
        :lazy="lazy"
        :paginator="showPaginator"
        :rows="rows"
        :rows-per-page-options="rowOptions"
        :paginator-template="wide ? undefined : 'PrevPageLink CurrentPageReport NextPageLink RowsPerPageDropdown'"
        :current-page-report-template="pageReport"
        :total-records="count"
        :first="first"
        :sort-field="gridSortField"
        :sort-order="sortOrder"
        :context-menu="hasMenu"
        scrollable
        :scroll-height="fill && wide ? 'flex' : '60vh'"
        size="small"
        striped-rows
        :row-hover="clickable"
        class="resource-table-grid"
        :class="{ 'resource-table-clickable': clickable, 'resource-table-stacked': !wide }"
        @page="state.onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @row-contextmenu="onRowContextMenu"
        @row-reorder="onRowReorder"
      >
        <template #empty>
          <span v-if="pinned.length && !loading" />
          <SkeletonRegion v-else-if="loading" class="resource-table-skeleton" testid="table-skeleton">
            <Skeleton v-for="n in 5" :key="n" :width="n % 2 ? '100%' : '85%'" height="1.25rem" />
          </SkeletonRegion>
          <slot v-else name="empty">
            <EmptyState :message="emptyMessage" :icon="emptyIcon" />
          </slot>
        </template>
        <Column v-if="reorderable && wide" row-reorder class="resource-table-handle" />
        <Column v-if="rowNumbers" class="resource-table-number" :show-filter-menu="false">
          <template #header>
            <span class="visually-hidden">{{ t('tableFilters.rowNumber') }}</span>
          </template>
          <template #body="{ index, frozenRow }">
            <span
              v-if="frozenRow"
              v-tooltip.top="t('tableFilters.pinned')"
              class="mdi mdi-pin-outline resource-table-pin"
              :aria-label="t('tableFilters.pinned')"
              role="img"
            />
            <template v-else>{{ first + index + 1 }}</template>
          </template>
          <template v-if="showFilterRow" #filter>
            <Button
              v-if="active"
              v-tooltip.top="t('tableFilters.clearAll', { count: active })"
              icon="mdi mdi-filter-remove-outline"
              text
              rounded
              size="small"
              :aria-label="t('tableFilters.clearAll', { count: active })"
              @click="state.clear"
            />
          </template>
        </Column>
        <Column
          v-for="column in visibleColumns"
          :key="column.field"
          :field="column.field"
          :header="column.header"
          :sortable="sortable(column)"
          :sort-field="(column.sortField ?? column.field) as string"
          :show-filter-menu="false"
          :class="[column.class, { 'resource-table-wrap': column.wrap }]"
        >
          <template #body="{ data }">
            <!-- A column with its own slot always renders that slot: Vue would show the fallback
                 for a slot that renders nothing (an empty cell), printing the raw value. -->
            <slot v-if="$slots[`body-${column.field}`]" :name="`body-${column.field}`" :data="data as T" :wide="wide" />
            <template v-else>{{ cell(data as T, column.field) }}</template>
            <div v-if="!wide && column === leadColumn && $slots.phone" class="resource-table-phone-meta">
              <slot name="phone" :data="data as T" />
            </div>
          </template>
          <template v-if="column.filter" #filter>
            <slot :name="`filter-${column.field}`" :wide="true" />
          </template>
        </Column>
        <Column v-if="reorderable && !wide" class="resource-table-move">
          <template #body="{ index }">
            <div class="resource-table-move-buttons">
              <Button
                icon="mdi mdi-arrow-up"
                text
                rounded
                :disabled="index === 0"
                :aria-label="t('tableFilters.moveUp')"
                @click.stop="move(index, -1)"
              />
              <Button
                icon="mdi mdi-arrow-down"
                text
                rounded
                :disabled="index === value.length - 1"
                :aria-label="t('tableFilters.moveDown')"
                @click.stop="move(index, 1)"
              />
            </div>
          </template>
        </Column>
        <Column v-if="hasMenu" class="resource-table-menu-cell">
          <template #body="{ data }">
            <Button
              icon="mdi mdi-dots-vertical"
              text
              rounded
              :size="wide ? 'small' : undefined"
              aria-haspopup="menu"
              :aria-label="t('tableFilters.rowActions')"
              @click.stop="openMenuFromButton($event, data as T)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
    <ContextMenu v-if="hasMenu" ref="contextMenu" :model="menuItems" @hide="onMenuHide" />
  </div>
</template>

<style scoped lang="scss">
// The placeholder rows of a first load, spaced like the small rows of the grid.
.resource-table-skeleton {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}

.resource-table-move-buttons {
  display: flex;
}

.resource-table {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.resource-table-card {
  min-width: 0;
}

// One column as wide as the card, so a tab bar or a hint in the header
// scrolls or wraps inside it instead of widening the card on a phone.
.resource-table-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.resource-table-phone-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.resource-table-phone-filters {
  display: grid;
  gap: var(--space-2);
}

.resource-table-phone-meta {
  font-size: var(--font-size-sm);
  color: var(--p-text-muted-color);
}

.resource-table-clickable {
  cursor: pointer;
}

// Cells keep to one line so a wide table scrolls sideways in its card
// instead of folding its rows; a column marked `wrap` opts out.
.resource-table-grid :deep(th),
.resource-table-grid :deep(td) {
  white-space: nowrap;
}

// On a phone the table is down to its lead column, so that column wraps
// to the screen instead of scrolling sideways.
.resource-table-stacked :deep(td) {
  white-space: normal;
  overflow-wrap: anywhere;
}

.resource-table-grid :deep(td.resource-table-wrap) {
  min-width: 16rem;
  white-space: normal;
}

.resource-table-grid :deep(.resource-table-number) {
  width: 1%;
  // The number never breaks, also on a phone where the other cells wrap.
  white-space: nowrap;
  overflow-wrap: normal;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.resource-table-grid :deep(.resource-table-handle),
.resource-table-grid :deep(.resource-table-move),
.resource-table-grid :deep(.resource-table-menu-cell) {
  width: 1%;
}

.resource-table-grid :deep(.resource-table-handle) {
  cursor: grab;
}

// From the small breakpoint up a filling table takes the rest of its page
// (a `.table-page`) and the table's body scrolls under its sticky header.
@media (min-width: $bp-sm) {
  .resource-table-fill {
    flex: 1 1 0;
    min-height: 0;
  }

  .resource-table-fill .resource-table-card {
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    min-height: 0;
  }

  .resource-table-fill .resource-table-grid {
    flex: 1 1 0;
    min-height: 0;
  }
}
.resource-table-pin {
  color: var(--p-orange-500);
}
</style>
