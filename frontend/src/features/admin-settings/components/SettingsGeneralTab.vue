<script setup lang="ts">
/**
 * The instance itself: its name and look (accent colour, the photo behind
 * the sign-in screens and the steam rising over them), the default language for new accounts, and how
 * dates, times and weeks are shown to everyone.
 */
import { computed, ref, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'

import { getGeneralSettings, saveGeneralSettings, uploadLoginBackground } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import { formatDateParts, formatTimeParts } from '@/core/utils/displayFormats'

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const publicInfo = usePublicInfoStore()

const { form, loaded, adopt, value } = useSettingsForm<Schemas['GeneralSettingsSchema']>(
  {
    instance_name: null,
    default_language: null,
    accent_color: null,
    login_steam: true,
    unit_system: null,
    date_format: null,
    time_format: null,
    first_day_of_week: null,
  },
  () => getGeneralSettings(),
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)
const uploading = ref(false)
const backgroundInput = useTemplateRef<HTMLInputElement>('background-input')
const languages = [
  { value: 'enGB', label: 'English' },
  { value: 'deAT', label: 'Deutsch' },
]
const sample = new Date(2026, 11, 24, 18, 30)
const dateFormats = (['dd.mm.yyyy', 'dd/mm/yyyy', 'yyyy-mm-dd', 'mm/dd/yyyy'] as const).map((f) => ({
  value: f,
  label: formatDateParts(sample, f),
}))
const timeFormats = (['24h', '12h'] as const).map((f) => ({ value: f, label: formatTimeParts(sample, f) }))
const weekdays = computed(() =>
  (['monday', 'saturday', 'sunday'] as const).map((d) => ({ value: d, label: t(`adminArea.general.weekdays.${d}`) })),
)
const unitSystems = computed(() => [{ value: 'metric', label: t('adminArea.general.metric') }])
const backgroundUrl = computed(() => {
  const fileId = form.value.login_background_file_id
  return fileId ? `${import.meta.env.VITE_API_URL ?? ''}/api/v1/web/files/${fileId}/content?variant=thumbnail` : null
})

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    adopt(await saveGeneralSettings(value()))
    await publicInfo.fetch()
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

// The input stays `hidden` and is opened from the button, because a focusable
// input hidden off the layout made the browser scroll the app shell on focus.
function chooseBackground() {
  backgroundInput.value?.click()
}

// Uploads the picked photo and puts its id into the form; saving the tab applies it.
async function uploadBackground(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !loaded.value) return
  uploading.value = true
  try {
    form.value.login_background_file_id = (await uploadLoginBackground(file)).id
  } catch (err) {
    toast.error(err)
  } finally {
    uploading.value = false
    input.value = ''
  }
}
</script>

<template>
  <form class="settings-tab" @submit.prevent="save">
    <div class="settings-fields">
      <div class="field">
        <label for="general-name">{{ t('settings.general.instanceName') }}</label>
        <InputText id="general-name" v-model="form.instance_name" :disabled="!editable" />
        <small class="field-hint">{{ t('settings.general.instanceNameHint') }}</small>
      </div>
      <div class="field">
        <label id="general-language-label" for="general-language">{{ t('settings.general.defaultLanguage') }}</label>
        <Select
          id="general-language"
          v-model="form.default_language"
          :options="languages"
          option-label="label"
          option-value="value"
          :disabled="!editable"
          aria-labelledby="general-language-label"
        />
      </div>
      <div class="field">
        <label for="general-accent">{{ t('adminArea.general.accent') }}</label>
        <InputText id="general-accent" v-model="form.accent_color" placeholder="#1c1c1f" :disabled="!editable" />
        <small class="field-hint">{{ t('adminArea.general.accentHint') }}</small>
      </div>
      <div class="field">
        <span id="general-background-label" class="field-label">{{ t('adminArea.general.loginBackground') }}</span>
        <div class="image-row">
          <img v-if="backgroundUrl" :src="backgroundUrl" alt="" class="background-preview" />
          <template v-if="canWrite">
            <Button
              type="button"
              :label="uploading ? t('adminArea.general.uploading') : t('adminArea.general.uploadLoginBackground')"
              icon="mdi mdi-upload"
              text
              class="image-upload"
              :disabled="!loaded || uploading"
              aria-describedby="general-background-label"
              @click="chooseBackground"
            />
            <input
              ref="background-input"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hidden
              tabindex="-1"
              aria-hidden="true"
              :disabled="!loaded"
              @change="uploadBackground"
            />
          </template>
          <Button v-if="canWrite && form.login_background_file_id" type="button" :label="t('adminArea.general.removeLoginBackground')" text size="small" @click="form.login_background_file_id = null" />
        </div>
        <small class="field-hint">{{ t('adminArea.general.loginBackgroundHint') }}</small>
      </div>
      <div class="field">
        <div class="toggle-field">
          <ToggleSwitch v-model="form.login_steam" input-id="general-steam" :disabled="!editable" />
          <label for="general-steam">{{ t('adminArea.general.loginSteam') }}</label>
        </div>
        <small class="field-hint">{{ t('adminArea.general.loginSteamHint') }}</small>
      </div>
      <div class="field">
        <label id="general-date-label" for="general-date">{{ t('adminArea.general.dateFormat') }}</label>
        <Select id="general-date" v-model="form.date_format" :options="dateFormats" option-label="label" option-value="value" aria-labelledby="general-date-label" :disabled="!editable" />
      </div>
      <div class="field">
        <label id="general-time-label" for="general-time">{{ t('adminArea.general.timeFormat') }}</label>
        <Select id="general-time" v-model="form.time_format" :options="timeFormats" option-label="label" option-value="value" aria-labelledby="general-time-label" :disabled="!editable" />
      </div>
      <div class="field">
        <label id="general-week-label" for="general-week">{{ t('adminArea.general.firstDay') }}</label>
        <Select id="general-week" v-model="form.first_day_of_week" :options="weekdays" option-label="label" option-value="value" aria-labelledby="general-week-label" :disabled="!editable" />
      </div>
      <div class="field">
        <label id="general-units-label" for="general-units">{{ t('adminArea.general.unitSystem') }}</label>
        <Select id="general-units" v-model="form.unit_system" :options="unitSystems" option-label="label" option-value="value" aria-labelledby="general-units-label" :disabled="!editable" />
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>

<style scoped lang="scss">
.toggle-field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.image-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.background-preview {
  width: 8rem;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: var(--p-content-border-radius);
}

.image-upload {
  min-height: 2.75rem;
}
</style>
