<script setup lang="ts">
/**
 * Webhooks: URLs that receive a signed POST when chosen events happen. The
 * signing secret shows once, after creating or rotating it. Each webhook's
 * delivery log lists attempts, and a failed delivery can be sent again.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'openvue/menuitem'
import { useConfirm } from 'openvue/useconfirm'

import ResourceTable, { type ResourceTableColumn } from '@/shared/components/resource-view/ResourceTable.vue'
import { useResourceTable } from '@/shared/composables/useResourceTable'
import {
  webhooksApi,
  type WebhookDelivery,
  type WebhookEvent,
  type WebhookForm,
  type WebhookSubscription,
} from '@/features/admin-settings/api/notifications'
import { getNotificationSettings, saveNotificationSettings } from '@/features/admin-settings/api/settings'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

// The switches render at once and stay disabled until the list and the
// settings are in.
const settings = ref<Schemas['NotificationSettingsSchema']>({ webhooks_enabled: false, allow_private_webhook_targets: false })
const loaded = ref(false)
const hooks = ref<WebhookSubscription[]>([])
const events = ref<WebhookEvent[]>([])
const dialog = ref(false)
const editing = ref<WebhookSubscription | null>(null)
const form = ref<WebhookForm>({ name: '', url: '', events: [], enabled: true })
const saving = ref(false)
const secret = ref<string | null>(null)

const logFor = ref<WebhookSubscription | null>(null)
const deliveries = ref<WebhookDelivery[]>([])
const deliveriesTotal = ref(0)
const deliveriesTable = useResourceTable('webhookDeliveries', {}, () => loadDeliveries())
const deliveryColumns = computed<ResourceTableColumn[]>(() => [
  { field: 'created', header: t('adminArea.webhooks.when') },
  { field: 'event', header: t('adminArea.webhooks.event'), phone: true },
  { field: 'status', header: t('adminArea.webhooks.status') },
  { field: 'attempts', header: t('adminArea.webhooks.attempts') },
])

async function load() {
  try {
    ;[hooks.value, events.value, settings.value] = await Promise.all([
      webhooksApi.list(),
      webhooksApi.events(),
      getNotificationSettings(),
    ])
    loaded.value = true
  } catch (err) {
    toast.error(err)
  }
}

function open(hook: WebhookSubscription | null) {
  editing.value = hook
  form.value = hook
    ? { name: hook.name, url: hook.url, events: [...hook.events], enabled: hook.enabled }
    : { name: '', url: '', events: [], enabled: true }
  dialog.value = true
}

async function submit() {
  saving.value = true
  try {
    if (editing.value) {
      await webhooksApi.update(editing.value.id, form.value)
    } else {
      secret.value = (await webhooksApi.create(form.value)).secret
    }
    dialog.value = false
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
      void action()
        .then(load)
        .catch((err: unknown) => toast.error(err))
    },
  })
}

const remove = (hook: WebhookSubscription) =>
  ask(t('adminArea.webhooks.deleteConfirm', { name: hook.name }), () => webhooksApi.remove(hook.id))
const rotate = (hook: WebhookSubscription) =>
  ask(t('adminArea.webhooks.rotateConfirm', { name: hook.name }), async () => {
    secret.value = (await webhooksApi.rotateSecret(hook.id)).secret
  })

async function test(hook: WebhookSubscription) {
  try {
    const delivery = await webhooksApi.test(hook.id)
    toast.success(t('adminArea.webhooks.testSent', { status: delivery.http_status ?? delivery.status }))
    if (logFor.value?.id === hook.id) await loadDeliveries()
  } catch (err) {
    toast.error(err)
  }
}

async function loadDeliveries() {
  if (!logFor.value) return
  try {
    const page = await webhooksApi.deliveries(
      logFor.value.id,
      deliveriesTable.rows.value,
      deliveriesTable.first.value,
    )
    deliveries.value = page.items
    deliveriesTotal.value = page.total
  } catch (err) {
    toast.error(err)
  }
}

function showLog(hook: WebhookSubscription) {
  logFor.value = hook
  deliveriesTable.first.value = 0
  void loadDeliveries()
}

async function retry(delivery: WebhookDelivery) {
  if (!logFor.value) return
  try {
    await webhooksApi.retry(logFor.value.id, delivery.id)
    await loadDeliveries()
  } catch (err) {
    toast.error(err)
  }
}

const deliveryMenu = (delivery: WebhookDelivery): MenuItem[] =>
  canWrite && delivery.status === 'failed'
    ? [{ label: t('adminArea.webhooks.retry'), icon: 'mdi mdi-replay', command: () => void retry(delivery) }]
    : []

async function saveSettings() {
  if (!loaded.value) return
  try {
    settings.value = await saveNotificationSettings(settings.value)
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  }
}

async function copySecret() {
  if (secret.value) await navigator.clipboard.writeText(secret.value)
  toast.success(t('common.done'))
}

onMounted(() => void load())
</script>

<template>
  <div class="settings-tab">
    <div class="section-head">
      <h2 class="panel-title">{{ t('adminArea.webhooks.title') }}</h2>
      <div v-if="canWrite" class="section-actions">
        <Button :label="t('adminArea.webhooks.create')" icon="mdi mdi-plus" :disabled="!loaded" @click="open(null)" />
      </div>
    </div>
    <p class="hint">{{ t('adminArea.webhooks.hint') }}</p>
    <div class="hook-settings">
      <div class="field toggle-field">
        <ToggleSwitch v-model="settings.webhooks_enabled" input-id="hooks-enabled" :disabled="!canWrite || !loaded" @update:model-value="saveSettings" />
        <label for="hooks-enabled">{{ t('adminArea.webhooks.allEnabled') }}</label>
      </div>
      <div class="field toggle-field">
        <ToggleSwitch v-model="settings.allow_private_webhook_targets" input-id="hooks-private" :disabled="!canWrite || !loaded" @update:model-value="saveSettings" />
        <label for="hooks-private">{{ t('adminArea.webhooks.allowPrivate') }}</label>
      </div>
    </div>

    <Message v-if="secret" severity="warn" :closable="true" @close="secret = null">
      <p>{{ t('adminArea.webhooks.secretOnce') }}</p>
      <code class="secret">{{ secret }}</code>
      <Button :label="t('common.copy')" icon="mdi mdi-content-copy" text size="small" @click="copySecret" />
    </Message>

    <ul v-if="hooks.length" class="hook-list">
      <li v-for="hook in hooks" :key="hook.id" class="hook-row">
        <span class="hook-text">
          <strong>{{ hook.name }}</strong>
          <small class="text-muted hook-url">{{ hook.url }}</small>
          <small class="text-muted">{{ hook.events.join(', ') }}</small>
        </span>
        <Tag :value="hook.enabled ? t('adminArea.webhooks.on') : t('adminArea.webhooks.off')" :severity="hook.enabled ? 'success' : 'secondary'" />
        <span class="hook-actions">
          <Button icon="mdi mdi-history" text rounded :aria-label="t('adminArea.webhooks.log')" @click="showLog(hook)" />
          <template v-if="canWrite">
            <Button icon="mdi mdi-send-outline" text rounded :aria-label="t('adminArea.webhooks.test')" @click="test(hook)" />
            <Button icon="mdi mdi-key-change" text rounded :aria-label="t('adminArea.webhooks.rotate')" @click="rotate(hook)" />
            <Button icon="mdi mdi-pencil" text rounded :aria-label="t('common.edit')" @click="open(hook)" />
            <Button icon="mdi mdi-delete-outline" text rounded severity="danger" :aria-label="t('common.delete')" @click="remove(hook)" />
          </template>
        </span>
      </li>
    </ul>
    <p v-else-if="loaded" class="empty-note">{{ t('adminArea.webhooks.none') }}</p>

    <template v-if="logFor">
      <h3 class="panel-title">{{ t('adminArea.webhooks.logOf', { name: logFor.name }) }}</h3>
      <ResourceTable
        :state="deliveriesTable"
        :value="deliveries"
        :columns="deliveryColumns"
        :total="deliveriesTotal"
        :fill="false"
        :menu="deliveryMenu"
        :empty-message="t('adminArea.webhooks.noDeliveries')"
        empty-icon="mdi mdi-history"
      >
        <template #body-created="{ data }">{{ formatDateTime(data.created, locale as AppLocale) }}</template>
        <template #body-status="{ data }">
          <Tag
            :value="data.http_status ? `${data.status} · ${data.http_status}` : data.status"
            :severity="data.status === 'succeeded' ? 'success' : data.status === 'failed' ? 'danger' : 'info'"
          />
          <small v-if="data.error" class="text-muted"> {{ data.error }}</small>
        </template>
        <template #phone="{ data }">
          {{ formatDateTime(data.created, locale as AppLocale) }} · {{ data.status }}
        </template>
      </ResourceTable>
    </template>

    <Dialog v-model:visible="dialog" modal :header="editing ? t('adminArea.webhooks.edit') : t('adminArea.webhooks.create')" class="hook-dialog">
      <form class="hook-form" @submit.prevent="submit">
        <div class="field">
          <label for="hook-name">{{ t('common.name') }}</label>
          <InputText id="hook-name" v-model="form.name" required fluid />
        </div>
        <div class="field">
          <label for="hook-url">{{ t('adminArea.webhooks.url') }}</label>
          <InputText id="hook-url" v-model="form.url" type="url" required fluid placeholder="https://" />
        </div>
        <div class="field">
          <label id="hook-events-label" for="hook-events">{{ t('adminArea.webhooks.events') }}</label>
          <MultiSelect
            id="hook-events"
            v-model="form.events"
            :options="events"
            option-label="key"
            option-value="key"
            aria-labelledby="hook-events-label"
            display="chip"
            fluid
          >
            <template #option="{ option }">
              <span class="event-option">
                <code>{{ option.key }}</code>
                <small class="text-muted">{{ option.description }}</small>
              </span>
            </template>
          </MultiSelect>
        </div>
        <div class="field toggle-field">
          <ToggleSwitch v-model="form.enabled" input-id="hook-enabled" />
          <label for="hook-enabled">{{ t('adminArea.webhooks.enabled') }}</label>
        </div>
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="dialog = false" />
          <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!form.events.length" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
.hook-list {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  margin: 0;
  list-style: none;
}

.hook-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.hook-text {
  display: grid;
  min-width: 0;
}

.hook-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hook-actions {
  display: flex;
  flex-wrap: wrap;
  grid-column: 1 / -1;
}

.secret {
  display: block;
  overflow-x: auto;
  margin: var(--space-1) 0;
}

.hook-dialog {
  width: min(var(--dialog-width-md), 100vw - 2 * var(--space-4));
}

.hook-form {
  display: grid;
  gap: var(--space-3);
}

.event-option {
  display: grid;
}

.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (min-width: $bp-sm) {
  .hook-actions {
    grid-column: auto;
  }

  .hook-row {
    grid-template-columns: minmax(0, 1fr) auto auto;
  }
}
</style>
