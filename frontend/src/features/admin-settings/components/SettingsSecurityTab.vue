<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { getSecuritySettings, saveSecuritySettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

type SecuritySettings = Schemas['SecuritySettingsSchema']
type NumberField = Exclude<keyof SecuritySettings, 'enforce_totp' | 'enable_api_key_auth'>

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const { form, loaded, adopt, value } = useSettingsForm<SecuritySettings>(
  {
    enforce_totp: false,
    enable_api_key_auth: false,
    min_password_length: null,
    session_timeout_minutes: null,
    session_max_lifetime_days: null,
    totp_trusted_device_days: null,
    max_login_attempts: null,
    lockout_duration_minutes: null,
    token_max_lifetime_days: null,
  },
  () => getSecuritySettings(),
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)

const numberFields: { key: NumberField; min: number; max?: number }[] = [
  { key: 'min_password_length', min: 8, max: 72 },
  { key: 'session_timeout_minutes', min: 5 },
  { key: 'session_max_lifetime_days', min: 1 },
  { key: 'totp_trusted_device_days', min: 0, max: 365 },
  { key: 'max_login_attempts', min: 1 },
  { key: 'lockout_duration_minutes', min: 0 },
  { key: 'token_max_lifetime_days', min: 0 },
]

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    adopt(await saveSecuritySettings(value()))
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="settings-tab" @submit.prevent="save">
    <div class="settings-fields">
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.enforce_totp" input-id="sec-enforce" :disabled="!editable" />
        <label for="sec-enforce">{{ t('settings.security.enforce_totp') }}</label>
      </div>
      <small class="field-hint">{{ t('settings.security.enforce_totpHint') }}</small>
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.enable_api_key_auth" input-id="sec-apikeys" :disabled="!editable" />
        <label for="sec-apikeys">{{ t('settings.security.enable_api_key_auth') }}</label>
      </div>
      <div v-for="f in numberFields" :key="f.key" class="field">
        <label :for="`sec-${f.key}`">{{ t(`settings.security.${f.key}`) }}</label>
        <InputNumber
          v-model="form[f.key]"
          :input-id="`sec-${f.key}`"
          :min="f.min"
          :max="f.max"
          :disabled="!editable"
          show-buttons
        />
        <small class="field-hint">{{ t(`settings.security.${f.key}Hint`) }}</small>
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>

<style scoped lang="scss">
.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}
</style>
