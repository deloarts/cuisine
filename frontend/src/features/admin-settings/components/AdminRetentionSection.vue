<script setup lang="ts">
/**
 * How long Cuisine keeps its records: security log, agent calls, webhook
 * deliveries and recipe revisions. A nightly purge deletes what is older;
 * 0 days keeps everything. The privacy statement's default draft names these
 * periods, so a change here belongs in the next statement too.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { getRetentionSettings, saveRetentionSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import { keepsForever, RETENTION_MAX_DAYS } from '@/features/admin-settings/operationsRules'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

type Retention = Schemas['RetentionSettingsSchema']

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const { form, loaded, adopt, value } = useSettingsForm<Retention>(
  { security_log_days: null, agent_calls_days: null, webhook_deliveries_days: null, recipe_revisions_days: null },
  () => getRetentionSettings(),
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)
const keys: (keyof Retention)[] = ['security_log_days', 'agent_calls_days', 'webhook_deliveries_days', 'recipe_revisions_days']

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    adopt(await saveRetentionSettings(value()))
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
    <h2 class="panel-title">{{ t('adminArea.retention.title') }}</h2>
    <p class="hint">{{ t('adminArea.retention.hint') }}</p>
    <div class="form-grid">
      <div v-for="key in keys" :key="key" class="field">
        <label :for="`retention-${key}`">{{ t(`adminArea.retention.${key}`) }}</label>
        <InputNumber
          v-model="form[key]"
          :input-id="`retention-${key}`"
          :min="0"
          :max="RETENTION_MAX_DAYS"
          :suffix="` ${t('adminArea.retention.days')}`"
          :disabled="!editable"
          fluid
        />
        <small class="field-hint">
          {{ !loaded ? '\u00a0' : keepsForever(form[key]) ? t('adminArea.retention.forever') : t('adminArea.retention.purged', { days: form[key] }) }}
        </small>
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>
