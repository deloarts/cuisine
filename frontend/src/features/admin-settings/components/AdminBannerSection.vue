<script setup lang="ts">
/**
 * The one in-app banner: a short message under the header for everyone,
 * with a severity, an optional time window and whether people may close it.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { getBannerSettings, saveBannerSettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import { CONTENT_LOCALES } from '@/shared/cookbook/contentLocale'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

type Banner = Schemas['BannerSettingsSchema']

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const { form, loaded, adopt, value } = useSettingsForm<Banner>(
  { enabled: false, severity: null, messages: {}, dismissible: false },
  async () => {
    const stored = await getBannerSettings()
    fillDates(stored)
    return stored
  },
)
const editable = computed(() => canWrite && loaded.value)
const startsAt = ref<Date | null>(null)
const endsAt = ref<Date | null>(null)
const saving = ref(false)

const severities = computed(() =>
  (['info', 'warning', 'critical'] as const).map((s) => ({ value: s, label: t(`adminArea.banner.severities.${s}`) })),
)

function fillDates(banner: Banner) {
  startsAt.value = banner.starts_at ? new Date(banner.starts_at) : null
  endsAt.value = banner.ends_at ? new Date(banner.ends_at) : null
}

async function save() {
  if (!loaded.value) return
  saving.value = true
  try {
    const stored = await saveBannerSettings({
      ...value(),
      starts_at: startsAt.value?.toISOString() ?? null,
      ends_at: endsAt.value?.toISOString() ?? null,
    })
    fillDates(stored)
    adopt(stored)
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
    <h2 class="panel-title">{{ t('adminArea.banner.title') }}</h2>
    <p class="hint">{{ t('adminArea.banner.hint') }}</p>
    <div class="settings-fields">
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.enabled" input-id="banner-enabled" :disabled="!editable" />
        <label for="banner-enabled">{{ t('adminArea.banner.enabled') }}</label>
      </div>
      <div class="field">
        <label id="banner-severity-label" for="banner-severity">{{ t('adminArea.banner.severity') }}</label>
        <Select
          id="banner-severity"
          v-model="form.severity"
          :options="severities"
          option-label="label"
          option-value="value"
          aria-labelledby="banner-severity-label"
          :disabled="!editable"
        />
      </div>
      <div v-for="locale in CONTENT_LOCALES" :key="locale" class="field">
        <label :for="`banner-msg-${locale}`">
          {{ t('adminArea.banner.message') }} ({{ t(`contentLocales.${locale.replace('-', '')}`) }})
        </label>
        <Textarea
          :id="`banner-msg-${locale}`"
          v-model="form.messages[locale]"
          rows="2"
          auto-resize
          :disabled="!editable"
          fluid
        />
      </div>
      <div class="field">
        <label for="banner-start">{{ t('adminArea.banner.startsAt') }}</label>
        <DatePicker v-model="startsAt" input-id="banner-start" show-time hour-format="24" show-button-bar :disabled="!editable" />
      </div>
      <div class="field">
        <label for="banner-end">{{ t('adminArea.banner.endsAt') }}</label>
        <DatePicker v-model="endsAt" input-id="banner-end" show-time hour-format="24" show-button-bar :disabled="!editable" />
      </div>
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.dismissible" input-id="banner-dismissible" :disabled="!editable" />
        <label for="banner-dismissible">{{ t('adminArea.banner.dismissible') }}</label>
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
