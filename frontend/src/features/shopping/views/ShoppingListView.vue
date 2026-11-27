<script setup lang="ts">
/**
 * One shopping list, built for the phone in the shop: items grouped in aisle
 * order, a tap anywhere on a row puts it in the basket, and every change
 * anyone makes shows up on every open device through the live connection.
 * Anyone on the list switches its mode, after a dialog that explains the new
 * one: a continuous list shows what was ticked under "Recently bought" with
 * undo until the purge removes it, a normal list shows the day it deletes
 * itself and a switch to keep it.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useConfirm } from 'openvue/useconfirm'

import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useHousehold } from '@/shared/household/useHousehold'
import { contentLocaleOf } from '@/shared/cookbook/contentLocale'
import IngredientOption from '@/shared/cookbook/IngredientOption.vue'
import type { IngredientResponse } from '@/shared/cookbook/types'
import UnitSelect from '@/shared/cookbook/UnitSelect.vue'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'
import { useKeepScreenOn } from '@/shared/composables/useKeepScreenOn'
import AddRecipeDialog, { type AddRecipeValue } from '@/features/shopping/components/AddRecipeDialog.vue'
import ListDialog from '@/features/shopping/components/ListDialog.vue'
import ShoppingListSkeleton from '@/features/shopping/components/ShoppingListSkeleton.vue'
import {
  amountLabel,
  CHECKED,
  groupItems,
  isBoughtSubRecipe,
  itemSource,
  shownRecipes,
  UNCATEGORISED,
  type ItemSource,
  type ShoppingItem,
} from '@/features/shopping/grouping'
import { useShoppingListEvents } from '@/features/shopping/liveEvents'
import {
  deletionDay,
  deletionIsNear,
  leavesAt,
  recentlyBought,
  undoPurchase,
  type ShoppingListMode,
} from '@/features/shopping/modes'
import {
  addRecipeToShoppingList,
  addShoppingItem,
  clearCheckedItems,
  deleteShoppingList,
  getShoppingList,
  leaveShoppingList,
  removeShoppingItem,
  searchIngredients as findIngredients,
  updateShoppingItem,
  updateShoppingList,
  type ShoppingList,
} from '@/features/shopping/api/shopping'
import { useAppToast } from '@/core/composables/useAppToast'
import { formatDate } from '@/core/utils/dates'
import { formatTimeParts } from '@/core/utils/displayFormats'
import ContentCard from '@/shared/components/ContentCard.vue'


const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useAppToast()
const confirm = useConfirm()
// The phone stays on while the list is open in the shop.
useKeepScreenOn()
const resources = useCookbookResources()
const { shoppingListId: householdListId, load: loadHousehold } = useHousehold()

const listId = computed(() => (typeof route.params.id === 'string' ? route.params.id : null))
// The household's default list belongs to every member automatically, so it
// is neither shared, left nor deleted by hand.
const isHouseholdList = computed(() => listId.value !== null && listId.value === householdListId.value)
const list = ref<ShoppingList | null>(null)
const loading = ref(false)

const newItem = ref<IngredientResponse | string | null>(null)
const suggestions = ref<IngredientResponse[]>([])
const amount = ref<number | null>(null)
const unitId = ref<string | null>(null)
const adding = ref(false)

const listDialog = ref(false)
const recipeDialog = ref(false)
const saving = ref(false)

const isContinuous = computed(() => list.value?.mode === 'continuous')
const modeOptions = computed(() =>
  (['continuous', 'normal'] as const).map((value) => ({ value, label: t(`shopping.modes.${value}`) })),
)
const savingMode = ref(false)
// A normal list outside the household that would delete itself, or one a
// member already keeps, offers the keep switch.
const offersKeep = computed(
  () => list.value?.mode === 'normal' && !isHouseholdList.value && (list.value.deletes_on !== null || list.value.keep),
)
const deletesOn = computed(() => (list.value ? deletionDay(list.value) : null))

// The items that were ticked when the list opened. Only these sit in the
// basket section: an item ticked while the list is open keeps its place in
// its aisle, so the rows don't jump under the shopper's thumb, and joins the
// basket the next time the list opens.
const basket = ref(new Set<string>())

const groups = computed(() => {
  const all = groupItems(list.value?.items ?? [], (item) => item.checked && basket.value.has(item.id))
  if (!isContinuous.value) return all
  // The basket of a continuous list is "Recently bought", newest first.
  return all.map((g) => (g.key === CHECKED ? { ...g, items: recentlyBought(g.items) } : g))
})
const numberLocale = computed(() => contentLocaleOf(locale.value))

/** An item's name; a bought sub-recipe the viewer cannot see has none of its own. */
function itemName(item: ShoppingItem): string {
  return item.name || (isBoughtSubRecipe(item) ? t('shopping.hiddenRecipe') : '')
}

/**
 * "for Lasagna sheets, in Lasagna" and the like, or empty for a free item.
 * An item several recipes want names them all ("for Coq au vin, Red
 * cabbage"); from four on the line names two and counts the rest ("+2"),
 * and `all` holds every name for the tooltip.
 */
function sourceLine(item: ShoppingItem): { text: string; all: string } | null {
  const source = itemSource(item)
  if (!source) return null
  const title = (value: string | null) => value ?? t('shopping.hiddenRecipe')
  const names = source.recipes.map(title)
  const { shown, more } = shownRecipes(names)
  const recipe = more ? t('shopping.moreRecipes', { recipes: shown.join(', '), count: more }) : shown.join(', ')
  return { text: sourceText(source, recipe, title), all: more ? names.join(', ') : '' }
}

function sourceText(source: ItemSource, recipe: string, title: (value: string | null) => string): string {
  if (source.kind === 'recipe') return t('shopping.fromRecipe', { recipe })
  const via = source.via.map(title).join(' › ')
  if (source.kind === 'bought') {
    return via ? t('shopping.boughtVia', { via, recipe }) : t('shopping.bought', { recipe })
  }
  const sub = title(source.sub)
  return via ? t('shopping.fromSubRecipeVia', { sub, via, recipe }) : t('shopping.fromSubRecipe', { sub, recipe })
}

/** Who ticked the item and when it leaves, after the source line. */
function metaLine(item: ShoppingItem): string {
  const parts: string[] = []
  if (item.checked && item.checked_by) parts.push(item.checked_by.display_name)
  const leaves = isContinuous.value && list.value ? leavesAt(item, list.value.bought_window_hours) : null
  if (leaves) parts.push(t('shopping.leavesAt', { time: formatTimeParts(leaves) }))
  return parts.filter(Boolean).join(' · ')
}

function groupTitle(key: string, name: string): string {
  if (key === CHECKED) return isContinuous.value ? t('shopping.recentlyBought') : t('shopping.inBasketTitle')
  if (key === UNCATEGORISED) return t('shopping.otherItems')
  return name
}

async function load() {
  if (!listId.value) return
  try {
    list.value = await getShoppingList(listId.value)
    forgetUnchecked()
  } catch (err) {
    toast.error(err)
  }
}

const { connected } = useShoppingListEvents(listId, {
  onRefetch: () => void load(),
  onDeleted: () => {
    toast.success(t('shopping.deletedElsewhere'))
    void router.push({ name: 'shopping' })
  },
})

async function searchIngredients(event: { query: string }) {
  try {
    suggestions.value = (await findIngredients(event.query, 8)).items
  } catch {
    suggestions.value = []
  }
}

async function addItem() {
  const value = newItem.value
  if (!listId.value || !value || (typeof value === 'string' && !value.trim())) return
  adding.value = true
  try {
    list.value = await addShoppingItem(
      listId.value,
      typeof value === 'string'
        ? { text: value.trim(), amount: amount.value, unit_id: unitId.value }
        : { ingredient_id: value.id, text: '', amount: amount.value, unit_id: unitId.value },
    )
    newItem.value = null
    amount.value = null
    unitId.value = null
  } catch (err) {
    toast.error(err)
  } finally {
    adding.value = false
  }
}

/** Drops the items no longer ticked, so ticking one again keeps it in place. */
function forgetUnchecked() {
  const ticked = new Set((list.value?.items ?? []).filter((i) => i.checked).map((i) => i.id))
  basket.value = new Set([...basket.value].filter((id) => ticked.has(id)))
}

async function toggle(item: ShoppingItem) {
  if (!listId.value) return
  item.checked = !item.checked
  try {
    list.value = await updateShoppingItem(listId.value, item.id, { checked: item.checked })
    forgetUnchecked()
  } catch (err) {
    item.checked = !item.checked
    toast.error(err)
  }
}

/** Puts a recently bought item back on the list, shown at once and rolled back on failure. */
async function undo(item: ShoppingItem) {
  if (!listId.value || !list.value) return
  const before = list.value
  list.value = { ...before, items: undoPurchase(before.items, item.id) }
  try {
    list.value = await updateShoppingItem(listId.value, item.id, { checked: false })
    forgetUnchecked()
  } catch (err) {
    list.value = before
    toast.error(err)
  }
}

async function changeList(body: { mode?: ShoppingListMode; keep?: boolean }) {
  if (!listId.value) return
  savingMode.value = true
  try {
    list.value = await updateShoppingList(listId.value, body)
  } catch (err) {
    toast.error(err)
  } finally {
    savingMode.value = false
  }
}

/** Explains the chosen mode and switches only once the user confirms. */
function setMode(mode: ShoppingListMode | null) {
  const current = list.value
  if (!mode || !current || mode === current.mode) return
  confirm.require({
    header: t('shopping.modeSwitchTitle', { mode: t(`shopping.modes.${mode}`) }),
    message: t(`shopping.modeHints.${mode}`, { hours: current.bought_window_hours }),
    acceptProps: { label: t('shopping.modeSwitch') },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void changeList({ mode }),
  })
}

async function removeItem(item: ShoppingItem) {
  if (!listId.value) return
  try {
    list.value = await removeShoppingItem(listId.value, item.id)
  } catch (err) {
    toast.error(err)
  }
}

async function clearChecked() {
  if (!listId.value) return
  try {
    const { removed } = await clearCheckedItems(listId.value)
    toast.success(t('shopping.cleared', { count: removed }))
    await load()
  } catch (err) {
    toast.error(err)
  }
}

async function addRecipe(value: AddRecipeValue) {
  if (!listId.value) return
  saving.value = true
  try {
    const { added } = await addRecipeToShoppingList(listId.value, value)
    recipeDialog.value = false
    toast.success(t('shopping.recipeAdded', { count: added }))
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function updateList(value: { name: string; member_ids: string[] }) {
  if (!listId.value) return
  saving.value = true
  try {
    await updateShoppingList(listId.value, value)
    listDialog.value = false
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

function ask(message: string, action: () => Promise<unknown>) {
  confirm.require({
    message,
    header: t('common.confirm'),
    acceptProps: { label: t('common.yes'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void (async () => {
        try {
          await action()
          await router.push({ name: 'shopping' })
        } catch (err) {
          toast.error(err)
        }
      })()
    },
  })
}

const deleteList = () =>
  ask(t('shopping.deleteConfirm', { name: list.value?.name ?? '' }), () =>
    deleteShoppingList(listId.value ?? ''),
  )
const leaveList = () =>
  ask(t('shopping.leaveConfirm', { name: list.value?.name ?? '' }), () =>
    leaveShoppingList(listId.value ?? ''),
  )

onMounted(async () => {
  loading.value = true
  await load()
  basket.value = new Set((list.value?.items ?? []).filter((i) => i.checked).map((i) => i.id))
  loading.value = false
  resources.load().catch((err: unknown) => toast.error(err))
  loadHousehold().catch(() => undefined)
})
</script>

<template>
  <section class="shopping-list">
    <PageHeader :title="list?.name ?? t('nav.shopping')">
      <template #title-end>
        <Tag v-if="isHouseholdList" :value="t('shopping.householdList')" icon="mdi mdi-home-heart" severity="secondary" />
      </template>
      <span class="live" :class="{ 'live--on': connected }" role="status">
        <i class="mdi" :class="connected ? 'mdi-access-point' : 'mdi-access-point-off'" aria-hidden="true" />
        {{ connected ? t('shopping.live') : t('shopping.offline') }}
      </span>
    </PageHeader>

    <ShoppingListSkeleton v-if="loading && !list" />

    <div v-if="list" class="toolbar">
      <Button :label="t('shopping.addRecipe')" icon="mdi mdi-book-plus-outline" outlined @click="recipeDialog = true" />
      <SelectButton
        :model-value="list.mode"
        :options="modeOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        :disabled="savingMode"
        :aria-label="t('shopping.mode')"
        @update:model-value="setMode"
      />
      <Button
        v-if="list.checked_count"
        :label="t('shopping.clearChecked')"
        icon="mdi mdi-broom"
        text
        @click="clearChecked"
      />
      <Button
        v-if="list.is_owner && !isHouseholdList"
        :label="t('shopping.share')"
        icon="mdi mdi-account-multiple-plus-outline"
        text
        @click="listDialog = true"
      />
      <template v-if="!isHouseholdList">
        <Button v-if="list.is_owner" :label="t('common.delete')" icon="mdi mdi-delete-outline" text severity="danger" @click="deleteList" />
        <Button v-else :label="t('shopping.leave')" icon="mdi mdi-exit-run" text severity="danger" @click="leaveList" />
      </template>
    </div>

    <ContentCard v-if="list && (deletesOn || offersKeep)" class="mode-bar">
      <Message
        v-if="deletesOn"
        :severity="deletionIsNear(list) ? 'warn' : 'secondary'"
        icon="mdi mdi-timer-sand"
        size="small"
        :closable="false"
      >
        {{ t('shopping.deletesOn', { date: formatDate(deletesOn) }) }}
      </Message>
      <div v-if="offersKeep" class="keep-row">
        <ToggleSwitch
          :model-value="list.keep"
          input-id="shopping-keep"
          :disabled="savingMode"
          @update:model-value="(keep: boolean) => changeList({ keep })"
        />
        <label for="shopping-keep">{{ t('shopping.keepList') }}</label>
        <small class="mode-hint keep-hint">{{ t('shopping.keepHint') }}</small>
      </div>
    </ContentCard>

    <ContentCard as="form" v-if="list" class="add-bar" @submit.prevent="addItem">
      <div class="add-row">
        <AutoComplete
          v-model="newItem"
          class="add-entry"
          input-id="shopping-new"
          :suggestions="suggestions"
          option-label="name"
          :placeholder="t('shopping.addPlaceholder')"
          :aria-label="t('shopping.addPlaceholder')"
          fluid
          @complete="searchIngredients"
        >
          <template #option="{ option }">
            <IngredientOption :ingredient="option" :meta="['category']" />
          </template>
        </AutoComplete>
        <InputNumber
          v-model="amount"
          :aria-label="t('shopping.amount')"
          :placeholder="t('shopping.amount')"
          :min="0"
          :max-fraction-digits="2"
          fluid
          class="add-amount"
        />
        <UnitSelect
          v-model="unitId"
          :units="resources.units.value"
          :placeholder="t('shopping.unit')"
          :aria-label="t('shopping.unit')"
          show-clear
          fluid
          class="add-unit"
        />
        <Button type="submit" icon="mdi mdi-plus" :aria-label="t('shopping.add')" :loading="adding" class="add-submit" />
      </div>
    </ContentCard>

    <ContentCard v-if="list && !list.items.length">
      <EmptyState :message="t('shopping.emptyList')" icon="mdi mdi-cart-outline" />
    </ContentCard>

    <div v-for="group in groups" :key="group.key" class="group">
      <h3 class="group-title">{{ groupTitle(group.key, group.name) }}</h3>
      <p v-if="group.key === CHECKED && isContinuous" class="group-hint">
        {{ t('shopping.recentlyBoughtHint', { hours: list?.bought_window_hours ?? 0 }) }}
      </p>
      <ContentCard as="ul" class="items">
        <li v-for="item in group.items" :key="item.id" class="item" :class="{ 'item--checked': item.checked }">
          <button
            type="button"
            class="item-toggle"
            :aria-pressed="item.checked"
            :aria-label="item.checked ? t('shopping.uncheck', { name: itemName(item) }) : t('shopping.check', { name: itemName(item) })"
            @click="toggle(item)"
          >
            <i class="mdi item-box" :class="item.checked ? 'mdi-checkbox-marked-circle' : 'mdi-checkbox-blank-circle-outline'" aria-hidden="true" />
            <span class="item-text">
              <span class="item-name">
                <strong v-if="amountLabel(item, numberLocale)" class="item-amount" data-testid="item-amount">
                  {{ amountLabel(item, numberLocale) }}
                </strong>
                <i v-if="isBoughtSubRecipe(item)" class="mdi mdi-book-open-page-variant-outline" aria-hidden="true" />
                {{ itemName(item) }}
                <i
                  v-if="item.has_warning"
                  v-tooltip="t('shopping.warning')"
                  class="mdi mdi-alert-circle warning"
                  :aria-label="t('shopping.warning')"
                />
              </span>
              <small v-if="sourceLine(item) || metaLine(item)" class="item-meta">
                <span
                  v-if="sourceLine(item)"
                  v-tooltip.bottom="sourceLine(item)?.all || null"
                  class="item-source"
                  data-testid="item-source"
                >{{ sourceLine(item)?.text }}</span>
                <template v-if="sourceLine(item) && metaLine(item)"> · </template>
                {{ metaLine(item) }}
              </small>
            </span>
          </button>
          <Button
            v-if="item.checked && isContinuous"
            :label="t('shopping.undo')"
            icon="mdi mdi-undo"
            text
            size="small"
            :aria-label="t('shopping.undoLabel', { name: itemName(item) })"
            @click="undo(item)"
          />
          <Button
            v-else
            icon="mdi mdi-close"
            text
            rounded
            severity="secondary"
            :aria-label="t('shopping.remove', { name: itemName(item) })"
            @click="removeItem(item)"
          />
        </li>
      </ContentCard>
    </div>

    <ListDialog
      v-if="list"
      v-model:visible="listDialog"
      :name="list.name"
      :member-ids="list.members.map((m) => m.id)"
      :saving="saving"
      :is-new="false"
      @submit="updateList"
    />
    <AddRecipeDialog v-model:visible="recipeDialog" :saving="saving" @submit="addRecipe" />
  </section>
</template>

<style scoped lang="scss">

.live {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--p-text-muted-color);
}

.live--on {
  color: var(--p-green-600);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.mode-bar {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.mode-hint,
.group-hint {
  color: var(--p-text-muted-color);
}

.group-hint {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-sm);
}

.keep-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.keep-hint {
  flex-basis: 100%;
}

.add-bar {
  margin-bottom: var(--space-4);
}

// On a phone the amount and unit sit under the entry so it keeps its width;
// from a tablet on the entry, a narrow amount, the unit and the add button
// share one row.
.add-row {
  display: grid;
  grid-template-columns: 5.5rem minmax(0, 1fr) auto;
  grid-template-areas:
    'entry entry submit'
    'amount unit .';
  align-items: center;
  gap: var(--space-2);
}

.add-entry {
  grid-area: entry;
}

.add-amount {
  grid-area: amount;
}

.add-unit {
  grid-area: unit;
}

.add-submit {
  grid-area: submit;
}

@media (min-width: $bp-sm) {
  .add-row {
    grid-template-columns: minmax(0, 1fr) 5.5rem 8rem auto;
    grid-template-areas: 'entry amount unit submit';
  }
}

.group {
  margin-bottom: var(--space-4);
}

.group-title {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-md);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--p-text-muted-color);
}

.items {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

// The check circle gets room on both sides, so it reads as its own target.
.item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding-inline: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);

  &:last-child {
    border-bottom: 0;
  }
}

.item-toggle {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  min-height: 3rem;
  padding: var(--space-2) 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.item-box {
  padding-inline: var(--space-2);
  font-size: var(--font-size-2xl);
  color: var(--p-primary-color);
}

.item-text {
  display: grid;
  min-width: 0;
}

// The amount and unit lead the name in bold ("500 g Mehl"); a long name
// wraps under them while the amount itself never breaks.
.item-name {
  font-size: var(--font-size-lg);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.item-amount {
  margin-inline-end: var(--space-1);
  font-weight: 700;
  white-space: nowrap;
}

.item-meta {
  color: var(--p-text-muted-color);
}

.warning {
  color: var(--p-red-500);
}

.item--checked .item-amount {
  font-weight: 600;
}

.item--checked .item-name {
  font-weight: 400;
  text-decoration: line-through;
  color: var(--p-text-muted-color);
}
</style>
