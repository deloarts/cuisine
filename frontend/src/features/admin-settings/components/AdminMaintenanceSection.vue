<script setup lang="ts">
/**
 * Maintenance mode: Cuisine stays readable but refuses every change, with a
 * banner for everyone. Admins switch it here; the maintenance sidecar does
 * the same during upgrades and restores. Switching it on or off is
 * confirmed first, since it affects everyone at once.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { useMaintenance } from '@/shared/maintenance/useMaintenance'
import { getMaintenanceSettings, saveMaintenanceSettings } from '@/features/admin-settings/api/settings'
import {
  cleanMessages,
  maintenanceChange,
  maintenanceMessageMissing,
  type Maintenance,
  type MaintenanceForm,
} from '@/features/admin-settings/operationsRules'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const { refresh: refreshBanner } = useMaintenance()

const saved = ref<Maintenance | null>(null)
const form = ref<MaintenanceForm>({ enabled: false, messages: {} })
const saving = ref(false)
// The fields render at once and stay disabled until the stored state is in.
const editable = computed(() => canWrite && saved.value !== null)
const locales = ['de-AT', 'en-GB'] as const

const change = computed(() => (saved.value ? maintenanceChange(saved.value, form.value) : null))
const missingMessage = computed(() => maintenanceMessageMissing(form.value))

function adopt(value: Maintenance) {
  saved.value = value
  form.value = { enabled: value.enabled, messages: { ...value.messages } }
}

async function store() {
  saving.value = true
  try {
    adopt(
      await saveMaintenanceSettings({ enabled: form.value.enabled, messages: cleanMessages(form.value.messages) }),
    )
    toast.success(t('common.saved'))
    void refreshBanner()
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

function save() {
  const what = change.value
  if (!what) return
  if (what === 'message') {
    void store()
    return
  }
  confirm.require({
    header: t('common.confirm'),
    message: what === 'on' ? t('adminArea.maintenance.confirmOn') : t('adminArea.maintenance.confirmOff'),
    acceptProps: { label: what === 'on' ? t('adminArea.maintenance.turnOn') : t('adminArea.maintenance.turnOff'), severity: 'warn' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void store(),
  })
}

onMounted(async () => {
  try {
    adopt(await getMaintenanceSettings())
  } catch (err) {
    toast.error(err)
  }
})
</script>

<template>
  <form class="settings-tab" @submit.prevent="save">
    <h2 class="panel-title">{{ t('adminArea.maintenance.title') }}</h2>
    <p class="hint">{{ t('adminArea.maintenance.hint') }}</p>
    <Message v-if="saved?.enabled" severity="warn" :closable="false">
      {{ saved.since ? t('adminArea.maintenance.activeSince', { date: formatDateTime(saved.since) }) : t('adminArea.maintenance.active') }}
    </Message>
    <div class="settings-fields">
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.enabled" input-id="maintenance-enabled" :disabled="!editable" />
        <label for="maintenance-enabled">{{ t('adminArea.maintenance.enabled') }}</label>
      </div>
      <div v-for="locale in locales" :key="locale" class="field">
        <label :for="`maintenance-${locale}`">{{ t('adminArea.maintenance.message', { language: t(`contentLocales.${locale === 'de-AT' ? 'deAT' : 'enGB'}`) }) }}</label>
        <Textarea
          :id="`maintenance-${locale}`"
          v-model="form.messages[locale]"
          rows="2"
          auto-resize
          :disabled="!editable"
        />
      </div>
      <small v-if="saved && missingMessage" class="field-hint">{{ t('adminArea.maintenance.noMessage') }}</small>
      <small class="field-hint">{{ t('adminArea.maintenance.cli') }}</small>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!change" />
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
