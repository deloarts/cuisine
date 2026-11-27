<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { forgetTrustedDevice, listTrustedDevices, type TrustedDevice } from '@/features/account/api/security'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const devices = ref<TrustedDevice[]>([])

async function load() {
  devices.value = await listTrustedDevices()
}

async function revoke(id?: string) {
  try {
    await forgetTrustedDevice(id)
    await load()
  } catch (err) {
    toast.error(err)
  }
}

onMounted(() => {
  load().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <div class="section">
    <h2 class="panel-title">{{ t('account.devices.title') }}</h2>
    <p class="hint">{{ t('account.devices.hint') }}</p>
    <DataTable :value="devices" size="small" data-key="id" scrollable class="device-table">
      <template #empty>{{ t('account.devices.none') }}</template>
      <Column :header="t('account.sessions.device')">
        <template #body="{ data }"><span class="agent">{{ data.user_agent }}</span></template>
      </Column>
      <Column :header="t('account.devices.expires')">
        <template #body="{ data }">{{ formatDateTime(data.expires_at, locale as AppLocale) }}</template>
      </Column>
      <Column class="row-actions">
        <template #body="{ data }">
          <Button
            icon="mdi mdi-close"
            text
            rounded
            severity="danger"
            :aria-label="t('account.devices.revoke')"
            @click="revoke(data.id)"
          />
        </template>
      </Column>
    </DataTable>
    <div v-if="devices.length > 1">
      <Button :label="t('account.devices.revokeAll')" outlined severity="danger" @click="revoke()" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.agent {
  font-size: var(--font-size-sm);
}

// The device's browser string is long, so the cells keep to one line and the
// table scrolls sideways inside the section, as every table does.
.device-table {
  min-width: 0;
}

.device-table :deep(th),
.device-table :deep(td) {
  white-space: nowrap;
}
</style>
