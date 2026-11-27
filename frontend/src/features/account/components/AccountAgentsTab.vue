<script setup lang="ts">
/**
 * Everything about AI agents for this user: the voluntary consent (without
 * it there are no agent tokens, and withdrawing it revokes them all), the
 * agent tokens themselves with the command that connects an agent, the apps
 * connected through OAuth (ChatGPT, claude.ai), and the calls agents made.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'
import { useConfirm } from 'openvue/useconfirm'

import AgentCallTable from '@/shared/components/AgentCallTable.vue'
import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import TokenCreateDialog, { type TokenForm } from '@/shared/components/TokenCreateDialog.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import {
  createToken,
  grantConsent,
  listConnectedApps,
  listConsents,
  listTokens,
  revokeConnectedApp,
  revokeToken,
  withdrawConsent,
  type ConnectedApp,
  type Consent,
  type PersonalToken,
} from '@/features/account/api/account'
import {
  AGENT_PERMISSION,
  AGENT_TOKEN_DAYS,
  agentTokens,
  canCreateAgentToken,
  consentOf,
  withdrawWarning,
} from '@/features/account/consents'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const currentUser = useCurrentUserStore()

// In development the API runs on its own port, so the agent needs that origin.
const apiOrigin = (import.meta.env.VITE_API_URL as string | undefined) || window.location.origin
const mcpCommand = `claude mcp add --transport http cuisine ${apiOrigin}/api/v1/mcp --header "Authorization: Bearer <token>"`

const consents = ref<Consent[]>([])
const tokens = ref<PersonalToken[]>([])
const apps = ref<ConnectedApp[]>([])
const switching = ref(false)
const dialog = ref(false)
const saving = ref(false)
const createdSecret = ref<string | null>(null)

const consent = computed(() => consentOf(consents.value, 'ai_agents'))
const canWriteTokens = computed(() => currentUser.hasPermission(Permission.WRITE_PAT))
const canCreate = computed(() => canCreateAgentToken(consent.value, canWriteTokens.value))
const grantedAt = computed(() =>
  consent.value.granted_at ? formatDateTime(consent.value.granted_at, locale.value as AppLocale) : '',
)

const table = useResourceTable('agentTokens', {})
const columns = computed<ResourceTableColumn[]>(() => [
  { field: 'name', header: t('common.name') },
  { field: 'token_prefix', header: t('tokens.prefix') },
  { field: 'expires_at', header: t('tokens.expires') },
  { field: 'last_used_at', header: t('account.lastUsed') },
])

async function loadTokens() {
  tokens.value = canWriteTokens.value ? agentTokens(await listTokens()) : []
}

async function loadApps() {
  apps.value = await listConnectedApps()
}

async function load() {
  const [list] = await Promise.all([listConsents(), loadTokens(), loadApps()])
  consents.value = list
}

async function setConsent(value: boolean) {
  if (value) {
    await change(() => grantConsent('ai_agents'))
    return
  }
  const warning = withdrawWarning('ai_agents', tokens.value.length + apps.value.length)
  confirm.require({
    header: t('consents.agents.withdrawTitle'),
    message: t(warning.key, { count: warning.count }, warning.count),
    acceptProps: { label: t('consents.withdraw'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void change(() => withdrawConsent('ai_agents')),
  })
}

async function change(action: () => Promise<Consent[]>) {
  switching.value = true
  try {
    consents.value = await action()
    await Promise.all([loadTokens(), loadApps()])
  } catch (err) {
    toast.error(err)
  } finally {
    switching.value = false
  }
}

function open() {
  createdSecret.value = null
  dialog.value = true
}

async function create(form: TokenForm) {
  saving.value = true
  try {
    createdSecret.value = await createToken(form)
    await loadTokens()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

async function revoke(id: string) {
  try {
    await revokeToken(id)
    await loadTokens()
  } catch (err) {
    toast.error(err)
  }
}

const appsTable = useResourceTable('connectedApps', {})
const appColumns = computed<ResourceTableColumn[]>(() => [
  { field: 'client_name', header: t('connectedApps.app') },
  { field: 'permissions', header: t('connectedApps.permissions'), wrap: true },
  { field: 'created', header: t('connectedApps.connected') },
  { field: 'expires_at', header: t('tokens.expires') },
  { field: 'last_used_at', header: t('account.lastUsed') },
])

function permissionLabel(permission: string): string {
  return t(`permissions.${permission.replace(':', '_')}`)
}

function confirmRevokeApp(app: ConnectedApp) {
  confirm.require({
    header: t('connectedApps.revokeTitle'),
    message: t('connectedApps.revokeMessage', { name: app.client_name }),
    acceptProps: { label: t('connectedApps.revoke'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void revokeApp(app.id),
  })
}

async function revokeApp(id: string) {
  try {
    await revokeConnectedApp(id)
    await loadApps()
  } catch (err) {
    toast.error(err)
  }
}

const appMenu = (app: ConnectedApp): MenuItem[] => [
  { label: t('connectedApps.revoke'), icon: 'mdi mdi-link-off', command: () => confirmRevokeApp(app) },
]

const tokenMenu = (token: PersonalToken): MenuItem[] => [
  { label: t('tokens.revoke'), icon: 'mdi mdi-delete-outline', command: () => void revoke(token.id) },
]

onMounted(() => {
  load().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <div class="settings-tab agents-tab">
    <section class="block">
      <h2 class="panel-title">{{ t('consents.agents.title') }}</h2>
      <p class="hint">{{ t('consents.agents.explanation') }}</p>
      <div class="consent-row">
        <ToggleSwitch
          :model-value="consent.granted"
          input-id="consent-agents"
          :disabled="switching"
          @update:model-value="setConsent"
        />
        <label for="consent-agents">{{ t('consents.agents.label') }}</label>
      </div>
      <small class="field-hint">
        {{ consent.granted ? t('consents.grantedAt', { date: grantedAt }) : t('consents.agents.missing') }}
      </small>
    </section>

    <section v-if="canWriteTokens" class="block">
      <div class="block-head">
        <h2 class="panel-title">{{ t('consents.agents.tokensTitle') }}</h2>
        <Button :label="t('consents.agents.createToken')" icon="mdi mdi-plus" :disabled="!canCreate" @click="open" />
      </div>
      <Message v-if="consent.granted" severity="secondary" :closable="false">
        <p class="mcp-title"><i class="mdi mdi-robot-outline" aria-hidden="true" /> {{ t('agents.mcpTitle') }}</p>
        <p>{{ t('agents.mcpHint') }}</p>
        <code class="mcp-command">{{ mcpCommand }}</code>
      </Message>
      <ResourceTable
        :state="table"
        :value="tokens"
        :columns="columns"
        :fill="false"
        :menu="tokenMenu"
        :empty-message="t('consents.agents.noTokens')"
        empty-icon="mdi mdi-robot-outline"
      >
        <template #body-token_prefix="{ data }"><code>{{ data.token_prefix }}…</code></template>
        <template #body-expires_at="{ data }">{{ formatDateTime(data.expires_at, locale as AppLocale) }}</template>
        <template #body-last_used_at="{ data }">{{ formatDateTime(data.last_used_at, locale as AppLocale) }}</template>
        <template #phone="{ data }">
          {{ data.token_prefix }}… · {{ t('tokens.expires') }} {{ formatDateTime(data.expires_at, locale as AppLocale) }}
        </template>
      </ResourceTable>
    </section>

    <section class="block">
      <h2 class="panel-title">{{ t('connectedApps.title') }}</h2>
      <p class="hint">{{ t('connectedApps.hint') }}</p>
      <ResourceTable
        :state="appsTable"
        :value="apps"
        :columns="appColumns"
        :fill="false"
        :menu="appMenu"
        :empty-message="t('connectedApps.none')"
        empty-icon="mdi mdi-link-variant"
      >
        <template #body-client_name="{ data }">
          {{ data.client_name }} <small class="app-host">{{ data.redirect_host }}</small>
        </template>
        <template #body-permissions="{ data }">
          {{ data.permissions.map(permissionLabel).join(', ') }}
        </template>
        <template #body-created="{ data }">{{ formatDateTime(data.created, locale as AppLocale) }}</template>
        <template #body-expires_at="{ data }">{{ formatDateTime(data.expires_at, locale as AppLocale) }}</template>
        <template #body-last_used_at="{ data }">{{ formatDateTime(data.last_used_at, locale as AppLocale) }}</template>
        <template #phone="{ data }">
          {{ data.redirect_host }} · {{ t('tokens.expires') }} {{ formatDateTime(data.expires_at, locale as AppLocale) }}
        </template>
      </ResourceTable>
    </section>

    <section class="block">
      <h2 class="panel-title">{{ t('agents.tab') }}</h2>
      <p class="hint">{{ t('agents.ownHint') }}</p>
      <AgentCallTable scope="own" />
    </section>

    <TokenCreateDialog
      v-model:visible="dialog"
      :title="t('consents.agents.createToken')"
      :saving="saving"
      :created-secret="createdSecret"
      :fixed-permissions="[AGENT_PERMISSION]"
      :max-days="AGENT_TOKEN_DAYS"
      :hint="t('consents.agents.tokenHint', { days: AGENT_TOKEN_DAYS })"
      @submit="create"
    />
  </div>
</template>

<style scoped lang="scss">
.agents-tab {
  gap: var(--space-6);
}

.block-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.block {
  display: grid;
  // One column as wide as the tab, so a long line inside (the agent's
  // connect command) scrolls in its own box instead of widening the block
  // and pushing its create button off a phone's screen.
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-3);
}

.consent-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
}

.app-host {
  color: var(--p-text-muted-color);
}

.mcp-title {
  margin: 0 0 var(--space-1);
  font-weight: 700;
}

.mcp-command {
  display: block;
  overflow-x: auto;
  margin-top: var(--space-2);
  white-space: pre;
  font-size: var(--font-size-sm);
}
</style>
