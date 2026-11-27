<script setup lang="ts">
/**
 * Paired instances: this instance's own identity, invitations (the link
 * shows once), accepting another instance's invitation, and the list of
 * paired instances with their versions, switches, channel status, refresh,
 * sync now and revoke, and each peer's catalogue mappings.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import PeerMappingsDialog from '@/features/admin-settings/components/PeerMappingsDialog.vue'
import PeerSwitchesDialog from '@/features/admin-settings/components/PeerSwitchesDialog.vue'
import {
  peeringApi,
  type CreatedPeerInvitation,
  type OwnInstance,
  type Peer,
  type PeerInvitation,
} from '@/features/admin-settings/api/peering'
import { channelErrorKey, formatVersions, incomingKey, missingCapabilities } from '@/features/admin-settings/peering'
import type { Schemas } from '@/core/api/generated'
import { groupsApi } from '@/features/admin-settings/api/users'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const own = ref<OwnInstance | null>(null)
const peers = ref<Peer[]>([])
const invitations = ref<PeerInvitation[]>([])
const groups = ref<Schemas['GroupResponse'][]>([])
const created = ref<CreatedPeerInvitation | null>(null)
const inviting = ref(false)
const link = ref('')
const accepting = ref(false)
const busy = ref<string | null>(null)
const editing = ref<Peer | null>(null)
const mappingsOf = ref<Peer | null>(null)
const unnotified = ref<string | null>(null)
const loaded = ref(false)

const ownCapabilities = computed(() => own.value?.capabilities ?? [])

async function load() {
  try {
    ;[own.value, peers.value, invitations.value] = await Promise.all([
      peeringApi.self(),
      peeringApi.list(),
      peeringApi.invitations(),
    ])
    loaded.value = true
  } catch (err) {
    toast.error(err)
  }
  try {
    groups.value = await groupsApi.list()
  } catch {
    // Without access to groups, only the instance-wide visibility is offered.
    groups.value = []
  }
}

async function invite() {
  inviting.value = true
  try {
    created.value = await peeringApi.invite()
    invitations.value = await peeringApi.invitations()
  } catch (err) {
    toast.error(err)
  } finally {
    inviting.value = false
  }
}

async function copyLink() {
  if (created.value) await navigator.clipboard.writeText(created.value.link)
  toast.success(t('common.done'))
}

async function accept() {
  accepting.value = true
  try {
    const peer = await peeringApi.accept(link.value.trim())
    link.value = ''
    toast.success(t('adminArea.peers.paired', { name: peer.name }))
    peers.value = await peeringApi.list()
  } catch (err) {
    toast.error(err)
  } finally {
    accepting.value = false
  }
}

function ask(message: string, action: () => Promise<unknown>) {
  confirm.require({
    message,
    header: t('common.confirm'),
    acceptProps: { label: t('common.yes'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void action()
        .then(load)
        .catch((err: unknown) => toast.error(err))
    },
  })
}

const revokeInvitation = (invitation: PeerInvitation) =>
  ask(t('adminArea.peers.revokeInvitationConfirm'), () => peeringApi.revokeInvitation(invitation.id))

const revoke = (peer: Peer) =>
  ask(t('adminArea.peers.revokeConfirm', { name: peer.name }), async () => {
    const result = await peeringApi.revoke(peer.id)
    unnotified.value = result.peer_notified ? null : peer.name
    if (result.peer_notified) toast.success(t('adminArea.peers.revoked'))
  })

async function refresh(peer: Peer) {
  busy.value = peer.id
  try {
    const updated = await peeringApi.refresh(peer.id)
    peers.value = peers.value.map((p) => (p.id === updated.id ? updated : p))
    toast.success(t('adminArea.peers.refreshed'))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

async function sync(peer: Peer) {
  busy.value = peer.id
  try {
    const updated = await peeringApi.sync(peer.id)
    peers.value = peers.value.map((p) => (p.id === updated.id ? updated : p))
    toast.success(t('adminArea.peers.syncing'))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

function saved(peer: Peer) {
  peers.value = peers.value.map((p) => (p.id === peer.id ? peer : p))
  editing.value = null
}

function groupName(id: string | null): string {
  return groups.value.find((g) => g.id === id)?.name ?? t('adminArea.peers.noGroup')
}

onMounted(() => void load())
</script>

<template>
  <div class="settings-tab">
    <h2 class="panel-title">{{ t('adminArea.peers.title') }}</h2>
    <p class="hint">{{ t('adminArea.peers.hint') }}</p>

    <dl class="readings">
      <div class="reading">
        <dt>{{ t('adminArea.peers.instanceId') }}</dt>
        <dd><code v-if="own">{{ own.instance_id }}</code><template v-else>&nbsp;</template></dd>
      </div>
      <div class="reading">
        <dt>{{ t('adminArea.peers.baseUrl') }}</dt>
        <dd>{{ own?.base_url ?? '\u00a0' }}</dd>
      </div>
      <div class="reading">
        <dt>{{ t('adminArea.peers.versions') }}</dt>
        <dd>
          <template v-if="own">
            {{ t('adminArea.peers.protocol', { versions: own.protocol_versions.join(', ') }) }}
            · {{ formatVersions(own.formats) }}
          </template>
          <template v-else>&nbsp;</template>
        </dd>
      </div>
    </dl>

    <h3 class="sub-title">{{ t('adminArea.peers.inviteTitle') }}</h3>
    <p class="hint">{{ t('adminArea.peers.inviteHint') }}</p>
    <Message v-if="created" severity="warn" :closable="true" @close="created = null">
      <p>{{ t('adminArea.peers.linkOnce', { date: formatDateTime(created.expires_at) }) }}</p>
      <code class="secret">{{ created.link }}</code>
      <Button :label="t('common.copy')" icon="mdi mdi-content-copy" text size="small" @click="copyLink" />
    </Message>
    <ul v-if="invitations.length" class="row-list">
      <li v-for="invitation in invitations" :key="invitation.id" class="row">
        <span class="row-text">
          <span>{{ t('adminArea.peers.openInvitation', { date: formatDateTime(invitation.created) }) }}</span>
          <small class="text-muted">{{ t('adminArea.peers.expires', { date: formatDateTime(invitation.expires_at) }) }}</small>
        </span>
        <Button
          v-if="canWrite"
          icon="mdi mdi-close-circle-outline"
          text
          rounded
          severity="danger"
          :aria-label="t('adminArea.peers.revokeInvitation')"
          @click="revokeInvitation(invitation)"
        />
      </li>
    </ul>
    <div v-if="canWrite">
      <Button
        :label="t('adminArea.peers.invite')"
        icon="mdi mdi-link-plus"
        :loading="inviting"
        :disabled="!loaded"
        @click="invite"
      />
    </div>

    <template v-if="canWrite">
      <h3 class="sub-title">{{ t('adminArea.peers.acceptTitle') }}</h3>
      <form class="accept-form" @submit.prevent="accept">
        <div class="field">
          <label for="peer-invitation-link">{{ t('adminArea.peers.acceptLabel') }}</label>
          <InputText
            id="peer-invitation-link"
            v-model="link"
            type="url"
            required
            fluid
            placeholder="https://…/peering/accept?code=…"
          />
          <small class="field-hint">{{ t('adminArea.peers.acceptHint') }}</small>
        </div>
        <div>
          <Button type="submit" :label="t('adminArea.peers.accept')" icon="mdi mdi-handshake-outline" :loading="accepting" :disabled="!link.trim()" />
        </div>
      </form>
    </template>

    <h3 class="sub-title">{{ t('adminArea.peers.listTitle') }}</h3>
    <Message v-if="unnotified" severity="warn" :closable="true" @close="unnotified = null">
      {{ t('adminArea.peers.revokedUnnotified', { name: unnotified }) }}
    </Message>
    <ul v-if="peers.length" class="row-list">
      <li v-for="peer in peers" :key="peer.id" class="row peer-row">
        <span class="row-text">
          <strong>{{ peer.name }}</strong>
          <small class="text-muted peer-url">{{ peer.base_url }}</small>
          <small class="text-muted">
            {{ t('adminArea.peers.appVersion', { version: peer.app_version || '–' }) }}
            · {{ t('adminArea.peers.protocol', { versions: peer.protocol_version }) }}
            · {{ formatVersions(peer.format_versions) }}
          </small>
          <small class="text-muted">
            {{ t('adminArea.peers.capabilities') }}: {{ peer.capabilities.join(', ') || t('common.none') }}
          </small>
          <small v-if="peer.status === 'active' && missingCapabilities(ownCapabilities, peer.capabilities).length" class="peer-lost">
            {{ t('adminArea.peers.lost', { capabilities: missingCapabilities(ownCapabilities, peer.capabilities).join(', ') }) }}
          </small>
          <small class="text-muted">
            {{ t('adminArea.peers.pairedAt', { date: formatDateTime(peer.paired_at) }) }}
            · {{ peer.last_contact_at ? t('adminArea.peers.lastContact', { date: formatDateTime(peer.last_contact_at) }) : t('adminArea.peers.noContact') }}
          </small>
          <template v-if="peer.status === 'active' && peer.channel">
            <small class="text-muted">
              {{ t('adminArea.peers.channelSent', { seq: peer.channel.last_sent_seq, pending: peer.channel.pending_outgoing }) }}
            </small>
            <small v-if="peer.channel.last_delivery_error" class="peer-lost">
              {{
                t(peer.channel.last_delivery_status ? 'adminArea.peers.deliveryFailedStatus' : 'adminArea.peers.deliveryFailed', {
                  date: formatDateTime(peer.channel.last_delivery_at),
                  error: t(channelErrorKey(peer.channel.last_delivery_error)),
                  status: peer.channel.last_delivery_status ?? '',
                  next: peer.channel.next_send_at ? formatDateTime(peer.channel.next_send_at) : '–',
                })
              }}
            </small>
            <small v-else-if="peer.channel.last_delivery_at" class="text-muted">
              {{ t('adminArea.peers.lastDelivery', { date: formatDateTime(peer.channel.last_delivery_at) }) }}
            </small>
            <small class="text-muted">
              {{ t('adminArea.peers.channelReceived', { seq: peer.channel.last_received_seq, pending: peer.channel.pending_incoming }) }}
              · {{ peer.channel.last_catch_up_at ? t('adminArea.peers.lastCatchUp', { date: formatDateTime(peer.channel.last_catch_up_at) }) : t('adminArea.peers.noCatchUp') }}
              <template v-if="peer.channel.last_reconcile_at">
                · {{ t('adminArea.peers.lastReconcile', { date: formatDateTime(peer.channel.last_reconcile_at) }) }}
              </template>
            </small>
            <small v-if="peer.channel.last_receive_error" class="peer-lost">
              {{ t('adminArea.peers.receiveFailed', { error: t(channelErrorKey(peer.channel.last_receive_error)) }) }}
            </small>
          </template>
          <small v-if="peer.status === 'revoked' && peer.revoked_at" class="text-muted">
            {{ t(peer.revoked_by === 'remote' ? 'adminArea.peers.revokedRemote' : 'adminArea.peers.revokedLocal', { date: formatDateTime(peer.revoked_at) }) }}
          </small>
          <small class="text-muted">
            {{ t('adminArea.peers.outgoing') }}:
            {{ peer.users_may_share ? t('adminArea.peers.usersMayShareOn') : t('adminArea.peers.usersMayShareOff') }}
          </small>
          <small class="text-muted">
            {{ t('adminArea.peers.incoming') }}:
            {{ t(incomingKey(peer)) }}
            · {{ peer.mirror_visibility === 'group' ? groupName(peer.mirror_group) : t('adminArea.peers.visibilityInstance') }}
          </small>
        </span>
        <Tag
          :value="peer.status === 'active' ? t('adminArea.peers.active') : t('adminArea.peers.revokedStatus')"
          :severity="peer.status === 'active' ? 'success' : 'secondary'"
        />
        <span class="row-actions peer-actions">
          <Button
            v-if="peer.status === 'active'"
            icon="mdi mdi-swap-horizontal"
            text
            rounded
            :aria-label="t('adminArea.mappings.open')"
            :title="t('adminArea.mappings.open')"
            :data-testid="`peer-mappings-${peer.id}`"
            @click="mappingsOf = peer"
          />
          <Button
            v-if="canWrite"
            icon="mdi mdi-tune-variant"
            text
            rounded
            :aria-label="t('adminArea.peers.switches')"
            @click="editing = peer"
          />
          <template v-if="canWrite && peer.status === 'active'">
            <Button
              icon="mdi mdi-refresh"
              text
              rounded
              :loading="busy === peer.id"
              :aria-label="t('adminArea.peers.refresh')"
              @click="refresh(peer)"
            />
            <Button
              icon="mdi mdi-sync"
              text
              rounded
              :disabled="busy === peer.id"
              :aria-label="t('adminArea.peers.sync')"
              @click="sync(peer)"
            />
            <Button
              icon="mdi mdi-link-off"
              text
              rounded
              severity="danger"
              :aria-label="t('adminArea.peers.revoke')"
              @click="revoke(peer)"
            />
          </template>
        </span>
      </li>
    </ul>
    <p v-else-if="loaded" class="empty-note">{{ t('adminArea.peers.none') }}</p>

    <PeerSwitchesDialog :peer="editing" :groups="groups" @saved="saved" @close="editing = null" />
    <PeerMappingsDialog :peer="mappingsOf" @close="mappingsOf = null" />
  </div>
</template>

<style scoped lang="scss">
.readings {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.reading {
  display: grid;
  min-width: 0;

  dt {
    font-size: var(--font-size-sm);
    color: var(--p-text-muted-color);
  }

  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
}

.sub-title {
  margin: var(--space-2) 0 0;
  font-size: var(--font-size-md);
}

.row-list {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.row-text {
  display: grid;
  min-width: 0;
}

.peer-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.peer-lost {
  color: var(--p-orange-600);
}

.peer-actions {
  grid-column: 1 / -1;
}

.secret {
  display: block;
  overflow-x: auto;
  margin: var(--space-1) 0;
}

.accept-form {
  display: grid;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .readings {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .peer-row {
    grid-template-columns: minmax(0, 1fr) auto auto;
  }

  .peer-actions {
    grid-column: auto;
  }
}
</style>
