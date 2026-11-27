<script setup lang="ts">
/**
 * The user's profile, look and recipe preferences. Every change saves on its
 * own: a switch, a choice or a colour at once, a text field when the user
 * leaves it or presses Enter, so a half-typed address is never sent. Only
 * the changed fields go out, and a short status line says when they are saved.
 */
import { onBeforeUnmount, reactive, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { PRIMARY_COLORS, SURFACES } from '@/core/config/colorPalettes'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import type { Language, ThemePreset, ThemePrimary, ThemeSurface } from '@/core/types/user'
import type { AmountStyle } from '@/features/recipes/utils/scaling'
import { removeAvatar, updateProfile, uploadAvatar } from '@/features/account/api/account'
import UserAvatar from '@/shared/components/UserAvatar.vue'

const { t } = useI18n()
const toast = useAppToast()
const currentUser = useCurrentUserStore()

interface ProfileForm {
  full_name: string
  nickname: string
  show_nickname: boolean
  email: string
  language: Language
  theme_preset: ThemePreset
  theme_primary: ThemePrimary
  theme_surface: ThemeSurface
  theme_dark_mode: boolean
  recipe_show_tips: boolean
  recipe_show_notes: boolean
  recipe_show_cooked: boolean
  recipe_show_rating: boolean
  recipe_highlight_mentions: boolean
  keep_screen_on: boolean
  amount_style: AmountStyle
}

const form = reactive<ProfileForm>({
  full_name: '',
  nickname: '',
  show_nickname: false,
  email: '',
  language: 'enGB',
  theme_preset: 'Aura',
  theme_primary: 'cuisine',
  theme_surface: 'neutral',
  theme_dark_mode: false,
  recipe_show_tips: true,
  recipe_show_notes: true,
  recipe_show_cooked: true,
  recipe_show_rating: true,
  recipe_highlight_mentions: true,
  keep_screen_on: true,
  amount_style: 'decimals',
})
const saving = ref(false)
const saved = ref(false)
// The text fields are only sent on blur or Enter; every other field at once.
const TEXT_FIELDS = ['full_name', 'nickname', 'email'] as const
let pending: ReturnType<typeof setTimeout> | undefined

watch(
  () => currentUser.user,
  (user) => {
    // A save in flight answers with the user, which must not undo what was
    // typed meanwhile; the answer of the last save fills the form.
    if (!user || saving.value || pending) return
    Object.assign(form, {
      full_name: user.full_name,
      nickname: user.nickname ?? '',
      show_nickname: user.show_nickname,
      email: user.email,
      language: user.language,
      theme_preset: user.theme_preset,
      theme_primary: user.theme_primary,
      theme_surface: user.theme_surface,
      theme_dark_mode: user.theme_dark_mode,
      recipe_show_tips: user.recipe_show_tips,
      recipe_show_notes: user.recipe_show_notes,
      recipe_show_cooked: user.recipe_show_cooked,
      recipe_show_rating: user.recipe_show_rating,
      recipe_highlight_mentions: user.recipe_highlight_mentions,
      keep_screen_on: user.keep_screen_on,
      amount_style: user.amount_style,
    })
  },
  { immediate: true },
)

const languages = [
  { value: 'deAT', label: 'Deutsch' },
  { value: 'enGB', label: 'English' },
]
const presets: ThemePreset[] = ['Aura', 'Lara', 'Material', 'Nora']
// The cards below a recipe, in the order the recipe page shows them.
const recipeCards = [
  { field: 'recipe_show_tips', label: 'recipeCards.tips', hint: 'recipeCards.tipsHint' },
  { field: 'recipe_show_notes', label: 'recipeCards.notes', hint: null },
  { field: 'recipe_show_cooked', label: 'recipeCards.cooked', hint: 'recipeCards.cookedHint' },
  { field: 'recipe_show_rating', label: 'recipeCards.rating', hint: null },
] as const
// How small metric amounts read in recipes, with an example of each.
const amountStyles = [
  { value: 'decimals', label: 'amountStyle.decimals' },
  { value: 'fractions', label: 'amountStyle.fractions' },
] as const

// The avatar is saved as soon as it is picked or removed, apart from the form.
const avatarBusy = ref(false)
const avatarInput = useTemplateRef<HTMLInputElement>('avatar-input')

function pickAvatar() {
  avatarInput.value?.click()
}

async function changeAvatar(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarBusy.value = true
  try {
    currentUser.apply(await uploadAvatar(file))
  } catch (err) {
    toast.error(err)
  } finally {
    avatarBusy.value = false
    input.value = ''
  }
}

async function clearAvatar() {
  avatarBusy.value = true
  try {
    currentUser.apply(await removeAvatar())
  } catch (err) {
    toast.error(err)
  } finally {
    avatarBusy.value = false
  }
}

/** The fields that differ from the saved user, text fields only when asked. */
function changes(withText: boolean): Partial<ProfileForm> {
  const user = currentUser.user
  if (!user) return {}
  const stored: ProfileForm = { ...form, ...user, nickname: user.nickname ?? '' }
  const diff: Partial<ProfileForm> = {}
  for (const key of Object.keys(form) as (keyof ProfileForm)[]) {
    if (!withText && (TEXT_FIELDS as readonly string[]).includes(key)) continue
    if (form[key] !== stored[key]) Object.assign(diff, { [key]: form[key] })
  }
  return diff
}

async function save(withText = false) {
  clearTimeout(pending)
  pending = undefined
  const body = changes(withText)
  if (!Object.keys(body).length) return
  saving.value = true
  saved.value = false
  try {
    currentUser.apply(await updateProfile(body))
    saved.value = true
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

/** Saves a text field's change, on blur or Enter. */
function commitText() {
  void save(true)
}

// Switches, choices and colours save a moment after they change, so a quick
// series of clicks goes out as one request.
watch(
  () => ({ ...form }),
  () => {
    if (!Object.keys(changes(false)).length) return
    clearTimeout(pending)
    pending = setTimeout(() => void save(false), 250)
  },
)

onBeforeUnmount(() => {
  if (pending) void save(false)
})
</script>

<template>
  <form class="settings-tab" @submit.prevent="commitText">
    <div class="profile-head">
      <h2 class="panel-title">{{ t('account.profile.title') }}</h2>
      <small class="save-status" aria-live="polite" data-testid="profile-save-status">
        <template v-if="saving">{{ t('common.saving') }}</template>
        <template v-else-if="saved">{{ t('common.saved') }}</template>
      </small>
    </div>
    <div class="avatar-row">
      <UserAvatar
        class="avatar-preview"
        :name="currentUser.user?.display_name ?? ''"
        :avatar-id="currentUser.user?.avatar_id"
      />
      <div class="avatar-actions">
        <span id="profile-avatar-label" class="field-label">{{ t('account.profile.avatar') }}</span>
        <div class="avatar-buttons">
          <Button
            type="button"
            :label="avatarBusy ? t('account.profile.avatarUploading') : t('account.profile.avatarUpload')"
            icon="mdi mdi-upload"
            severity="secondary"
            text
            aria-describedby="profile-avatar-label"
            :loading="avatarBusy"
            @click="pickAvatar"
          />
          <input
            ref="avatar-input"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            hidden
            tabindex="-1"
            aria-hidden="true"
            :disabled="avatarBusy"
            @change="changeAvatar"
          />
          <Button
            v-if="currentUser.user?.avatar_id"
            type="button"
            :label="t('account.profile.avatarRemove')"
            icon="mdi mdi-delete-outline"
            severity="secondary"
            text
            :disabled="avatarBusy"
            @click="clearAvatar"
          />
        </div>
        <small class="field-hint">{{ t('account.profile.avatarHint') }}</small>
      </div>
    </div>
    <div class="form-grid">
      <div class="field">
        <label for="profile-name">{{ t('account.profile.fullName') }}</label>
        <InputText id="profile-name" v-model="form.full_name" autocomplete="name" @blur="commitText" />
      </div>
      <div class="field">
        <label for="profile-nickname">{{ t('account.profile.nickname') }}</label>
        <InputText id="profile-nickname" v-model="form.nickname" autocomplete="nickname" maxlength="64" @blur="commitText" />
      </div>
      <div class="field toggle-field nickname-toggle">
        <ToggleSwitch v-model="form.show_nickname" input-id="profile-show-nickname" :disabled="!form.nickname.trim()" />
        <div class="recipe-card-text">
          <label for="profile-show-nickname">{{ t('account.profile.showNickname') }}</label>
          <small class="field-hint">{{ t('account.profile.showNicknameHint') }}</small>
        </div>
      </div>
      <div class="field">
        <label for="profile-email">{{ t('account.profile.email') }}</label>
        <InputText
          id="profile-email"
          v-model="form.email"
          type="email"
          autocomplete="email"
          aria-describedby="profile-email-hint"
          @blur="commitText"
        />
        <small id="profile-email-hint" class="field-hint">{{ t('account.profile.emailHint') }}</small>
      </div>
      <div class="field">
        <label id="profile-language-label" for="profile-language">{{ t('account.profile.language') }}</label>
        <Select
id="profile-language"
          v-model="form.language"
          :options="languages"
          option-label="label"
          option-value="value"
          aria-labelledby="profile-language-label"
        />
      </div>
    </div>

    <h2 class="panel-title">{{ t('account.profile.appearance') }}</h2>
    <div class="form-grid">
      <div class="field">
        <label id="profile-preset-label" for="profile-preset">{{ t('account.profile.preset') }}</label>
        <Select id="profile-preset" v-model="form.theme_preset" :options="presets" aria-labelledby="profile-preset-label" />
      </div>
      <div class="field">
        <label id="profile-surface-label" for="profile-surface">{{ t('account.profile.surface') }}</label>
        <Select
id="profile-surface"
          v-model="form.theme_surface"
          :options="SURFACES.map((s) => s.name)"
          aria-labelledby="profile-surface-label"
        />
      </div>
      <div class="field">
        <span class="field-label">{{ t('account.profile.primary') }}</span>
        <div class="swatches" role="radiogroup" :aria-label="t('account.profile.primary')">
          <button
            v-for="color in PRIMARY_COLORS"
            :key="color.name"
            v-tooltip.top="color.name"
            type="button"
            role="radio"
            class="swatch"
            :class="{ selected: form.theme_primary === color.name }"
            :style="{ '--swatch': color.palette[500] }"
            :aria-checked="form.theme_primary === color.name"
            :aria-label="color.name"
            @click="form.theme_primary = color.name as ThemePrimary"
          />
        </div>
      </div>
      <div class="field toggle-field">
        <ToggleSwitch v-model="form.theme_dark_mode" input-id="profile-dark" />
        <label for="profile-dark">{{ t('account.profile.darkMode') }}</label>
      </div>
    </div>

    <h2 class="panel-title">{{ t('recipeCards.title') }}</h2>
    <p class="field-hint">{{ t('recipeCards.intro') }}</p>
    <div class="recipe-cards" data-testid="recipe-cards">
      <div v-for="card in recipeCards" :key="card.field" class="field toggle-field">
        <ToggleSwitch
          :model-value="form[card.field]"
          :input-id="`profile-${card.field}`"
          @update:model-value="(on: boolean) => (form[card.field] = on)"
        />
        <div class="recipe-card-text">
          <label :for="`profile-${card.field}`">{{ t(card.label) }}</label>
          <small v-if="card.hint" class="field-hint">{{ t(card.hint) }}</small>
        </div>
      </div>
    </div>
    <div class="form-grid">
      <div class="field">
        <label id="profile-amount-style-label" for="profile-amount-style">{{ t('amountStyle.label') }}</label>
        <Select
          id="profile-amount-style"
          v-model="form.amount_style"
          :options="amountStyles.map((s) => ({ value: s.value, label: t(s.label) }))"
          option-label="label"
          option-value="value"
          aria-labelledby="profile-amount-style-label"
        />
        <small class="field-hint">{{ t('amountStyle.hint') }}</small>
      </div>
    </div>
    <div class="field toggle-field">
      <ToggleSwitch v-model="form.recipe_highlight_mentions" input-id="profile-recipe_highlight_mentions" />
      <div class="recipe-card-text">
        <label for="profile-recipe_highlight_mentions">{{ t('mentionHighlight.label') }}</label>
        <small class="field-hint">{{ t('mentionHighlight.hint') }}</small>
      </div>
    </div>
    <div class="field toggle-field">
      <ToggleSwitch v-model="form.keep_screen_on" input-id="profile-keep_screen_on" />
      <div class="recipe-card-text">
        <label for="profile-keep_screen_on">{{ t('keepScreenOn.label') }}</label>
        <small class="field-hint">{{ t('keepScreenOn.hint') }}</small>
      </div>
    </div>
  </form>
</template>

<style scoped lang="scss">
.avatar-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.avatar-preview {
  --avatar-size: 5rem;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.avatar-buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.swatch {
  width: 1.8rem;
  height: 1.8rem;
  border-radius: 50%;
  border: 2px solid transparent;
  background: var(--swatch);
  cursor: pointer;

  &.selected {
    border-color: var(--p-text-color);
    box-shadow: 0 0 0 2px var(--p-content-background) inset;
  }

  &:focus-visible {
    outline: 2px solid var(--p-focus-ring-color);
    outline-offset: 2px;
  }
}

.toggle-field {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2);

  // The switch keeps its size and the text beside it wraps instead.
  > :first-child {
    flex-shrink: 0;
  }
}

// The label and hint are long, so the switch takes a row of its own.
.nickname-toggle {
  grid-column: 1 / -1;
  align-items: flex-start;
}

.recipe-cards {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.recipe-card-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.profile-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.save-status {
  min-height: 1lh;
  color: var(--p-text-muted-color);
}
</style>
