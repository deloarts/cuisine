<script setup lang="ts">
/**
 * Recipes paired instances share with this one wait here until an
 * administrator accepts them; nobody else sees them before. The pending list
 * holds new recipes and held updates (a mirror's update that brought
 * catalogue entries without a mapping); the rejected list keeps what was
 * discarded, which can be reopened or accepted after all.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import IncomingRecipeDialog from '@/features/admin-settings/components/IncomingRecipeDialog.vue'
import { incomingApi, type IncomingRecipe, type IncomingStatus } from '@/features/admin-settings/api/peering'
import { catalogueApi } from '@/features/admin-settings/api/catalogue'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'
import type { EquipmentResponse } from '@/shared/cookbook/types'
import { useCookbookResources } from '@/shared/cookbook/useCookbookResources'

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const resources = useCookbookResources()

const status = ref<IncomingStatus>('pending')
const items = ref<IncomingRecipe[]>([])
const loading = ref(false)
const busy = ref<string | null>(null)
const reviewing = ref<IncomingRecipe | null>(null)
const equipment = ref<EquipmentResponse[]>([])
const statuses = computed(() => [
  { value: 'pending', label: t('adminArea.incoming.pending') },
  { value: 'rejected', label: t('adminArea.incoming.rejected') },
])

async function load() {
  loading.value = true
  try {
    items.value = await incomingApi.list(status.value)
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

// The decision dialog picks from the catalogue, loaded once when needed.
async function loadCatalogue() {
  try {
    await resources.load()
    if (!equipment.value.length) equipment.value = await catalogueApi.equipment()
  } catch (err) {
    toast.error(err)
  }
}

async function review(item: IncomingRecipe) {
  busy.value = item.id
  try {
    const [fresh] = await Promise.all([incomingApi.get(item.id), loadCatalogue()])
    reviewing.value = fresh
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

async function reject(item: IncomingRecipe) {
  busy.value = item.id
  try {
    await incomingApi.reject(item.id)
    toast.success(t('adminArea.incoming.rejectedDone', { title: item.title }))
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

async function reopen(item: IncomingRecipe) {
  busy.value = item.id
  try {
    await incomingApi.reopen(item.id)
    toast.success(t('adminArea.incoming.reopened', { title: item.title }))
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = null
  }
}

async function accepted() {
  reviewing.value = null
  await load()
}

watch(status, () => void load())
onMounted(() => void load())
</script>

<template>
  <div class="settings-tab">
    <h2 class="panel-title">{{ t('adminArea.incoming.title') }}</h2>
    <p class="hint">{{ t('adminArea.incoming.hint') }}</p>
    <SelectButton
      v-model="status"
      :options="statuses"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      :aria-label="t('adminArea.incoming.statusFilter')"
    />
    <ul v-if="items.length" class="row-list" data-testid="incoming-list">
      <li v-for="item in items" :key="item.id" class="row" :data-testid="`incoming-${item.id}`">
        <span class="row-text">
          <strong>{{ item.title }}</strong>
          <small class="text-muted">
            {{
              item.author_name
                ? t('adminArea.incoming.fromBy', { instance: item.peer.name, name: item.author_name })
                : t('adminArea.incoming.from', { instance: item.peer.name })
            }}
            · {{ formatDateTime(item.received_at) }}
          </small>
          <small v-if="item.kind === 'update'" class="incoming-update" data-testid="incoming-update">
            <span class="mdi mdi-update" aria-hidden="true" />
            {{ t('adminArea.incoming.heldUpdateShort') }}
          </small>
          <small class="text-muted">
            {{
              item.entries.length
                ? t('adminArea.incoming.toDecide', { n: item.entries.length }, item.entries.length)
                : t('adminArea.incoming.allMapped')
            }}
          </small>
        </span>
        <Tag
          :value="item.kind === 'update' ? t('adminArea.incoming.kindUpdate') : t('adminArea.incoming.kindNew')"
          :severity="item.kind === 'update' ? 'info' : 'secondary'"
        />
        <span v-if="canWrite" class="row-actions incoming-actions">
          <Button
            :label="item.status === 'rejected' ? t('adminArea.incoming.acceptAnyway') : t('adminArea.incoming.review')"
            icon="mdi mdi-clipboard-check-outline"
            size="small"
            :loading="busy === item.id"
            @click="review(item)"
          />
          <Button
            v-if="item.status === 'pending'"
            :label="t('adminArea.incoming.reject')"
            icon="mdi mdi-close"
            size="small"
            severity="danger"
            text
            :disabled="busy === item.id"
            @click="reject(item)"
          />
          <Button
            v-else
            :label="t('adminArea.incoming.reopen')"
            icon="mdi mdi-restore"
            size="small"
            severity="secondary"
            text
            :disabled="busy === item.id"
            @click="reopen(item)"
          />
        </span>
      </li>
    </ul>
    <p v-else-if="!loading" class="empty-note">
      {{ status === 'pending' ? t('adminArea.incoming.nonePending') : t('adminArea.incoming.noneRejected') }}
    </p>

    <IncomingRecipeDialog :item="reviewing" :equipment="equipment" @accepted="accepted" @close="reviewing = null" />
  </div>
</template>

<style scoped lang="scss">
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

.incoming-update {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--p-primary-color);
  font-weight: 700;
}

.incoming-actions {
  grid-column: 1 / -1;
}
</style>
