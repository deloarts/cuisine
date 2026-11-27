<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { endOtherSessions, endSession, listSessions, type Session } from '@/features/account/api/security'
import { useAppToast } from '@/core/composables/useAppToast'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'

const { t, locale } = useI18n()
const toast = useAppToast()
const sessions = ref<Session[]>([])

async function load() {
  sessions.value = await listSessions()
}

async function revoke(id: string) {
  try {
    await endSession(id)
    await load()
  } catch (err) {
    toast.error(err)
  }
}

async function revokeOthers() {
  try {
    await endOtherSessions()
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
    <h2 class="panel-title">{{ t('account.sessions.title') }}</h2>
    <DataTable :value="sessions" size="small" data-key="id" scrollable class="device-table">
      <Column :header="t('account.sessions.device')">
        <template #body="{ data }">
          <span class="agent">{{ data.user_agent }}</span>
          <Tag v-if="data.current" :value="t('account.sessions.current')" severity="success" />
        </template>
      </Column>
      <Column field="client_ip" :header="t('securityLog.address')" />
      <Column :header="t('account.sessions.lastSeen')">
        <template #body="{ data }">{{ formatDateTime(data.last_seen_at, locale as AppLocale) }}</template>
      </Column>
      <Column class="row-actions">
        <template #body="{ data }">
          <Button
            v-if="!data.current"
            icon="mdi mdi-logout"
            text
            rounded
            severity="danger"
            :aria-label="t('account.sessions.revoke')"
            @click="revoke(data.id)"
          />
        </template>
      </Column>
    </DataTable>
    <div>
      <Button
        :label="t('account.sessions.revokeOthers')"
        outlined
        severity="danger"
        :disabled="sessions.length < 2"
        @click="revokeOthers"
      />
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
  margin-right: var(--space-2);
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
