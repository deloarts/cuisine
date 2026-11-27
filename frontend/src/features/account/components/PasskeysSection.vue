<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { listPasskeys, removePasskey, type Passkey } from '@/features/account/api/security'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { AppLocale } from '@/core/i18n'
import { formatDateTime } from '@/core/utils/dates'
import { setUpPasskeyOnThisDevice } from '@/features/auth/utils/passkeySetup'
import { forgetPasskey } from '@/features/auth/utils/rememberedAccounts'
import { passkeyPromptDismissed, passkeysSupported } from '@/features/auth/utils/webauthn'

const { t, locale } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()

const passkeys = ref<Passkey[]>([])
const name = ref('')
const busy = ref(false)
const supported = passkeysSupported()
// The system account signs in with its password and code only.
const isSystemUser = computed(() => useCurrentUserStore().user?.is_systemuser ?? false)

async function load() {
  passkeys.value = await listPasskeys()
}

async function add() {
  busy.value = true
  try {
    const user = useCurrentUserStore().user
    if (!user) return
    await setUpPasskeyOnThisDevice(user.id, name.value || 'Passkey')
    name.value = ''
    await load()
    toast.success(t('account.passkeys.added'))
  } catch (err) {
    if (!passkeyPromptDismissed(err)) toast.error(err)
  } finally {
    busy.value = false
  }
}

function remove(passkey: Passkey) {
  confirm.require({
    message: t('account.passkeys.removeConfirm', { name: passkey.name }),
    header: t('common.confirm'),
    acceptProps: { label: t('common.delete'), severity: 'danger' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => {
      void (async () => {
        try {
          await removePasskey(passkey.id)
          forgetPasskey(passkey.id)
          await load()
        } catch (err) {
          toast.error(err)
        }
      })()
    },
  })
}

onMounted(() => {
  load().catch((err: unknown) => toast.error(err))
})
</script>

<template>
  <div class="section">
    <h2 class="panel-title">{{ t('account.passkeys.title') }}</h2>
    <p class="hint">{{ t('account.passkeys.hint') }}</p>
    <DataTable :value="passkeys" size="small" data-key="id">
      <template #empty>{{ t('account.passkeys.none') }}</template>
      <Column field="name" :header="t('common.name')" />
      <Column :header="t('common.created')">
        <template #body="{ data }">{{ formatDateTime(data.created, locale as AppLocale) }}</template>
      </Column>
      <Column :header="t('account.lastUsed')">
        <template #body="{ data }">{{ formatDateTime(data.last_used_at, locale as AppLocale) }}</template>
      </Column>
      <Column class="row-actions">
        <template #body="{ data }">
          <Button
            icon="mdi mdi-delete-outline"
            text
            rounded
            severity="danger"
            :aria-label="t('common.delete')"
            @click="remove(data)"
          />
        </template>
      </Column>
    </DataTable>
    <Message v-if="isSystemUser" severity="info" :closable="false">
      {{ t('account.passkeys.systemUser') }}
    </Message>
    <Message v-else-if="!supported" severity="info" :closable="false">
      {{ t('account.passkeys.unsupported') }}
    </Message>
    <form v-else class="add" @submit.prevent="add">
      <InputText v-model="name" :placeholder="t('account.passkeys.namePlaceholder')" :aria-label="t('common.name')" />
      <Button type="submit" :label="t('account.passkeys.add')" icon="mdi mdi-fingerprint" :loading="busy" />
    </form>
  </div>
</template>

<style scoped lang="scss">
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.add {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
</style>
