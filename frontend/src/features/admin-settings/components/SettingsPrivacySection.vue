<script setup lang="ts">
/**
 * Who sees a new recipe by default, whether people may choose another
 * visibility for their own recipes, whether public recipes are allowed and
 * whether search engines may index them.
 * A public default needs the public switch, so switching it off moves a
 * public default back to the instance. A paired instances default is offered
 * only while peering is on.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import { getPrivacySettings, savePrivacySettings } from '@/features/admin-settings/api/settings'
import { useSettingsForm } from '@/features/admin-settings/useSettingsForm'
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import { offeredVisibilities } from '@/shared/cookbook/privacyMode'

const { t } = useI18n()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)
const confirm = useConfirm()
const publicInfo = usePublicInfoStore()
const peering = computed(() => publicInfo.info?.features.peering ?? false)
type Privacy = Schemas['PrivacySettingsSchema']
// The saved values, to tell whether a save changes the privacy mode.
const saved = ref<Privacy | null>(null)
const { form, loaded, adopt, value } = useSettingsForm<Privacy>(
  {
    default_recipe_visibility: null,
    users_may_change_visibility: false,
    allow_public_recipes: false,
    index_public_recipes: false,
  },
  async () => {
    const stored = await getPrivacySettings()
    saved.value = { ...stored }
    return stored
  },
)
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)

const visibilities = computed(() =>
  offeredVisibilities(
    form.value.allow_public_recipes,
    peering.value || form.value.default_recipe_visibility === 'peers',
  ).map((v) => ({
    value: v,
    label: t(`adminArea.privacy.visibility.${v}`),
  })),
)

watch(
  () => form.value.allow_public_recipes,
  (allowed) => {
    if (loaded.value && !allowed && form.value.default_recipe_visibility === 'public') {
      form.value.default_recipe_visibility = 'instance'
    }
  },
)

// Changing the mode creates a new privacy statement version that everyone
// has to acknowledge before they can go on, so the admin confirms it first.
// The search engine switch alone changes no statement and saves at once.
function save() {
  if (!loaded.value) return
  const f = form.value
  const changed =
    f.default_recipe_visibility !== saved.value?.default_recipe_visibility ||
    f.users_may_change_visibility !== saved.value?.users_may_change_visibility ||
    f.allow_public_recipes !== saved.value?.allow_public_recipes
  if (!changed) {
    if (f.index_public_recipes !== saved.value?.index_public_recipes) void store()
    return
  }
  confirm.require({
    message: t('adminArea.privacy.confirmChange'),
    header: t('common.confirm'),
    acceptProps: { label: t('common.save'), severity: 'warn' },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void store(),
  })
}

async function store() {
  if (!loaded.value) return
  saving.value = true
  try {
    const stored = await savePrivacySettings(value())
    saved.value = { ...stored }
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
    <h2 class="panel-title">{{ t('adminArea.privacy.title') }}</h2>
    <div class="settings-fields">
      <div class="field">
        <label id="privacy-default-label" for="privacy-default">{{ t('adminArea.privacy.default') }}</label>
        <Select
          id="privacy-default"
          v-model="form.default_recipe_visibility"
          :options="visibilities"
          option-label="label"
          option-value="value"
          aria-labelledby="privacy-default-label"
          :disabled="!editable"
        />
        <small class="field-hint">{{ t('adminArea.privacy.defaultHint') }}</small>
      </div>
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.users_may_change_visibility" input-id="privacy-change" :disabled="!editable" />
        <label for="privacy-change">{{ t('adminArea.privacy.mayChange') }}</label>
      </div>
      <div class="field">
        <div class="toggle-field">
          <ToggleSwitch
            v-model="form.allow_public_recipes"
            input-id="privacy-public"
            :disabled="!editable"
            aria-describedby="privacy-public-hint"
          />
          <label for="privacy-public">{{ t('adminArea.privacy.allowPublic') }}</label>
        </div>
        <small id="privacy-public-hint" class="field-hint">{{ t('adminArea.privacy.allowPublicHint') }}</small>
      </div>
      <div class="field">
        <div class="toggle-field">
          <ToggleSwitch
            v-model="form.index_public_recipes"
            input-id="privacy-index"
            :disabled="!editable || !form.allow_public_recipes"
            aria-describedby="privacy-index-hint"
          />
          <label for="privacy-index">{{ t('adminArea.privacy.indexPublic') }}</label>
        </div>
        <small id="privacy-index-hint" class="field-hint">{{ t('adminArea.privacy.indexPublicHint') }}</small>
      </div>
    </div>
    <div v-if="canWrite">
      <Button type="submit" :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" />
    </div>
  </form>
</template>
