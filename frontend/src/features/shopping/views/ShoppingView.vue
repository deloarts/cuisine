<script setup lang="ts">
/**
 * Every shopping list the user owns or was invited to, as tappable cards,
 * with the household's default list first and marked as such. Each card
 * carries its tags (household, mode, kept) at the top right, the counts of
 * what is still to buy and already in the basket with a progress bar, who
 * works on it, the last activity and, for a normal list, the day it deletes
 * itself.
 * Above them stand the notes about unused lists that deleted themselves,
 * until the user dismisses them.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import { useHousehold } from '@/shared/household/useHousehold'
import ListDialog from '@/features/shopping/components/ListDialog.vue'
import { deletionDay, deletionIsNear } from '@/features/shopping/modes'
import {
  createShoppingList,
  dismissShoppingListNote,
  listShoppingListNotes,
  listShoppingLists,
  type ShoppingListNote as ListNote,
  type ShoppingListSummary as ListSummary,
} from '@/features/shopping/api/shopping'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'
import { formatDate, formatDateTime } from '@/core/utils/dates'
import ContentCard from '@/shared/components/ContentCard.vue'

type PersonRef = Schemas['PersonRef']

const { t } = useI18n()
const router = useRouter()
const toast = useAppToast()
const { shoppingListId, load: loadHousehold } = useHousehold()

const lists = ref<ListSummary[]>([])
const notes = ref<ListNote[]>([])
const sorted = computed(() =>
  [...lists.value].sort((a, b) => Number(b.id === shoppingListId.value) - Number(a.id === shoppingListId.value)),
)
// True from the start, so the first frame shows the skeleton cards rather
// than the empty state.
const loading = ref(true)
const dialog = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    lists.value = await listShoppingLists()
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function loadNotes() {
  try {
    notes.value = await listShoppingListNotes()
  } catch {
    notes.value = []
  }
}

async function dismiss(note: ListNote) {
  try {
    await dismissShoppingListNote(note.id)
    notes.value = notes.value.filter((n) => n.id !== note.id)
  } catch (err) {
    toast.error(err)
  }
}

async function create(value: { name: string; member_ids: string[] }) {
  saving.value = true
  try {
    const created = await createShoppingList(value)
    dialog.value = false
    await router.push({ name: 'shopping-list', params: { id: created.id } })
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

// The owner and the members, everyone who works on the list.
function persons(list: ListSummary): PersonRef[] {
  return [list.owner, ...list.members].filter((p): p is PersonRef => p !== null)
}

function people(list: ListSummary): string {
  return persons(list)
    .map((p) => p.display_name)
    .join(', ')
}

function total(list: ListSummary): number {
  return list.open_count + list.checked_count
}

onMounted(() => {
  void load()
  void loadNotes()
  loadHousehold().catch(() => undefined)
})
</script>

<template>
  <section class="shopping">
    <PageHeader :title="t('nav.shopping')">
      <Button :label="t('shopping.newList')" icon="mdi mdi-plus" @click="dialog = true" />
    </PageHeader>

    <Message
      v-for="note in notes"
      :key="note.id"
      severity="info"
      icon="mdi mdi-information-outline"
      class="note"
      closable
      :close-button-props="{ 'aria-label': t('shopping.dismiss') }"
      @close="dismiss(note)"
    >
      {{ t('shopping.deletedNote', { name: note.list_name, days: note.idle_days }) }}
    </Message>

    <SkeletonRegion v-if="loading && !lists.length" class="list-cards" testid="shopping-skeleton">
      <ContentCard v-for="n in 2" :key="n" class="list-card">
        <div class="list-head">
          <Skeleton width="45%" height="1.75rem" />
          <span class="list-tags">
            <Skeleton width="5.5rem" height="1.6rem" border-radius="1rem" />
            <Skeleton width="6.5rem" height="1.6rem" border-radius="1rem" />
          </span>
        </div>
        <div class="list-stats">
          <div v-for="m in 3" :key="m" class="list-stat">
            <Skeleton width="2.5rem" height="2rem" />
            <Skeleton width="4.5rem" height="0.875rem" />
          </div>
        </div>
        <Skeleton height="0.5rem" border-radius="1rem" />
        <Skeleton width="60%" height="0.875rem" />
      </ContentCard>
    </SkeletonRegion>

    <ContentCard v-else-if="!loading && !lists.length">
      <EmptyState :message="t('shopping.noLists')" icon="mdi mdi-cart-outline">
        <Button :label="t('shopping.newList')" icon="mdi mdi-plus" @click="dialog = true" />
      </EmptyState>
    </ContentCard>

    <ul class="list-cards">
      <li v-for="list in sorted" :key="list.id">
        <RouterLink :to="{ name: 'shopping-list', params: { id: list.id } }" class="list-card card">
          <div class="list-head">
            <span class="list-name">{{ list.name }}</span>
            <span class="list-tags">
              <Tag
                v-if="list.id === shoppingListId"
                :value="t('shopping.householdList')"
                icon="mdi mdi-home-heart"
                severity="secondary"
              />
              <Tag
                :value="t(`shopping.modes.${list.mode}`)"
                :icon="list.mode === 'continuous' ? 'mdi mdi-autorenew' : 'mdi mdi-format-list-checks'"
                severity="contrast"
              />
              <Tag
                v-if="list.mode === 'normal' && list.keep"
                :value="t('shopping.kept')"
                icon="mdi mdi-pin-outline"
                severity="secondary"
              />
            </span>
          </div>

          <dl class="list-stats">
            <div class="list-stat">
              <dt>{{ t('shopping.card.toBuy') }}</dt>
              <dd>{{ list.open_count }}</dd>
            </div>
            <div class="list-stat">
              <dt>{{ t('shopping.inBasketTitle') }}</dt>
              <dd>{{ list.checked_count }}</dd>
            </div>
            <div class="list-stat">
              <dt>{{ t('shopping.card.people') }}</dt>
              <dd class="list-people">
                <span class="avatar-stack" aria-hidden="true">
                  <UserAvatar
                    v-for="person in persons(list).slice(0, 4)"
                    :key="person.id"
                    :name="person.display_name"
                    :avatar-id="person.avatar_id"
                    class="avatar-stack-item"
                  />
                </span>
                {{ persons(list).length }}
              </dd>
            </div>
          </dl>

          <div
            v-if="total(list)"
            class="list-progress"
            role="progressbar"
            :aria-label="t('shopping.card.progress')"
            :aria-valuenow="list.checked_count"
            aria-valuemin="0"
            :aria-valuemax="total(list)"
          >
            <span class="list-progress-bar" :style="{ width: `${(100 * list.checked_count) / total(list)}%` }" />
          </div>

          <div class="list-foot">
            <small class="text-muted">
              <i class="mdi mdi-clock-outline" aria-hidden="true" />
              {{ t('shopping.card.lastActivity', { date: formatDateTime(list.last_activity_at) }) }}
            </small>
            <small v-if="deletionDay(list)" class="deletes-on" :class="{ 'deletes-on--near': deletionIsNear(list) }">
              <i class="mdi mdi-timer-sand" aria-hidden="true" />
              {{ t('shopping.deletesOnShort', { date: formatDate(deletionDay(list)) }) }}
            </small>
            <small v-if="list.members.length || !list.is_owner" class="text-muted">
              <i class="mdi mdi-account-multiple-outline" aria-hidden="true" /> {{ people(list) }}
            </small>
          </div>
        </RouterLink>
      </li>
    </ul>

    <ListDialog v-model:visible="dialog" :saving="saving" is-new @submit="create" />
  </section>
</template>

<style scoped lang="scss">

.list-cards {
  display: grid;
  gap: var(--space-3);
  padding: 0;
  margin: 0;
  list-style: none;
}

.list-card {
  display: grid;
  gap: var(--space-3);
  color: inherit;
  text-decoration: none;

  &:hover,
  &:focus-visible {
    box-shadow: var(--shadow-lg);
  }
}

.list-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
}

.list-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-left: auto;
}

.list-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.list-stat {
  display: flex;
  flex-direction: column-reverse;
  gap: var(--space-1);

  dt {
    font-size: var(--font-size-sm);
    color: var(--p-text-muted-color);
  }

  dd {
    margin: 0;
    font-size: var(--font-size-2xl);
    font-weight: 700;
    line-height: 1.1;
  }
}

.list-people {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.avatar-stack {
  display: inline-flex;
}

// Each avatar after the first overlaps the one before, ringed in the card's
// background so the stack stays readable.
.avatar-stack-item {
  width: 1.75rem;
  height: 1.75rem;
  font-size: var(--font-size-xs);
  border: 2px solid var(--p-content-background);
  border-radius: 50%;

  & + & {
    margin-left: -0.5rem;
  }
}

.list-progress {
  height: 0.5rem;
  overflow: hidden;
  background: var(--p-content-border-color);
  border-radius: 1rem;
}

.list-progress-bar {
  display: block;
  height: 100%;
  background: var(--p-primary-color);
  border-radius: inherit;
  transition: width 0.2s ease;
}

.list-foot {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
}

.note {
  margin-bottom: var(--space-3);
}

.deletes-on {
  color: var(--p-text-muted-color);
}

.deletes-on--near {
  color: var(--p-orange-600);
}

.list-name {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

@media (min-width: $bp-sm) {
  .list-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
