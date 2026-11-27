<script setup lang="ts">
/**
 * The per-peer switches: whether anything goes to the paired instance, what
 * is accepted from it, who here sees what it shares, and whether its recipes
 * are taken in at once ("sync all"). Switching "sync all" on offers once to
 * accept every recipe of the peer that waits now, with the same automatic
 * decisions; rejected recipes stay rejected.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import {
  incomingApi,
  peeringApi,
  type Peer,
  type PeerSwitches,
} from '@/features/admin-settings/api/peering'
import { switchesComplete, switchesOf, syncAllSwitchedOn } from '@/features/admin-settings/peering'
import type { Schemas } from '@/core/api/generated'
import { useAppToast } from '@/core/composables/useAppToast'

const props = defineProps<{ peer: Peer | null; groups: Schemas['GroupResponse'][] }>()
const emit = defineEmits<{ saved: [peer: Peer]; close: [] }>()

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()

const form = ref<PeerSwitches | null>(null)
const saving = ref(false)
const visible = computed({
  get: () => props.peer !== null,
  set: (open: boolean) => {
    if (!open) emit('close')
  },
})
const visibilities = computed(() => [
  { value: 'instance', label: t('adminArea.peers.visibilityInstance') },
  { value: 'group', label: t('adminArea.peers.visibilityGroup') },
])

watch(
  () => props.peer,
  (peer) => {
    form.value = peer ? switchesOf(peer) : null
  },
  { immediate: true },
)

// Asks once whether the recipes that wait from the peer should be accepted
// now, since "sync all" takes in only what arrives from now on.
async function offerWaiting(peer: Peer) {
  const waiting = (await incomingApi.list('pending')).filter((i) => i.peer.id === peer.id).length
  if (!waiting) return
  confirm.require({
    message: t('adminArea.peers.acceptWaitingConfirm', { count: waiting, name: peer.name }, waiting),
    header: t('adminArea.peers.acceptWaitingHeader'),
    acceptProps: { label: t('adminArea.peers.acceptWaiting') },
    rejectProps: { label: t('adminArea.peers.acceptWaitingLater'), text: true },
    accept: () => {
      void peeringApi
        .acceptWaiting(peer.id)
        .then((done) =>
          toast.success(t('adminArea.peers.acceptedWaiting', { count: done.accepted }, done.accepted)),
        )
        .catch((err: unknown) => toast.error(err))
    },
  })
}

async function save() {
  if (!props.peer || !form.value) return
  const before = props.peer
  saving.value = true
  try {
    const body = { ...form.value, mirror_group: form.value.mirror_visibility === 'group' ? form.value.mirror_group : null }
    const saved = await peeringApi.saveSwitches(before.id, body)
    emit('saved', saved)
    toast.success(t('common.saved'))
    if (syncAllSwitchedOn(before, saved)) await offerWaiting(saved)
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('adminArea.peers.switchesOf', { name: peer?.name ?? '' })"
    class="switches-dialog"
  >
    <form v-if="form" class="switches-form" @submit.prevent="save">
      <p class="hint">{{ t('adminArea.peers.switchesHint') }}</p>
      <fieldset class="switch-group">
        <legend class="field-label">{{ t('adminArea.peers.outgoing') }}</legend>
        <div class="switch">
          <ToggleSwitch v-model="form.users_may_share" input-id="peer-users-may-share" />
          <label for="peer-users-may-share" class="switch-label">
            <span>{{ t('adminArea.peers.usersMayShare') }}</span>
            <small class="field-hint">{{ t('adminArea.peers.usersMayShareHint') }}</small>
          </label>
        </div>
      </fieldset>
      <fieldset class="switch-group">
        <legend class="field-label">{{ t('adminArea.peers.incoming') }}</legend>
        <div class="switch">
          <ToggleSwitch v-model="form.accept_incoming" input-id="peer-accept-incoming" />
          <label for="peer-accept-incoming" class="switch-label">
            <span>{{ t('adminArea.peers.acceptIncoming') }}</span>
            <small class="field-hint">{{ t('adminArea.peers.acceptIncomingHint') }}</small>
          </label>
        </div>
        <div class="switch">
          <ToggleSwitch
            v-model="form.sync_all"
            input-id="peer-sync-all"
            :disabled="!form.accept_incoming"
          />
          <label for="peer-sync-all" class="switch-label">
            <span>{{ t('adminArea.peers.syncAll') }}</span>
            <small class="field-hint">{{ t('adminArea.peers.syncAllHint') }}</small>
          </label>
        </div>
        <div class="field">
          <label id="peer-visibility-label" for="peer-visibility">{{ t('adminArea.peers.mirrorVisibility') }}</label>
          <Select
            id="peer-visibility"
            v-model="form.mirror_visibility"
            :options="visibilities"
            option-label="label"
            option-value="value"
            aria-labelledby="peer-visibility-label"
            fluid
          />
          <small class="field-hint">{{ t('adminArea.peers.mirrorVisibilityHint') }}</small>
        </div>
        <div v-if="form.mirror_visibility === 'group'" class="field">
          <label id="peer-group-label" for="peer-group">{{ t('adminArea.peers.mirrorGroup') }}</label>
          <Select
            id="peer-group"
            v-model="form.mirror_group"
            :options="groups"
            option-label="name"
            option-value="id"
            aria-labelledby="peer-group-label"
            :placeholder="t('adminArea.peers.pickGroup')"
            fluid
          />
        </div>
      </fieldset>
      <div class="dialog-actions">
        <Button type="button" :label="t('common.cancel')" text @click="emit('close')" />
        <Button
          type="submit"
          :label="t('common.save')"
          icon="mdi mdi-content-save"
          :loading="saving"
          :disabled="!switchesComplete(form)"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped lang="scss">
.switches-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.switches-form {
  display: grid;
  gap: var(--space-3);
}

.switch-group {
  display: grid;
  gap: var(--space-3);
  padding: 0;
  margin: 0;
  border: 0;
}

.switch {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.switch-label {
  display: grid;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
