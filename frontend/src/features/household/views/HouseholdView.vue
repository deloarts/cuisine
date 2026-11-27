<script setup lang="ts">
/**
 * The user's household: the people who share a meal plan and a default
 * shopping list. Without one, the page shows the invitations to answer and
 * offers to start a household; inside one, it lists the members and open
 * invitations, invites more people, renames it and leaves it.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import EmptyState from '@/shared/components/EmptyState.vue'
import PageHeader from '@/shared/components/PageHeader.vue'
import PersonSelect from '@/shared/components/PersonSelect.vue'
import ListItemSkeleton from '@/shared/components/skeleton/ListItemSkeleton.vue'
import SkeletonLines from '@/shared/components/skeleton/SkeletonLines.vue'
import SkeletonRegion from '@/shared/components/skeleton/SkeletonRegion.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import { useHousehold } from '@/shared/household/useHousehold'
import {
  acceptInvitation,
  createHousehold,
  declineInvitation,
  directory,
  inviteToHousehold,
  leaveHousehold,
  receivedInvitations,
  renameHousehold,
  revokeInvitation,
} from '@/features/household/api/households'
import {
  householdPhase,
  invitableUsers,
  leavingDissolves,
  sortedInvitations,
  type DirectoryUser,
  type ReceivedInvitation,
} from '@/features/household/householdState'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDate } from '@/core/utils/dates'
import ContentCard from '@/shared/components/ContentCard.vue'

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const currentUser = useCurrentUserStore()
const { household, load, reload, set } = useHousehold()

const received = ref<ReceivedInvitation[]>([])
const people = ref<DirectoryUser[]>([])
const loading = ref(true)
const busy = ref(false)

const newName = ref('')
const renaming = ref(false)
const renameValue = ref('')
const invitee = ref<string | null>(null)

const phase = computed(() => householdPhase(household.value, received.value))
const invitations = computed(() => sortedInvitations(received.value))
const candidates = computed(() =>
  household.value ? invitableUsers(people.value, household.value, currentUser.user?.id ?? null) : [],
)

async function refresh() {
  try {
    const [, mine] = await Promise.all([reload(), receivedInvitations()])
    received.value = mine
  } catch (err) {
    toast.error(err)
  }
}

/** Runs one change with the page locked, then shows what the backend says now. */
async function act(action: () => Promise<unknown>, success: string) {
  busy.value = true
  try {
    await action()
    toast.success(success)
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
    await refresh()
  }
}

function create() {
  const name = newName.value.trim()
  if (!name) return
  void act(async () => {
    set(await createHousehold(name))
    newName.value = ''
  }, t('household.created'))
}

function accept(invitation: ReceivedInvitation) {
  void act(async () => set(await acceptInvitation(invitation.id)), t('household.joined', { name: invitation.household.name }))
}

function decline(invitation: ReceivedInvitation) {
  void act(() => declineInvitation(invitation.id), t('household.declined'))
}

function startRename() {
  renameValue.value = household.value?.name ?? ''
  renaming.value = true
}

function rename() {
  const name = renameValue.value.trim()
  if (!name) return
  void act(async () => {
    set(await renameHousehold(name))
    renaming.value = false
  }, t('common.saved'))
}

function invite() {
  const id = invitee.value
  if (!id) return
  void act(async () => {
    await inviteToHousehold(id)
    invitee.value = null
  }, t('household.invited'))
}

function revoke(id: string) {
  void act(() => revokeInvitation(id), t('household.revoked'))
}

function leave() {
  const h = household.value
  if (!h) return
  confirm.require({
    header: t('household.leave'),
    message: leavingDissolves(h) ? t('household.leaveLast', { name: h.name }) : t('household.leaveConfirm', { name: h.name }),
    acceptProps: { label: t('household.leave'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void act(async () => {
      await leaveHousehold()
      set(null)
    }, t('household.left')),
  })
}

onMounted(async () => {
  try {
    const [, mine, everyone] = await Promise.all([load(), receivedInvitations(), directory()])
    received.value = mine
    people.value = everyone
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="household" :aria-busy="loading">
    <PageHeader :title="household?.name ?? t('nav.household')">
      <Button
        v-if="household"
        :label="t('household.rename')"
        icon="mdi mdi-pencil"
        text
        :disabled="busy"
        @click="startRename"
      />
    </PageHeader>

    <SkeletonRegion v-if="loading" class="household-grid" testid="household-skeleton">
      <ContentCard class="stack">
        <Skeleton width="40%" height="1.25rem" />
        <ul class="people">
          <li v-for="n in 3" :key="n" class="person">
            <ListItemSkeleton thumb="2rem" round :lines="1" />
          </li>
        </ul>
        <SkeletonLines :lines="2" />
      </ContentCard>
      <ContentCard class="stack">
        <Skeleton width="50%" height="1.25rem" />
        <div class="invite-form">
          <Skeleton height="2.75rem" />
          <Skeleton width="9rem" height="2.75rem" />
        </div>
        <SkeletonLines :lines="2" />
      </ContentCard>
    </SkeletonRegion>

    <template v-else>
      <!-- Inside a household -->
      <div v-if="phase === 'member' && household" class="household-grid">
        <ContentCard class="stack">
          <h2 class="panel-title">{{ t('household.members') }}</h2>
          <ul class="people">
            <li v-for="member in household.members" :key="member.id" class="person">
              <UserAvatar class="member-avatar" :name="member.display_name" :avatar-id="member.avatar_id" />
              <span>{{ member.display_name }}</span>
              <Tag v-if="member.id === currentUser.user?.id" :value="t('household.you')" severity="secondary" />
            </li>
          </ul>
          <p class="hint">{{ t('household.sharedHint') }}</p>
          <div class="links">
            <RouterLink :to="{ name: 'meal-plan' }" class="link">
              <i class="mdi mdi-calendar-week-outline" aria-hidden="true" /> {{ t('household.toMealPlan') }}
            </RouterLink>
            <RouterLink
              v-if="household.shopping_list_id"
              :to="{ name: 'shopping-list', params: { id: household.shopping_list_id } }"
              class="link"
            >
              <i class="mdi mdi-cart-outline" aria-hidden="true" /> {{ t('household.toList') }}
            </RouterLink>
          </div>
        </ContentCard>

        <ContentCard class="stack">
          <h2 class="panel-title">{{ t('household.invite') }}</h2>
          <form class="invite-form" @submit.prevent="invite">
            <label id="household-invitee-label" for="household-invitee" class="visually-hidden">
              {{ t('household.invitee') }}
            </label>
            <PersonSelect
              id="household-invitee"
              v-model="invitee"
              :people="candidates"
              :placeholder="t('household.invitee')"
              aria-labelledby="household-invitee-label"
              :empty-message="t('household.nobodyLeft')"
              filter
              fluid
            />
            <Button type="submit" :label="t('household.sendInvite')" icon="mdi mdi-email-fast-outline" :disabled="!invitee || busy" />
          </form>
          <p class="hint">{{ t('household.inviteHint') }}</p>

          <h3 class="sub-title">{{ t('household.pending') }}</h3>
          <p v-if="!household.invitations.length" class="hint">{{ t('household.noPending') }}</p>
          <ul v-else class="people">
            <li v-for="sent in household.invitations" :key="sent.id" class="person">
              <i class="mdi mdi-email-outline" aria-hidden="true" />
              <span>
                {{ sent.invitee?.display_name ?? t('household.formerMember') }}
                <small class="text-muted">{{ t('household.since', { date: formatDate(sent.created) }) }}</small>
              </span>
              <Button
                icon="mdi mdi-close"
                text
                rounded
                severity="secondary"
                :aria-label="t('household.revoke', { name: sent.invitee?.display_name ?? '' })"
                :disabled="busy"
                @click="revoke(sent.id)"
              />
            </li>
          </ul>
        </ContentCard>

        <ContentCard class="stack">
          <h2 class="panel-title">{{ t('household.leave') }}</h2>
          <p class="hint">{{ leavingDissolves(household) ? t('household.leaveLastHint') : t('household.leaveHint') }}</p>
          <p v-if="received.length" class="hint">{{ t('household.otherInvitations', { count: received.length }, received.length) }}</p>
          <div>
            <Button :label="t('household.leave')" icon="mdi mdi-exit-run" severity="danger" outlined :disabled="busy" @click="leave" />
          </div>
        </ContentCard>
      </div>

      <!-- Not in a household -->
      <div v-else class="household-grid">
        <ContentCard v-if="phase === 'invited'" class="stack">
          <h2 class="panel-title">{{ t('household.invitations') }}</h2>
          <ul class="people">
            <li v-for="invitation in invitations" :key="invitation.id" class="invitation">
              <span class="invitation-text">
                <strong>{{ invitation.household.name }}</strong>
                <small class="text-muted">
                  {{
                    invitation.inviter
                      ? t('household.invitedBy', { name: invitation.inviter.display_name, date: formatDate(invitation.created) })
                      : formatDate(invitation.created)
                  }}
                </small>
              </span>
              <span class="row-actions">
                <Button :label="t('household.accept')" icon="mdi mdi-check" size="small" :disabled="busy" @click="accept(invitation)" />
                <Button
                  :label="t('household.decline')"
                  icon="mdi mdi-close"
                  size="small"
                  text
                  severity="secondary"
                  :disabled="busy"
                  @click="decline(invitation)"
                />
              </span>
            </li>
          </ul>
          <p class="hint">{{ t('household.acceptHint') }}</p>
        </ContentCard>

        <ContentCard class="stack">
          <EmptyState v-if="phase === 'alone'" :message="t('household.none')" icon="mdi mdi-home-heart" />
          <h2 class="panel-title">{{ t('household.start') }}</h2>
          <p class="hint">{{ t('household.startHint') }}</p>
          <form class="invite-form" @submit.prevent="create">
            <label for="household-name" class="visually-hidden">{{ t('household.name') }}</label>
            <InputText id="household-name" v-model="newName" :placeholder="t('household.namePlaceholder')" maxlength="100" fluid />
            <Button type="submit" :label="t('household.create')" icon="mdi mdi-home-plus-outline" :disabled="!newName.trim() || busy" />
          </form>
        </ContentCard>
      </div>
    </template>

    <Dialog v-model:visible="renaming" modal :header="t('household.rename')" class="rename-dialog">
      <form class="stack" @submit.prevent="rename">
        <div class="field">
          <label for="household-rename">{{ t('household.name') }}</label>
          <InputText id="household-rename" v-model="renameValue" maxlength="100" fluid />
        </div>
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="renaming = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :disabled="!renameValue.trim() || busy" />
        </div>
      </form>
    </Dialog>
  </section>
</template>

<style scoped lang="scss">
.household-grid {
  display: grid;
  gap: var(--space-3);
}

.stack {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.people {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.person {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;

  > span {
    display: grid;
    flex: 1;
  }

  > .member-avatar {
    --avatar-size: 2rem;

    flex: 0 0 auto;
    place-items: center;
  }
}

.invitation {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--p-content-border-color);

  &:last-child {
    border-bottom: 0;
  }
}

.invitation-text {
  display: grid;
}

.links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 2.75rem;
  color: var(--p-primary-color);
  text-decoration: none;
}

.invite-form {
  display: grid;
  gap: var(--space-2);
}

.sub-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.rename-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .invite-form {
    grid-template-columns: minmax(0, 1fr) auto;
  }
}

@media (min-width: $bp-lg) {
  .household-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
