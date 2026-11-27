<script setup lang="ts">
/**
 * How a paired instance's catalogue entries map onto this instance's
 * catalogue: matched by seed key or decided by an administrator. Correcting
 * one rebuilds every mirror of that peer that uses the entry at once, since
 * everything derived is computed from the mapping.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import MappingDecisionFields from '@/features/admin-settings/components/MappingDecisionFields.vue'
import { incomingApi, type Peer, type PeerMapping } from '@/features/admin-settings/api/peering'
import {
  decisionComplete,
  entryKey,
  mappingDecision,
  type DecisionState,
} from '@/features/admin-settings/incomingRecipes'
import { catalogueApi } from '@/features/admin-settings/api/catalogue'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { normaliseText } from '@/shared/composables/tableText'
import type { EquipmentResponse } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'

const props = defineProps<{ peer: Peer | null }>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const resources = useCookbookResources()

const mappings = ref<PeerMapping[]>([])
const equipment = ref<EquipmentResponse[]>([])
const loading = ref(false)
const search = ref('')
// The mapping being corrected and its new decision.
const editing = ref<string | null>(null)
const draft = ref<DecisionState | null>(null)
const saving = ref(false)
const visible = computed({
  get: () => props.peer !== null,
  set: (open: boolean) => {
    if (!open) emit('close')
  },
})
const shown = computed(() => {
  const q = normaliseText(search.value.trim())
  return q
    ? mappings.value.filter((m) => normaliseText(`${m.name} ${m.target_name ?? ''}`).includes(q))
    : mappings.value
})

async function load(peer: Peer) {
  loading.value = true
  try {
    mappings.value = await incomingApi.mappings(peer.id)
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.peer,
  (peer) => {
    editing.value = null
    draft.value = null
    search.value = ''
    mappings.value = []
    if (peer) void load(peer)
  },
  { immediate: true },
)

async function edit(mapping: PeerMapping) {
  editing.value = entryKey(mapping)
  draft.value = mappingDecision(mapping)
  try {
    await resources.load()
    if (!equipment.value.length) equipment.value = await catalogueApi.equipment()
  } catch (err) {
    toast.error(err)
  }
}

function cancel() {
  editing.value = null
  draft.value = null
}

async function save(mapping: PeerMapping) {
  if (!props.peer || !draft.value || !decisionComplete(draft.value)) return
  saving.value = true
  try {
    const updated = await incomingApi.correct(props.peer.id, mapping.kind, mapping.source_id, {
      action: draft.value.action,
      target_id: draft.value.action === 'map' ? draft.value.target_id : null,
      category_id: draft.value.action === 'create' && mapping.kind === 'ingredient' ? draft.value.category_id : null,
    })
    mappings.value = mappings.value.map((m) => (entryKey(m) === entryKey(updated) ? updated : m))
    toast.success(t('adminArea.mappings.saved', { n: updated.used_by }, updated.used_by))
    cancel()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

function current(mapping: PeerMapping): string {
  if (mapping.action === 'map') return t('adminArea.mappings.mapsTo', { name: mapping.target_name ?? '?' })
  if (mapping.action === 'plain') return t('adminArea.mappings.plain')
  if (mapping.action === 'none') return t(`adminArea.incoming.noneHint.${mapping.kind}`)
  return t('adminArea.mappings.undecided')
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('adminArea.mappings.title', { name: peer?.name ?? '' })"
    class="mappings-dialog"
  >
    <div class="mappings-body">
      <p class="hint">{{ t('adminArea.mappings.hint') }}</p>
      <div class="field">
        <label for="mappings-search" class="visually-hidden">{{ t('adminArea.mappings.search') }}</label>
        <InputText id="mappings-search" v-model="search" :placeholder="t('adminArea.mappings.search')" fluid />
      </div>
      <ul v-if="shown.length" class="mappings-list" data-testid="mappings-list">
        <li v-for="mapping in shown" :key="entryKey(mapping)" class="mapping" :data-testid="`mapping-${entryKey(mapping)}`">
          <div class="mapping-text">
            <span>
              <Tag :value="t(`adminArea.incoming.kinds.${mapping.kind}`)" severity="secondary" />
              <strong class="mapping-name">{{ mapping.name }}</strong>
            </span>
            <small :class="mapping.action ? 'text-muted' : 'mapping-undecided'">{{ current(mapping) }}</small>
            <small class="text-muted">
              {{ mapping.matched_by === 'seed_key' ? t('adminArea.mappings.bySeedKey') : t('adminArea.mappings.byDecision') }}
              <template v-if="mapping.created_here"> · {{ t('adminArea.mappings.createdHere') }}</template>
              · {{ t('adminArea.mappings.usedBy', { n: mapping.used_by }, mapping.used_by) }}
            </small>
          </div>
          <template v-if="editing === entryKey(mapping) && draft">
            <MappingDecisionFields
              v-model="draft"
              :kind="mapping.kind"
              :id-base="`mapping-${mapping.kind}-${mapping.source_id}`"
              :equipment="equipment"
            />
            <div class="row-actions">
              <Button :label="t('common.cancel')" size="small" text @click="cancel" />
              <Button
                :label="t('common.save')"
                icon="mdi mdi-content-save"
                size="small"
                :loading="saving"
                :disabled="!decisionComplete(draft)"
                data-testid="mapping-save"
                @click="save(mapping)"
              />
            </div>
          </template>
          <div v-else-if="canWrite" class="row-actions">
            <Button
              :label="t('adminArea.mappings.change')"
              icon="mdi mdi-pencil-outline"
              size="small"
              text
              :data-testid="`mapping-edit-${entryKey(mapping)}`"
              @click="edit(mapping)"
            />
          </div>
        </li>
      </ul>
      <p v-else-if="!loading" class="empty-note">{{ t('adminArea.mappings.none') }}</p>
    </div>
  </Dialog>
</template>

<style scoped lang="scss">
.mappings-dialog {
  width: min(var(--dialog-width-lg), 100vw - 2 * var(--space-4));
}

.mappings-body {
  display: grid;
  gap: var(--space-3);
}

.mappings-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.mapping {
  display: grid;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
}

.mapping-text {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.mapping-name {
  margin-left: var(--space-2);
}

.mapping-undecided {
  color: var(--p-orange-600);
  font-weight: 700;
}
</style>
