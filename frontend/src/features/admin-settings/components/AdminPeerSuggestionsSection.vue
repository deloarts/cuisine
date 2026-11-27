<script setup lang="ts">
/**
 * Suggested by peers: catalogue values paired instances sent with their
 * recipes that differ from the local entry their mapping points at, shown
 * next to the reference data updates with the same field labels. Each row
 * is one field of one local entry from one peer and is accepted (the local
 * entry takes the peer's value) or dismissed (hidden until the peer offers
 * another value). Allergens and diet markers come first and are marked.
 * The peer and kind filters live in the URL and are applied by the backend,
 * and the table keeps the backend's order until a column header is clicked.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import { isSafetyField } from '@/features/admin-settings/referenceUpdates'
import {
  mayDecide,
  suggestionKey,
  suggestionRows,
  SUGGESTION_KINDS,
  type PeerSuggestionRow,
  type SuggestionKind,
} from '@/features/admin-settings/peerSuggestions'
import { peeringApi, suggestionsApi, type Peer } from '@/features/admin-settings/api/peering'
import { useCatalogueFieldLabels } from '@/features/admin-settings/useCatalogueFieldLabels'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const toast = useAppToast()
const { kindLabel, fieldLabel, valueText } = useCatalogueFieldLabels()
const currentUser = useCurrentUserStore()

const rows = ref<PeerSuggestionRow[]>([])
const peers = ref<Peer[]>([])
const loading = ref(false)
const busy = ref<string | null>(null)

const table = useResourceTable('peerSuggestions', { sugPeer: 'string', sugKind: 'string' }, () => load())
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name') },
  { field: 'kind', header: t('peerSuggestions.kind'), filter: true, sortField: (r: PeerSuggestionRow) => kindLabel(r.kind) },
  { field: 'field', header: t('peerSuggestions.field'), sortField: (r: PeerSuggestionRow) => fieldLabel(r.field) },
  { field: 'peer', header: t('peerSuggestions.peer'), filter: true, sortField: (r: PeerSuggestionRow) => r.peer.name },
  { field: 'current', header: t('peerSuggestions.current'), sortField: (r: PeerSuggestionRow) => show(r, r.current) },
  { field: 'suggested', header: t('peerSuggestions.suggested'), sortField: (r: PeerSuggestionRow) => show(r, r.suggested) },
])
const kindOptions = computed(() => SUGGESTION_KINDS.map((k) => ({ value: k, label: kindLabel(k) })))
const peerOptions = computed(() =>
  peers.value.filter((p) => p.status === 'active').map((p) => ({ value: p.id, label: p.name })),
)

function show(row: PeerSuggestionRow, value: unknown): string {
  return valueText(row.field, value)
}

function canDecide(kind: SuggestionKind): boolean {
  return mayDecide(kind, (p) => currentUser.hasPermission(p))
}

async function load() {
  loading.value = true
  try {
    const query: { peer_id?: string; kind?: SuggestionKind } = {}
    if (table.filters.sugPeer) query.peer_id = table.filters.sugPeer
    if (table.filters.sugKind) query.kind = table.filters.sugKind as SuggestionKind
    rows.value = suggestionRows(await suggestionsApi.list(query))
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function loadPeers() {
  try {
    peers.value = await peeringApi.list()
  } catch (err) {
    toast.error(err)
  }
}

async function decide(row: PeerSuggestionRow, action: 'accept' | 'dismiss') {
  busy.value = row.id
  try {
    const body = { peer_id: row.peer.id, kind: row.kind, source_id: row.source_id, field: row.field }
    await (action === 'accept' ? suggestionsApi.accept(body) : suggestionsApi.dismiss(body))
    if (action === 'accept') {
      toast.success(t('peerSuggestions.accepted', { name: row.name }))
      // Accepting changes the entry, so other rows of it may change too.
      await load()
    } else {
      rows.value = rows.value.filter((r) => suggestionKey(r) !== row.id)
    }
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

const suggestionMenu = (row: PeerSuggestionRow): MenuItem[] =>
  canDecide(row.kind)
    ? [
        {
          label: t('peerSuggestions.accept', { name: row.name, field: fieldLabel(row.field) }),
          icon: 'mdi mdi-check',
          disabled: busy.value === row.id,
          command: () => void decide(row, 'accept'),
        },
        {
          label: t('peerSuggestions.dismiss', { name: row.name, field: fieldLabel(row.field) }),
          icon: 'mdi mdi-close',
          disabled: busy.value === row.id,
          command: () => void decide(row, 'dismiss'),
        },
      ]
    : []

onMounted(() => {
  void loadPeers()
  void load()
})
</script>

<template>
  <section class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('peerSuggestions.title') }}</h2>
      <div class="section-actions">
        <Button :label="t('adminArea.refresh')" icon="mdi mdi-refresh" text :loading="loading" @click="load" />
      </div>
    </div>
    <p class="hint">{{ t('peerSuggestions.hint') }}</p>
    <ResourceTable
      :state="table"
      :value="rows"
      :columns="columns"
      :loading="loading"
      :fill="false"
      :default-sort="null"
      :menu="suggestionMenu"
      :empty-message="t('peerSuggestions.none')"
      empty-icon="mdi mdi-check-all"
    >
      <template #filter-kind>
        <Select
          v-model="table.filters.sugKind"
          :options="kindOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('peerSuggestions.kind') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #filter-peer>
        <Select
          v-model="table.filters.sugPeer"
          :options="peerOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('tableFilters.all')"
          :aria-label="t('tableFilters.filterBy', { column: t('peerSuggestions.peer') })"
          show-clear
          size="small"
          fluid
        />
      </template>
      <template #body-name="{ data }">
        <span class="name">
          <Tag v-if="isSafetyField(data.field)" :value="t('peerSuggestions.safety')" severity="danger" />
          {{ data.name }}
        </span>
      </template>
      <template #body-kind="{ data }">{{ kindLabel(data.kind) }}</template>
      <template #body-field="{ data }">{{ fieldLabel(data.field) }}</template>
      <template #body-peer="{ data }">{{ data.peer.name }}</template>
      <template #body-current="{ data }">{{ show(data, data.current) }}</template>
      <template #body-suggested="{ data }">
        <strong>{{ show(data, data.suggested) }}</strong>
        <small v-if="data.unmapped_units.length" class="unmapped">
          {{ t('peerSuggestions.unmappedUnits', { units: data.unmapped_units.join(', ') }) }}
        </small>
      </template>
      <template #phone="{ data }">
        {{ kindLabel(data.kind) }} · {{ data.peer.name }} · {{ fieldLabel(data.field) }}:
        {{ show(data, data.current) }} → {{ show(data, data.suggested) }}
        <small v-if="data.unmapped_units.length" class="unmapped">
          {{ t('peerSuggestions.unmappedUnits', { units: data.unmapped_units.join(', ') }) }}
        </small>
      </template>
    </ResourceTable>
  </section>
</template>

<style scoped lang="scss">
.name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.unmapped {
  display: block;
  color: var(--p-text-muted-color);
}
</style>
