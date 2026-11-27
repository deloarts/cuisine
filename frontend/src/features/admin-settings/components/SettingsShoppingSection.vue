<script setup lang="ts">
/**
 * The two shopping list mode settings: how long ticked items stay under
 * "Recently bought" on continuous lists, and after how many unused days a
 * normal list deletes itself (0 never). A purge applies both every 15
 * minutes.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { getShoppingSettings, saveShoppingSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

type Shopping = Schemas['ShoppingSettingsSchema']

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const { form, loaded, adopt, value } = useSettingsForm<Shopping>(
  { bought_window_hours: null, idle_list_days: null },
  () => getShoppingSettings(),
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    adopt(await saveShoppingSettings(value()))
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
    <h2 class="panel-title">{{ t('adminArea.shopping.title') }}</h2>
    <p class="hint">{{ t('adminArea.shopping.hint') }}</p>
    <div class="form-grid">
      <div class="field">
        <label for="shopping-window">{{ t('adminArea.shopping.window') }}</label>
        <InputNumber
          v-model="form.bought_window_hours"
          input-id="shopping-window"
          :min="1"
          :max="720"
          :suffix="` ${t('adminArea.shopping.hours')}`"
          :disabled="!editable"
          fluid
        />
        <small class="field-hint">
          {{ loaded ? t('adminArea.shopping.windowHint', { hours: form.bought_window_hours }) : '\u00a0' }}
        </small>
      </div>
      <div class="field">
        <label for="shopping-idle">{{ t('adminArea.shopping.idleDays') }}</label>
        <InputNumber
          v-model="form.idle_list_days"
          input-id="shopping-idle"
          :min="0"
          :max="3650"
          :suffix="` ${t('adminArea.shopping.days')}`"
          :disabled="!editable"
          fluid
        />
        <small class="field-hint">
          {{
            !loaded
              ? '\u00a0'
              : form.idle_list_days === 0
              ? t('adminArea.shopping.idleOff')
              : t('adminArea.shopping.idleHint', { days: form.idle_list_days })
          }}
        </small>
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>
