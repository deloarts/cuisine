<script setup lang="ts">
/**
 * The USDA FoodData Central lookup in the ingredient editor. Without a key
 * of its own the instance uses USDA's shared demo key, which is rate
 * limited; a free personal key from api.data.gov lifts that.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { getIntegrationSettings, saveIntegrationSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const { form, loaded, adopt } = useSettingsForm<Schemas['IntegrationSettingsResponse']>(
  { usda_enabled: false, usda_api_key_set: false, usda_uses_demo_key: false },
  () => getIntegrationSettings(),
)
// Empty keeps the stored key, since the API never sends it out.
const apiKey = ref('')
const DEMO_KEY = 'DEMO_KEY'
const saving = ref(false)

async function save(useDemoKey = false) {
  if (!loaded.value) return
  saving.value = true
  try {
    adopt(
      await saveIntegrationSettings({ usda_enabled: form.value.usda_enabled, usda_api_key: useDemoKey ? DEMO_KEY : apiKey.value || null }),
    )
    apiKey.value = ''
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="settings-tab" @submit.prevent="save()">
    <h2 class="panel-title">{{ t('integrations.usdaTitle') }}</h2>
    <p class="hint">{{ t('integrations.usdaHint') }}</p>
    <div class="settings-fields">
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.usda_enabled" input-id="usda-enabled" :disabled="!canWrite || !loaded" />
        <label for="usda-enabled">{{ t('integrations.usdaEnabled') }}</label>
      </div>
      <div class="field">
        <label for="usda-key">{{ t('integrations.apiKey') }}</label>
        <Password v-model="apiKey" input-id="usda-key" :feedback="false" toggle-mask autocomplete="off" :disabled="!canWrite || !loaded" />
        <small class="field-hint">
          <template v-if="!loaded">&nbsp;</template>
          <template v-else-if="form.usda_uses_demo_key">{{ t('integrations.usesDemoKey') }}</template>
          <template v-else-if="form.usda_api_key_set">{{ t('integrations.keyStored') }}</template>
          <template v-else>{{ t('integrations.noKey') }}</template>
        </small>
      </div>
    </div>
    <div v-if="canWrite" class="actions">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
      <Button
        v-if="!form.usda_uses_demo_key"
        type="button"
        :label="t('integrations.useDemoKey')"
        text
        :loading="saving"
        :disabled="!loaded"
        @click="save(true)"
      />
    </div>
  </form>
</template>

<style scoped lang="scss">
.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
