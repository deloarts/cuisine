<script setup lang="ts">
/**
 * One legal page, the imprint or the privacy statement, in both content
 * languages. Publishing adds a new version and never edits an old one; a new
 * privacy statement version asks everyone to acknowledge it again. The
 * privacy statement can start from a default draft written from what this
 * instance actually does, and its privacy mode section is always generated
 * by the backend where the `{{ privacy_mode }}` marker stands.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'openvue/useconfirm'

import LegalText from '@/shared/components/legal/LegalText.vue'
import {
  cleanTexts,
  currentVersion,
  hasChanges,
  LEGAL_LOCALES,
  localesWithoutMarker,
  missingLocales,
  PRIVACY_MODE_MARKER,
  type LegalKind,
  type LegalTexts,
  type LegalVersion,
} from '@/features/admin-settings/legalRules'
import { adminLegalApi } from '@/features/admin-settings/api/legal'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { formatDateTime } from '@/core/utils/dates'
import ContentCard from '@/shared/components/ContentCard.vue'

const props = defineProps<{ kind: LegalKind }>()

const { t } = useI18n()
const toast = useAppToast()
const confirm = useConfirm()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

const versions = ref<LegalVersion[]>([])
const form = ref<LegalTexts>({ 'de-AT': '', 'en-GB': '' })
const activeLocale = ref<string>('de-AT')
const preview = ref(false)
const loading = ref(false)
const loaded = ref(false)
const publishing = ref(false)
const drafting = ref(false)

const isPrivacy = computed(() => props.kind === 'privacy')
const current = computed(() => currentVersion(versions.value))
const history = computed(() => [...versions.value].sort((a, b) => b.version - a.version))
const changed = computed(() => hasChanges(form.value, current.value))
const missing = computed(() => missingLocales(form.value))
const withoutMarker = computed(() => (isPrivacy.value ? localesWithoutMarker(form.value) : []))

const languageName = (locale: string) => t(locale === 'de-AT' ? 'contentLocales.deAT' : 'contentLocales.enGB')
const languages = (locales: string[]) => locales.map(languageName).join(', ')

function modeLabel(version: LegalVersion): string {
  if (!version.privacy_mode) return ''
  const mode = t(`adminArea.legal.modes.${version.privacy_mode}`)
  const label = version.default_visibility
    ? t('adminArea.legal.modeWithDefault', {
        mode,
        visibility: t(`adminArea.privacy.visibility.${version.default_visibility}`),
      })
    : mode
  const parts = [label]
  if (version.allow_public_recipes) parts.push(t('adminArea.legal.publicAllowed'))
  if (version.peering_enabled) parts.push(t('adminArea.legal.peeringEnabled'))
  return parts.join(', ')
}

async function load() {
  loading.value = true
  try {
    versions.value = await adminLegalApi.versions(props.kind)
    const latest = currentVersion(versions.value)
    form.value = { 'de-AT': latest?.texts['de-AT'] ?? '', 'en-GB': latest?.texts['en-GB'] ?? '' }
    loaded.value = true
  } catch (err) {
    toast.error(err)
  } finally {
    loading.value = false
  }
}

async function fillDraft() {
  drafting.value = true
  try {
    const drafts = await Promise.all(
      LEGAL_LOCALES.map((locale) => adminLegalApi.privacyDraft(locale)),
    )
    const next: LegalTexts = { ...form.value }
    for (const draft of drafts) next[draft.locale] = draft.body
    form.value = next
    preview.value = false
    toast.success(t('adminArea.legal.draftFilled'))
  } catch (err) {
    toast.error(err)
  } finally {
    drafting.value = false
  }
}

function generateDraft() {
  if (!Object.keys(cleanTexts(form.value)).length) {
    void fillDraft()
    return
  }
  confirm.require({
    header: t('common.confirm'),
    message: t('adminArea.legal.draftReplace'),
    acceptProps: { label: t('adminArea.legal.generate') },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void fillDraft(),
  })
}

async function publish() {
  publishing.value = true
  try {
    await adminLegalApi.publish(props.kind, cleanTexts(form.value))
    toast.success(t('adminArea.legal.published'))
    await load()
  } catch (err) {
    toast.error(err)
  } finally {
    publishing.value = false
  }
}

function confirmPublish() {
  if (!changed.value) return
  const next = (current.value?.version ?? 0) + 1
  confirm.require({
    header: t('common.confirm'),
    message: isPrivacy.value
      ? t('adminArea.legal.publishPrivacy', { version: next })
      : t('adminArea.legal.publishImprint', { version: next }),
    acceptProps: { label: t('adminArea.legal.publish'), severity: isPrivacy.value ? 'warn' : undefined },
    rejectProps: { label: t('common.cancel'), text: true },
    accept: () => void publish(),
  })
}

onMounted(() => void load())
</script>

<template>
  <section class="settings-tab legal">
    <h2 class="panel-title">{{ t(`adminArea.legal.${isPrivacy ? 'privacyTitle' : 'imprintTitle'}`) }}</h2>
    <p class="hint">{{ t(`adminArea.legal.${isPrivacy ? 'privacyHint' : 'imprintHint'}`) }}</p>

    <p v-if="current" class="current">
      <Tag :value="t('adminArea.legal.version', { version: current.version })" severity="info" />
      {{ t('adminArea.legal.publishedAt', { date: formatDateTime(current.published_at) }) }}
      <template v-if="isPrivacy && current.privacy_mode"> · {{ modeLabel(current) }}</template>
    </p>
    <Message v-else-if="loaded" severity="info" :closable="false">
      {{ t(`adminArea.legal.${isPrivacy ? 'noPrivacy' : 'noImprint'}`) }}
    </Message>
    <p v-else class="current">&nbsp;</p>

    <div class="toolbar">
      <SelectButton
        v-model="activeLocale"
        :options="[...LEGAL_LOCALES]"
        :option-label="languageName"
        :allow-empty="false"
        :aria-label="t('adminArea.legal.language')"
      />
      <ToggleButton
        v-model="preview"
        :on-label="t('adminArea.legal.edit')"
        :off-label="t('adminArea.legal.preview')"
        on-icon="mdi mdi-pencil"
        off-icon="mdi mdi-eye-outline"
      />
      <Button
        v-if="isPrivacy && canWrite"
        :label="t('adminArea.legal.generate')"
        icon="mdi mdi-file-document-edit-outline"
        text
        :loading="drafting"
        :disabled="!loaded"
        @click="generateDraft"
      />
    </div>

    <div v-for="locale in LEGAL_LOCALES" v-show="activeLocale === locale" :key="locale" class="editor">
      <ContentCard v-if="preview" class="preview">
        <LegalText v-if="form[locale]?.trim()" :text="form[locale]" />
        <p v-else class="hint">{{ t('adminArea.legal.empty') }}</p>
      </ContentCard>
      <div v-else class="field">
        <label :for="`legal-${kind}-${locale}`" class="visually-hidden">
          {{ t('adminArea.legal.textIn', { language: languageName(locale) }) }}
        </label>
        <Textarea
          :id="`legal-${kind}-${locale}`"
          v-model="form[locale]"
          rows="14"
          auto-resize
          class="markdown"
          :disabled="!canWrite || !loaded"
        />
        <small class="field-hint">{{ t('adminArea.legal.markdownHint') }}</small>
      </div>
    </div>

    <Message v-if="missing.length && missing.length < LEGAL_LOCALES.length" severity="secondary" size="small" :closable="false">
      {{ t('adminArea.legal.missing', { languages: languages(missing) }) }}
    </Message>
    <Message v-if="withoutMarker.length" severity="secondary" size="small" :closable="false">
      {{ t('adminArea.legal.noMarker', { languages: languages(withoutMarker), marker: PRIVACY_MODE_MARKER }) }}
    </Message>

    <div v-if="canWrite" class="actions">
      <Button
        :label="t('adminArea.legal.publish')"
        icon="mdi mdi-publish"
        :disabled="!changed"
        :loading="publishing"
        @click="confirmPublish"
      />
    </div>

    <details v-if="history.length" class="history">
      <summary>{{ t('adminArea.legal.history', { count: history.length }) }}</summary>
      <ul class="versions">
        <li v-for="v in history" :key="v.id">
          <strong>{{ t('adminArea.legal.version', { version: v.version }) }}</strong>
          · {{ formatDateTime(v.published_at) }}
          <template v-if="v.privacy_mode"> · {{ modeLabel(v) }}</template>
          · {{ languages(Object.keys(cleanTexts(v.texts))) }}
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped lang="scss">
.current {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.markdown {
  width: 100%;
  font-family: ui-monospace, monospace;
  font-size: var(--font-size-sm);
}

.preview {
  max-height: 32rem;
  overflow-y: auto;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.history summary {
  min-height: 2.75rem;
  cursor: pointer;
}

.versions {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding-left: var(--space-4);
}
</style>
