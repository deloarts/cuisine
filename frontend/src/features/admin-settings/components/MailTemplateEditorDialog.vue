<script setup lang="ts">
/**
 * Edits both languages of one mail template kind, ported from Glados: the
 * subject, the HTML body with the kind's variables to insert at the caret,
 * and a live preview the backend renders with sample values exactly as a
 * send would. The preview runs in a sandboxed iframe, since the body is a
 * full HTML document. A language can go back to its built-in default, and a
 * template file can be loaded into the editor or saved from it.
 */
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDebounceFn } from '@vueuse/core'

import { downloadText, pickFiles } from '@/shared/composables/fileTransfer'
import {
  defaultMailTemplate,
  MAIL_LOCALES,
  previewMailTemplate,
  saveMailTemplates,
  type ContentLocale,
  type MailTemplateGroup,
  type MailTemplateKind,
  type MailTemplateText,
} from '@/features/admin-settings/api/mail'
import {
  insertAtCaret,
  mailTemplateFileName,
  mailTemplateFileTarget,
  parseMailTemplateFile,
  serializeMailTemplateFile,
} from '@/features/admin-settings/mailTemplateFile'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { errorMessage } from '@/core/utils/errors'

const props = defineProps<{ group: MailTemplateGroup | null }>()
const visible = defineModel<boolean>('visible', { default: false })
const emit = defineEmits<{ saved: [] }>()

const { t } = useI18n()
const uid = useId()
const toast = useAppToast()
const canWrite = useCurrentUserStore().hasPermission(Permission.WRITE_SETTINGS)

// Hydrated on every open, so a cancelled dialog never leaks a draft into the next one.
const drafts = ref<Record<string, MailTemplateText>>({})
const locale = ref<ContentLocale>('de-AT')
const kind = computed(() => (props.group?.kind ?? 'test_mail') as MailTemplateKind)

function draft(): MailTemplateText {
  const current = drafts.value[locale.value] ?? { subject: '', body: '' }
  drafts.value[locale.value] = current
  return current
}

const subject = computed({
  get: () => drafts.value[locale.value]?.subject ?? '',
  set: (value: string) => {
    draft().subject = value
  },
})
const body = computed({
  get: () => drafts.value[locale.value]?.body ?? '',
  set: (value: string) => {
    draft().body = value
  },
})

const languageName = (l: string) => t(l === 'de-AT' ? 'contentLocales.deAT' : 'contentLocales.enGB')
const title = computed(() => t('mailSettings.editor.title', { kind: t(`mailSettings.kinds.${kind.value}.label`) }))

// ── Preview ──

const previewSubject = ref('')
const previewHtml = ref('')
const previewError = ref<string | null>(null)
const previewLoading = ref(false)

async function runPreview() {
  if (!props.group) return
  previewLoading.value = true
  previewError.value = null
  try {
    const result = await previewMailTemplate(kind.value, { subject: subject.value, body: body.value })
    previewSubject.value = result.subject
    previewHtml.value = result.html
  } catch (err) {
    previewHtml.value = ''
    previewError.value = errorMessage(err, t('mailSettings.editor.previewError'))
  } finally {
    previewLoading.value = false
  }
}

const debouncedPreview = useDebounceFn(runPreview, 400)
// Set while hydration fills the drafts, so it does not also queue a debounced
// preview; cleared on the next tick so every watcher of the update sees it.
let hydrating = false

watch([subject, body, locale], () => {
  if (!hydrating && visible.value) void debouncedPreview()
})

watch(
  visible,
  (open) => {
    if (!open || !props.group) return
    hydrating = true
    drafts.value = Object.fromEntries(
      MAIL_LOCALES.map((l) => {
        const stored = props.group?.templates.find((tpl) => tpl.locale === l)
        return [l, { subject: stored?.subject ?? '', body: stored?.body ?? '' }]
      }),
    )
    locale.value = MAIL_LOCALES[0] ?? 'de-AT'
    previewError.value = null
    void runPreview()
    void nextTick(() => {
      hydrating = false
    })
  },
  { immediate: true },
)

// ── Variables ──

const textarea = ref<HTMLTextAreaElement | null>(null)

function insertVariable(name: string) {
  const el = textarea.value
  const token = `{{ ${name} }}`
  const start = el?.selectionStart ?? body.value.length
  const end = el?.selectionEnd ?? body.value.length
  const next = insertAtCaret(body.value, start, end, token)
  body.value = next.value
  void nextTick(() => {
    el?.focus()
    el?.setSelectionRange(next.caret, next.caret)
  })
}

// ── Default, file import and export ──

const resetting = ref(false)

async function resetToDefault() {
  resetting.value = true
  try {
    const result = await defaultMailTemplate(kind.value, locale.value)
    subject.value = result.subject
    body.value = result.body
  } catch (err) {
    toast.error(err)
  } finally {
    resetting.value = false
  }
}

async function importFile() {
  const [file] = await pickFiles('.html,.htm')
  if (!file) return
  try {
    const target = mailTemplateFileTarget(file.name)
    if (target && target.kind !== kind.value) {
      toast.error(t('mailSettings.editor.wrongKind', { file: file.name }))
      return
    }
    if (target && MAIL_LOCALES.includes(target.locale as ContentLocale)) locale.value = target.locale as ContentLocale
    const content = parseMailTemplateFile(await file.text())
    subject.value = content.subject
    body.value = content.body
  } catch {
    toast.error(t('mailSettings.import.readFailed', { files: file.name }))
  }
}

function exportFile() {
  downloadText(
    serializeMailTemplateFile({ subject: subject.value, body: body.value }),
    mailTemplateFileName(kind.value, locale.value),
    'text/html',
  )
}

// ── Save ──

const saving = ref(false)

async function save() {
  saving.value = true
  try {
    await saveMailTemplates(kind.value, drafts.value)
    toast.success(t('common.saved'))
    visible.value = false
    emit('saved')
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="title" class="template-dialog">
    <div class="template-editor">
      <div class="editor-top">
        <div class="top-field">
          <span :id="`${uid}-locale`" class="field-label">{{ t('mailSettings.editor.language') }}</span>
          <SelectButton
            v-model="locale"
            :options="MAIL_LOCALES"
            :option-label="languageName"
            :allow-empty="false"
            :aria-labelledby="`${uid}-locale`"
          />
        </div>
        <div class="top-field top-field--grow">
          <label :for="`${uid}-subject`" class="field-label">{{ t('mailSettings.editor.subject') }}</label>
          <InputText :id="`${uid}-subject`" v-model="subject" fluid :disabled="!canWrite" />
        </div>
      </div>

      <div v-if="group?.variables.length" class="vars">
        <span class="field-label">{{ t('mailSettings.editor.variables') }}</span>
        <div class="var-chips">
          <Button
            v-for="v in group.variables"
            :key="v"
            :label="`{{ ${v} }}`"
            size="small"
            severity="secondary"
            outlined
            class="var-chip"
            :aria-label="t('mailSettings.editor.insert', { name: v })"
            :disabled="!canWrite"
            @click="insertVariable(v)"
          />
        </div>
      </div>

      <div class="split">
        <div class="pane">
          <label :for="`${uid}-body`" class="pane-header">{{ t('mailSettings.editor.body') }}</label>
          <!-- A native textarea, not OpenVue's Textarea, because inserting a variable needs the element's caret and selection. -->
          <textarea
            :id="`${uid}-body`"
            ref="textarea"
            v-model="body"
            class="html-textarea"
            spellcheck="false"
            autocomplete="off"
            :disabled="!canWrite"
            :placeholder="t('mailSettings.editor.bodyPlaceholder')"
          />
        </div>
        <div class="pane">
          <span class="pane-header">
            {{ t('mailSettings.editor.preview') }}
            <i v-if="previewLoading" class="mdi mdi-loading mdi-spin" aria-hidden="true" />
          </span>
          <small class="preview-note">
            {{ previewSubject ? t('mailSettings.editor.previewSubject', { subject: previewSubject }) : t('mailSettings.editor.previewNote') }}
          </small>
          <Message v-if="previewError" severity="error" class="preview-error" :closable="false">{{ previewError }}</Message>
          <iframe v-else :srcdoc="previewHtml" sandbox="" class="preview-frame" :title="previewSubject || title" />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="footer">
        <span class="footer-files">
          <Button
            :label="t('mailSettings.editor.importFile')"
            icon="mdi mdi-file-import-outline"
            text
            severity="secondary"
            :disabled="!canWrite"
            @click="importFile"
          />
          <Button :label="t('mailSettings.editor.exportFile')" icon="mdi mdi-file-export-outline" text severity="secondary" @click="exportFile" />
          <Button
            :label="t('mailSettings.editor.reset')"
            icon="mdi mdi-restore"
            text
            severity="secondary"
            :disabled="!canWrite"
            :loading="resetting"
            @click="resetToDefault"
          />
        </span>
        <Button :label="t('common.cancel')" text @click="visible = false" />
        <Button :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!canWrite" @click="save" />
      </div>
    </template>
  </Dialog>
</template>

<style scoped lang="scss">
.template-dialog {
  // Mail clients show the mail on white, whatever the app's theme.
  --mail-preview-background: #fff;

  width: var(--dialog-width-full);
}

.template-editor {
  display: grid;
  gap: var(--space-3);
}

.editor-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-3);
}

.top-field {
  display: grid;
  gap: var(--space-1);

  &--grow {
    flex: 1 1 16rem;
  }
}

.vars {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.var-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.var-chip {
  font-family: ui-monospace, monospace;
}

.split {
  display: grid;
  gap: var(--space-3);
}

.pane {
  display: flex;
  flex-direction: column;
  min-height: 20rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  overflow: hidden;
}

.pane-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.html-textarea {
  flex: 1 1 auto;
  width: 100%;
  min-height: 18rem;
  padding: var(--space-3);
  border: 0;
  outline: none;
  resize: vertical;
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-family: ui-monospace, monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.preview-note {
  padding: var(--space-2) var(--space-3) 0;
  color: var(--p-text-muted-color);
}

.preview-error {
  margin: var(--space-3);
}

.preview-frame {
  flex: 1 1 auto;
  width: 100%;
  min-height: 18rem;
  border: 0;
  background: var(--mail-preview-background);
}

.footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
  width: 100%;
}

.footer-files {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-right: auto;
}

@media (min-width: $bp-lg) {
  .split {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pane {
    height: 55vh;
  }
}
</style>
