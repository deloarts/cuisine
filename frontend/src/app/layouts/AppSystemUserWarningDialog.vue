<script setup lang="ts">
/**
 * Warns once per sign-in that the system account is for administration
 * only and that its session ends 15 minutes after sign-in. The store sets
 * `systemUserWarningPending`; the dialog closes only through its button,
 * which records the acknowledgement for this tab.
 */
import { useI18n } from 'vue-i18n'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const currentUser = useCurrentUserStore()
</script>

<template>
  <Dialog
    :visible="currentUser.systemUserWarningPending"
    modal
    :closable="false"
    :close-on-escape="false"
    :draggable="false"
    class="system-user-dialog"
  >
    <template #header>
      <div class="warning-header">
        <span class="mdi mdi-alert warning-icon" aria-hidden="true" />
        <span>{{ t('systemUserWarning.title') }}</span>
      </div>
    </template>

    <p>{{ t('systemUserWarning.body') }}</p>
    <p>{{ t('systemUserWarning.countdown') }}</p>

    <template #footer>
      <Button
        :label="t('systemUserWarning.acknowledge')"
        severity="warn"
        @click="currentUser.acknowledgeSystemUserWarning()"
      />
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
.system-user-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.warning-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
}

.warning-icon {
  color: var(--p-orange-500);
  font-size: var(--font-size-lg);
}

p {
  margin: 0 0 var(--space-3);
  line-height: 1.5;

  &:last-child {
    margin-bottom: 0;
  }
}
</style>
