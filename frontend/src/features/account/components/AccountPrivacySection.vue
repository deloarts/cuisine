<script setup lang="ts">
/**
 * The instance's privacy mode, read-only, as the administrator set it, and,
 * when users may choose, the visibility the user's new recipes start with
 * (paired instances only while peering is on, public only while the
 * instance allows public recipes). Below, whether the
 * user's display name is shown on their public recipes and on recipes shared
 * with paired instances; both are stored now and used once those exist.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  effectiveDefault,
  effectiveVisibility,
  isVisibility,
  offeredVisibilities,
  privacyMode,
  type PrivacySettings,
  type RecipeVisibility,
} from '@/shared/cookbook/privacyMode'
import { getPrivacySettings, updateProfile } from '@/features/account/api/account'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'

const { t } = useI18n()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const publicInfo = usePublicInfoStore()
const peering = computed(() => publicInfo.info?.features.peering ?? false)

const settings = ref<PrivacySettings | null>(null)
const own = ref<RecipeVisibility | null>(null)
const saving = ref(false)
const savingNames = ref(false)

const mode = computed(() => (settings.value ? privacyMode(settings.value, peering.value) : null))
const instanceDefault = computed(() => {
  const s = settings.value
  if (!s) return ''
  const value = effectiveVisibility(s.default_recipe_visibility, s.allow_public_recipes, peering.value)
  return t(`privacyMode.visibility.${value}`)
})
const options = computed(() =>
  offeredVisibilities(settings.value?.allow_public_recipes ?? false, peering.value).map((value) => ({
    value,
    label: t(`privacyMode.visibility.${value}`),
  })),
)
const showNameOnPublic = computed(() => currentUser.user?.show_name_on_public_recipes ?? false)
const showNameOnPaired = computed(() => currentUser.user?.show_name_on_paired_instances ?? true)

type NameSetting = 'show_name_on_public_recipes' | 'show_name_on_paired_instances'

async function saveName(field: NameSetting, value: boolean) {
  savingNames.value = true
  try {
    currentUser.apply(await updateProfile({ [field]: value }))
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    savingNames.value = false
  }
}

watch(
  [() => currentUser.user?.default_recipe_visibility, settings, peering],
  ([value]) => {
    if (settings.value) own.value = effectiveDefault(settings.value, value, peering.value)
    else own.value = isVisibility(value) ? value : null
  },
  { immediate: true },
)

async function save() {
  if (!own.value) return
  saving.value = true
  try {
    currentUser.apply(await updateProfile({ default_recipe_visibility: own.value }))
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    settings.value = await getPrivacySettings()
  } catch (err) {
    toast.error(err)
  }
})
</script>

<template>
  <section v-if="settings && mode" class="settings-tab">
    <h2 class="panel-title">{{ t('accountPrivacy.title') }}</h2>
    <p class="mode">
      <i class="mdi" :class="mode === 'choice' ? 'mdi-account-key-outline' : 'mdi-lock-outline'" aria-hidden="true" />
      <span>
        <strong>{{ t(`privacyMode.modes.${mode}`) }}</strong>
        {{ t(`privacyMode.modeText.${mode}`, { visibility: instanceDefault }) }}
      </span>
    </p>
    <p class="hint">{{ t('accountPrivacy.adminDecides') }}</p>

    <div v-if="mode === 'choice'" class="own-default">
      <div class="field">
        <label id="own-visibility-label" for="own-visibility">{{ t('accountPrivacy.ownDefault') }}</label>
        <Select
          id="own-visibility"
          v-model="own"
          :options="options"
          option-label="label"
          option-value="value"
          aria-labelledby="own-visibility-label"
          :loading="saving"
          @update:model-value="save"
        />
        <small class="field-hint">{{ t('accountPrivacy.ownDefaultHint') }}</small>
      </div>
    </div>

    <div class="author-name">
      <h3 class="author-name-title">{{ t('accountPrivacy.authorName.title') }}</h3>
      <p class="hint">{{ t('accountPrivacy.authorName.intro') }}</p>
      <div class="field">
        <div class="toggle-field">
          <ToggleSwitch
            :model-value="showNameOnPublic"
            input-id="show-name-public"
            :disabled="savingNames"
            aria-describedby="show-name-public-hint"
            @update:model-value="(v: boolean) => saveName('show_name_on_public_recipes', v)"
          />
          <label for="show-name-public">{{ t('accountPrivacy.authorName.public') }}</label>
        </div>
        <small id="show-name-public-hint" class="field-hint">{{ t('accountPrivacy.authorName.publicHint') }}</small>
      </div>
      <div class="field">
        <div class="toggle-field">
          <ToggleSwitch
            :model-value="showNameOnPaired"
            input-id="show-name-paired"
            :disabled="savingNames"
            aria-describedby="show-name-paired-hint"
            @update:model-value="(v: boolean) => saveName('show_name_on_paired_instances', v)"
          />
          <label for="show-name-paired">{{ t('accountPrivacy.authorName.paired') }}</label>
        </div>
        <small id="show-name-paired-hint" class="field-hint">{{ t('accountPrivacy.authorName.pairedHint') }}</small>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.mode {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin: 0;
}

.own-default {
  display: grid;
  gap: var(--space-3);
  max-width: 32rem;
}

.author-name {
  display: grid;
  gap: var(--space-3);
  max-width: 32rem;
}

.author-name-title {
  margin: 0;
  font-size: var(--font-size-lg);
}

.toggle-field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
