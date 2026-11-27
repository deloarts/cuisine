<script setup lang="ts">
/**
 * The user's own data: a download of everything stored about them, and the
 * deletion of the account, which offers that download first.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { downloadText } from '@/shared/composables/fileTransfer'
import AccountDeletionDialog from '@/features/account/components/AccountDeletionDialog.vue'
import { exportMyData } from '@/features/account/api/account'
import { useAppToast } from '@/core/composables/useAppToast'

const { t } = useI18n()
const toast = useAppToast()

const downloading = ref(false)
const deleting = ref(false)

async function download() {
  downloading.value = true
  try {
    const data = await exportMyData()
    const day = new Date().toISOString().slice(0, 10)
    downloadText(JSON.stringify(data, null, 2), `cuisine-data-${day}.json`, 'application/json')
  } catch (err) {
    toast.error(err)
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="settings-tab data-tab">
    <section class="block">
      <h2 class="panel-title">{{ t('accountData.downloadTitle') }}</h2>
      <p class="hint">{{ t('accountData.downloadHint') }}</p>
      <div>
        <Button :label="t('accountData.download')" icon="mdi mdi-download" :loading="downloading" @click="download" />
      </div>
    </section>

    <section class="block danger">
      <h2 class="panel-title">{{ t('accountDeletion.title') }}</h2>
      <p class="hint">{{ t('accountData.deleteHint') }}</p>
      <div>
        <Button
          :label="t('accountData.deleteOpen')"
          icon="mdi mdi-account-remove-outline"
          severity="danger"
          outlined
          @click="deleting = true"
        />
      </div>
    </section>

    <AccountDeletionDialog v-model:visible="deleting" @download="download" />
  </div>
</template>

<style scoped lang="scss">
.data-tab {
  gap: var(--space-6);
}

.block {
  display: grid;
  gap: var(--space-2);
}

.danger {
  padding-top: var(--space-4);
  border-top: 1px solid var(--p-content-border-color);
}
</style>
