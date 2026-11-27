<script setup lang="ts">
/**
 * The user's personal access tokens for scripts and integrations. Agent
 * tokens (those carrying `use:mcp`) live on the AI agents tab, so this tab
 * neither lists nor creates them.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { matchesText } from '@/shared/composables/tableText'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import TokenCreateDialog, { type TokenForm } from '@/shared/components/TokenCreateDialog.vue'
import { createToken, listTokens, revokeToken, type PersonalToken } from '@/features/account/api/account'
import { AGENT_PERMISSION, otherTokens } from '@/features/account/consents'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()

const tokens = ref<PersonalToken[]>([])
const dialog = ref(false)
const table = useResourceTable('tokens', { q: 'string' })
const filtered = computed(() => tokens.value.filter((k) => matchesText(table.filters.q, k.name, k.token_prefix)))
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name'), filter: true },
  { field: 'token_prefix', header: t('tokens.prefix') },
  { field: 'permissions', header: t('tokens.permissions'), sortable: false },
  { field: 'expires_at', header: t('tokens.expires') },
  { field: 'last_used_at', header: t('account.lastUsed') },
])
const saving = ref(false)
const createdSecret = ref<string | null>(null)

async function load() {
  tokens.value = otherTokens(await listTokens())
}

function open() {
  createdSecret.value = null
  dialog.value = true
}

async function create(form: TokenForm) {
  saving.value = true
  try {
    createdSecret.value = await createToken(form)
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function revoke(id: string) {
  try {
    await revokeToken(id)
    await load()
  } catch (err) {
    toast.error(err)
  }
}

const tokenMenu = (token: PersonalToken): MenuItem[] => [
  { label: t('tokens.revoke'), icon: 'mdi mdi-delete-outline', command: () => void revoke(token.id) },
]

onMounted(() => {
  load().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <div class="settings-tab">
    <div class="block-head">
      <h2 class="panel-title">{{ t('tokens.patTitle') }}</h2>
      <Button :label="t('tokens.create')" icon="mdi mdi-plus" @click="open" />
    </div>
    <p class="hint">{{ t('tokens.patHint') }}</p>
    <ResourceTable
      :state="table"
      :value="filtered"
      :columns="columns"
      :fill="false"
      :menu="tokenMenu"
      :empty-message="t('tokens.none')"
      empty-icon="mdi mdi-key-outline"
    >
      <template #filter-name>
        <InputText
          v-model="table.filters.q"
          :placeholder="t('tableFilters.search')"
          :aria-label="t('tableFilters.filterBy', { column: t('common.name') })"
          size="small"
          fluid
        />
      </template>
      <template #body-token_prefix="{ data }"><code>{{ data.token_prefix }}…</code></template>
      <template #body-permissions="{ data }">
        <Tag v-for="p in data.permissions" :key="p" :value="p" severity="secondary" class="perm" />
      </template>
      <template #body-expires_at="{ data }">{{ formatDateTime(data.expires_at, locale as AppLocale) }}</template>
      <template #body-last_used_at="{ data }">{{ formatDateTime(data.last_used_at, locale as AppLocale) }}</template>
      <template #phone="{ data }">
        {{ data.token_prefix }}… · {{ t('tokens.expires') }} {{ formatDateTime(data.expires_at, locale as AppLocale) }}
      </template>
    </ResourceTable>
    <TokenCreateDialog
      v-model:visible="dialog"
      :title="t('tokens.create')"
      :saving="saving"
      :created-secret="createdSecret"
      :exclude-permissions="[AGENT_PERMISSION]"
      @submit="create"
    />
  </div>
</template>

<style scoped lang="scss">
.block-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.perm {
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
