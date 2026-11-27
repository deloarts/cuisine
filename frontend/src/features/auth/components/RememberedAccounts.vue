<script setup lang="ts">
// The other accounts that signed in on this device, under the one the sign-in
// page opened on, so switching takes one tap. Part of the sign-in card, which
// keeps its fixed dark look in every theme.
import { useI18n } from 'vue-i18n'

import type { RememberedAccount } from '@/features/auth/utils/rememberedAccounts'
import UserAvatar from '@/shared/components/UserAvatar.vue'

defineProps<{ accounts: RememberedAccount[]; disabled: boolean }>()
const emit = defineEmits<{ select: [account: RememberedAccount] }>()

const { t } = useI18n()
</script>

<template>
  <div v-if="accounts.length > 0" class="other-accounts">
    <span class="other-accounts-label">{{ t('auth.chooser.otherAccounts') }}</span>
    <button
      v-for="account in accounts"
      :key="account.userId"
      type="button"
      class="other-account"
      :disabled="disabled"
      :data-testid="`login-account-${account.userId}`"
      @click="emit('select', account)"
    >
      <UserAvatar class="other-avatar" :name="account.displayName" :src="account.avatar" />
      {{ account.displayName }}
    </button>
  </div>
</template>

<style scoped lang="scss">
.other-accounts {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-top: var(--space-3);
  border-top: 1px solid var(--auth-line);
}

.other-accounts-label {
  color: var(--auth-text-muted);
  font-size: var(--font-size-xs);
  text-align: center;
}

.other-account {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  padding: var(--space-1) var(--space-2);
  background: none;
  border: none;
  border-radius: 9px;
  cursor: pointer;
  color: var(--auth-text);
  font: inherit;
  font-size: var(--font-size-sm);
  text-align: left;
  transition: background 0.15s ease;

  &:hover:not(:disabled) {
    background: var(--auth-field);
  }

  &:focus-visible {
    outline: 2px solid var(--auth-focus-border);
    outline-offset: 2px;
  }

  &:disabled {
    cursor: default;
  }
}

.other-avatar {
  --avatar-size: 1.75rem;
  --avatar-background: var(--auth-field);
  --avatar-color: var(--auth-text-strong);
}
</style>
