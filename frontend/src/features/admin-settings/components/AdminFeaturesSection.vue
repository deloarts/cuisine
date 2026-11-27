<script setup lang="ts">
/**
 * The feature switches in one place: AI agents, webhooks, households, dinner
 * guests, the USDA lookup and peering with other instances. The switches in
 * the agents, notifications and nutrition sections mirror these, so a change
 * here shows there too. Switching peering changes who may receive recipes
 * (recipes set to paired instances go out only while it is on), so it
 * publishes a new privacy statement version and asks first.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { getFeatureSettings, saveFeatureSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

type Features = Schemas['FeatureSettingsSchema']

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const publicInfo = usePublicInfoStore()
const confirm = useConfirm()
// The saved peering switch, to tell whether a save changes it.
const savedPeering = ref(false)

const { form, loaded, adopt, value } = useSettingsForm<Features>(
  { agents: false, webhooks: false, households: false, dinner_guests: false, usda: false, peering: false },
  async () => {
    const stored = await getFeatureSettings()
    savedPeering.value = stored.peering
    return stored
  },
)
const saving = ref(false)
const keys: (keyof Features)[] = ['agents', 'webhooks', 'households', 'dinner_guests', 'usda', 'peering']

function save() {
  if (!loaded.value) return
  if (form.value.peering === savedPeering.value) {
    void store()
    return
  }
  confirm.require({
    message: t('adminArea.features.peeringConfirm'),
    header: t('common.confirm'),
    acceptProps: { label: t('common.save'), severity: 'warn' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void store(),
  })
}

async function store() {
  saving.value = true
  try {
    const stored = await saveFeatureSettings(value())
    adopt(stored)
    savedPeering.value = stored.peering
    toast.success(t('common.saved'))
    void publicInfo.fetch()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="settings-tab" @submit.prevent="save">
    <h2 class="panel-title">{{ t('adminArea.features.title') }}</h2>
    <p class="hint">{{ t('adminArea.features.hint') }}</p>
    <div class="switches">
      <div v-for="key in keys" :key="key" class="switch">
        <ToggleSwitch v-model="form[key]" :input-id="`feature-${key}`" :disabled="!canWrite || !loaded" />
        <label :for="`feature-${key}`" class="switch-label">
          <span>{{ t(`adminArea.features.${key}`) }}</span>
          <small class="field-hint">{{ t(`adminArea.features.${key}Hint`) }}</small>
        </label>
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>

<style scoped lang="scss">
.switches {
  display: grid;
  gap: var(--space-3);
}

.switch {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.switch-label {
  display: grid;
}
</style>
