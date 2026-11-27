<script setup lang="ts">
/**
 * Mail, ported from Glados's mail tab: the provider (server, sign-in,
 * sender, encryption and certificate check), who gets operational alerts
 * such as a failed backup, the hourly sending limit, a test mail, and the
 * templates per language with an editor and a file import. Mail stays
 * optional: without it Cuisine works fully, it only sends nothing.
 */
import { computed, onMounted, reactive, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { pickFiles } from '@/shared/composables/fileTransfer'
import MailTemplateEditorDialog from '@/features/admin-settings/components/MailTemplateEditorDialog.vue'
import MailTemplateImportDialog from '@/features/admin-settings/components/MailTemplateImportDialog.vue'
import {
  getMailAlerts,
  getMailSettings,
  getMailTemplates,
  MAIL_LOCALES,
  saveMailSettings,
  sendTestMail,
  type MailAlert,
  type MailSettings,
  type MailSettingsRequest,
  type MailTemplateGroup,
} from '@/features/admin-settings/api/mail'
import { addRecipient } from '@/features/admin-settings/mailRecipients'
import { planMailTemplateImport, type MailTemplateImportRow } from '@/features/admin-settings/mailTemplateFile'
import { Permission } from '@/core/auth/permissions'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

type Security = MailSettingsRequest['security']

const { t } = useI18n()
const uid = useId()
const toast = useAppToast()
const currentUser = useCurrentUserStore()
const canWrite = currentUser.hasPermission(Permission.WRITE_SETTINGS)

const loaded = ref(false)
const passwordSet = ref(false)
// Blank until the stored settings arrive; the fields render at once and stay
// disabled until then.
const form = reactive({
  enabled: false,
  host: '',
  port: null as number | null,
  security: null as Security | null,
  username: '',
  password: '',
  sender: '',
  sender_name: '',
  reply_to: '',
  verify_certificate: false,
  send_limit_per_hour: null as number | null,
  alert_recipients: [] as string[],
})
const editable = computed(() => canWrite && loaded.value)
const saving = ref(false)
const securityModes = computed(() =>
  (['starttls', 'tls', 'none'] as const).map((value) => ({ value, label: t(`mailSettings.security.${value}`) })),
)

function adopt(mail: MailSettings) {
  Object.assign(form, {
    enabled: mail.enabled,
    host: mail.host,
    port: mail.port,
    security: mail.security as Security,
    username: mail.username,
    password: '',
    sender: mail.sender,
    sender_name: mail.sender_name,
    reply_to: mail.reply_to,
    verify_certificate: mail.verify_certificate,
    send_limit_per_hour: mail.send_limit_per_hour,
    alert_recipients: [...mail.alert_recipients],
  })
  passwordSet.value = mail.password_set
  loaded.value = true
}

async function save() {
  if (!loaded.value || form.port === null || form.security === null || form.send_limit_per_hour === null) return
  saving.value = true
  try {
    adopt(
      await saveMailSettings({
        enabled: form.enabled,
        host: form.host.trim(),
        port: form.port,
        security: form.security,
        username: form.username.trim(),
        // Empty keeps the stored password, since the API never sends it out.
        password: form.password.trim() || null,
        sender: form.sender.trim(),
        sender_name: form.sender_name.trim(),
        reply_to: form.reply_to.trim(),
        verify_certificate: form.verify_certificate,
        send_limit_per_hour: form.send_limit_per_hour,
        alert_recipients: form.alert_recipients,
      }),
    )
    toast.success(t('common.saved'))
  } catch (err) {
    toast.error(err)
  } finally {
    saving.value = false
  }
}

// ── Alert recipients ──

const alerts = ref<MailAlert[]>([])
const recipientInput = ref('')

function addAlertRecipient() {
  const result = addRecipient(form.alert_recipients, recipientInput.value)
  if (result.error) {
    toast.error(t('mailSettings.invalidRecipient', { email: recipientInput.value.trim() }))
    return
  }
  form.alert_recipients = result.recipients
  recipientInput.value = ''
}

function removeRecipient(email: string) {
  form.alert_recipients = form.alert_recipients.filter((e) => e !== email)
}

// ── Test mail ──

const testVisible = ref(false)
const testRecipient = ref('')
const testing = ref(false)

function openTest() {
  testRecipient.value = ''
  testVisible.value = true
}

async function sendTest() {
  testing.value = true
  try {
    await sendTestMail(testRecipient.value.trim() || null)
    toast.success(t('mailSettings.test.sent'))
    testVisible.value = false
  } catch (err) {
    toast.error(err)
  } finally {
    testing.value = false
  }
}

// ── Templates ──

const templates = ref<MailTemplateGroup[]>([])
const editorVisible = ref(false)
const editing = ref<MailTemplateGroup | null>(null)

function isCustomized(kind: string, locale: string): boolean {
  return templates.value.find((g) => g.kind === kind)?.templates.find((tpl) => tpl.locale === locale)?.customized ?? false
}

async function loadTemplates() {
  try {
    templates.value = await getMailTemplates()
  } catch (err) {
    toast.error(err)
  }
}

function openEditor(group: MailTemplateGroup) {
  editing.value = group
  editorVisible.value = true
}

const importRows = ref<MailTemplateImportRow[]>([])
const importVisible = ref(false)

async function importTemplates() {
  const files = await pickFiles('.html,.htm', true)
  if (!files.length) return
  try {
    const picked = await Promise.all(files.map(async (file) => ({ name: file.name, text: await file.text() })))
    importRows.value = planMailTemplateImport(
      picked,
      templates.value.map((g) => g.kind),
      MAIL_LOCALES,
      isCustomized,
    )
    importVisible.value = true
  } catch {
    toast.error(t('mailSettings.import.readFailed', { files: files.map((f) => f.name).join(', ') }))
  }
}

onMounted(async () => {
  try {
    adopt(await getMailSettings())
  } catch (err) {
    toast.error(err)
  }
  void loadTemplates()
  getMailAlerts()
    .then((list) => {
      alerts.value = list
    })
    .catch(() => undefined)
})
</script>

<template>
  <div class="settings-tab mail">
    <p class="hint">{{ t('mailSettings.intro') }}</p>
    <div v-if="canWrite" class="toolbar">
      <Button :label="t('common.save')" icon="mdi mdi-content-save" :loading="saving" :disabled="!loaded" @click="save" />
      <Button
        :label="t('mailSettings.test.button')"
        icon="mdi mdi-email-fast-outline"
        outlined
        :disabled="!form.enabled"
        @click="openTest"
      />
      <Button
        :label="t('mailSettings.import.button')"
        icon="mdi mdi-file-import-outline"
        text
        :disabled="!templates.length"
        @click="importTemplates"
      />
    </div>

    <form class="mail-form" @submit.prevent="save">
      <section class="block">
        <h3 class="block-title">{{ t('mailSettings.provider') }}</h3>
        <div class="toggle">
          <ToggleSwitch v-model="form.enabled" :input-id="`${uid}-enabled`" :disabled="!editable" />
          <label :for="`${uid}-enabled`">{{ t('settings.mail.enabled') }}</label>
        </div>
        <div class="form-grid">
          <div class="field">
            <label :for="`${uid}-host`">{{ t('settings.mail.host') }}</label>
            <InputText :id="`${uid}-host`" v-model="form.host" :disabled="!editable" />
          </div>
          <div class="field">
            <label :for="`${uid}-port`">{{ t('settings.mail.port') }}</label>
            <InputNumber v-model="form.port" :input-id="`${uid}-port`" :min="1" :max="65535" :use-grouping="false" :disabled="!editable" />
          </div>
          <div class="field">
            <label :id="`${uid}-security-label`" :for="`${uid}-security`">{{ t('settings.mail.security') }}</label>
            <Select
              :id="`${uid}-security`"
              v-model="form.security"
              :options="securityModes"
              option-label="label"
              option-value="value"
              :aria-labelledby="`${uid}-security-label`"
              :disabled="!editable"
            />
          </div>
          <div class="field">
            <label :for="`${uid}-username`">{{ t('settings.mail.username') }}</label>
            <InputText :id="`${uid}-username`" v-model="form.username" autocomplete="off" :disabled="!editable" />
          </div>
          <div class="field">
            <label :for="`${uid}-password`">{{ t('settings.mail.password') }}</label>
            <Password
              v-model="form.password"
              :input-id="`${uid}-password`"
              :feedback="false"
              toggle-mask
              autocomplete="new-password"
              :disabled="!editable"
            />
            <small class="field-hint">
              {{ !loaded ? '\u00a0' : passwordSet ? t('settings.mail.passwordKeep') : t('settings.mail.passwordNone') }}
            </small>
          </div>
          <div class="field">
            <label :for="`${uid}-sender`">{{ t('settings.mail.sender') }}</label>
            <InputText :id="`${uid}-sender`" v-model="form.sender" type="email" :disabled="!editable" />
          </div>
          <div class="field">
            <label :for="`${uid}-sender-name`">{{ t('mailSettings.senderName') }}</label>
            <InputText :id="`${uid}-sender-name`" v-model="form.sender_name" maxlength="128" :disabled="!editable" />
            <small class="field-hint">{{ t('mailSettings.senderNameHint') }}</small>
          </div>
          <div class="field">
            <label :for="`${uid}-reply-to`">{{ t('mailSettings.replyTo') }}</label>
            <InputText :id="`${uid}-reply-to`" v-model="form.reply_to" type="email" :disabled="!editable" />
            <small class="field-hint">{{ t('mailSettings.replyToHint') }}</small>
          </div>
        </div>
        <div class="toggle">
          <ToggleSwitch v-model="form.verify_certificate" :input-id="`${uid}-verify`" :disabled="!editable" />
          <label :for="`${uid}-verify`" class="toggle-label">
            {{ t('mailSettings.verifyCertificate') }}
            <small class="field-hint">{{ t('mailSettings.verifyCertificateHint') }}</small>
          </label>
        </div>
      </section>

      <section class="block">
        <h3 class="block-title">{{ t('mailSettings.alertRecipients') }}</h3>
        <p class="hint">{{ t('mailSettings.alertRecipientsHint') }}</p>
        <ul v-if="alerts.length" class="alert-kinds">
          <li v-for="alert in alerts" :key="alert.kind">{{ alert.description }}</li>
        </ul>
        <div v-if="form.alert_recipients.length" class="recipients">
          <span v-for="email in form.alert_recipients" :key="email" class="recipient">
            {{ email }}
            <Button
              icon="mdi mdi-close"
              text
              rounded
              size="small"
              severity="secondary"
              :disabled="!editable"
              :aria-label="t('mailSettings.removeRecipient', { email })"
              @click="removeRecipient(email)"
            />
          </span>
        </div>
        <p v-else-if="loaded" class="field-hint">{{ t('mailSettings.noRecipients') }}</p>
        <div class="recipient-add">
          <label :for="`${uid}-recipient`" class="visually-hidden">{{ t('mailSettings.addRecipient') }}</label>
          <InputText
            :id="`${uid}-recipient`"
            v-model="recipientInput"
            type="email"
            :placeholder="t('mailSettings.recipientPlaceholder')"
            :disabled="!editable"
            @keydown.enter.prevent="addAlertRecipient"
          />
          <Button
            icon="mdi mdi-plus"
            severity="secondary"
            :aria-label="t('mailSettings.addRecipient')"
            :disabled="!editable"
            @click="addAlertRecipient"
          />
        </div>
      </section>

      <section class="block">
        <h3 class="block-title">{{ t('mailSettings.limits') }}</h3>
        <div class="field limit">
          <label :for="`${uid}-limit`">{{ t('mailSettings.sendLimitPerHour') }}</label>
          <InputNumber
            v-model="form.send_limit_per_hour"
            :input-id="`${uid}-limit`"
            :min="1"
            :max="1000"
            :use-grouping="false"
            :disabled="!editable"
          />
          <small class="field-hint">{{ t('mailSettings.sendLimitPerHourHint') }}</small>
        </div>
      </section>
    </form>

    <section class="block">
      <h3 class="block-title">{{ t('mailSettings.templates') }}</h3>
      <p class="hint">{{ t('mailSettings.templatesHint') }}</p>
      <ul class="template-rows">
        <li v-for="group in templates" :key="group.kind" class="template-row">
          <span class="template-text">
            <strong>{{ t(`mailSettings.kinds.${group.kind}.label`) }}</strong>
            <small class="text-muted">{{ t(`mailSettings.kinds.${group.kind}.hint`) }}</small>
          </span>
          <span class="template-status">
            <Tag
              v-for="locale in MAIL_LOCALES"
              :key="locale"
              v-tooltip.top="isCustomized(group.kind, locale) ? t('mailSettings.customized') : t('mailSettings.builtIn')"
              :value="locale"
              :severity="isCustomized(group.kind, locale) ? 'success' : 'secondary'"
            />
            <Button
              :label="canWrite ? t('common.edit') : t('mailSettings.view')"
              icon="mdi mdi-pencil"
              text
              size="small"
              @click="openEditor(group)"
            />
          </span>
        </li>
      </ul>
    </section>

    <MailTemplateEditorDialog v-model:visible="editorVisible" :group="editing" @saved="loadTemplates" />
    <MailTemplateImportDialog v-model:visible="importVisible" :rows="importRows" @imported="loadTemplates" />

    <Dialog v-model:visible="testVisible" modal :header="t('mailSettings.test.title')" class="test-dialog">
      <form class="test-form" @submit.prevent="sendTest">
        <div class="field">
          <label :for="`${uid}-test-to`">{{ t('mailSettings.test.recipient') }}</label>
          <InputText
            :id="`${uid}-test-to`"
            v-model="testRecipient"
            type="email"
            :placeholder="currentUser.user?.email ?? ''"
            fluid
          />
          <small class="field-hint">{{ t('mailSettings.test.recipientHint') }}</small>
        </div>
        <div class="dialog-actions">
          <Button type="button" :label="t('common.cancel')" text @click="testVisible = false" />
          <Button type="submit" :label="t('mailSettings.test.send')" icon="mdi mdi-send" :loading="testing" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
.mail,
.mail-form {
  display: grid;
  gap: var(--space-4);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.block {
  display: grid;
  gap: var(--space-3);

  p {
    margin: 0;
  }
}

.block-title {
  margin: 0;
  font-size: var(--font-size-md);
}

.toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.toggle-label {
  display: grid;
}

.alert-kinds {
  margin: 0;
  padding-left: var(--space-4);
  color: var(--p-text-muted-color);
  font-size: var(--font-size-sm);
}

.recipients {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.recipient {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding-left: var(--space-2);
  border-radius: var(--p-content-border-radius);
  background: var(--p-content-hover-background);
}

.recipient-add {
  display: flex;
  gap: var(--space-2);
  max-width: 28rem;
}

.limit {
  max-width: 20rem;
}

.template-rows {
  display: grid;
  padding: 0;
  margin: 0;
  list-style: none;
}

.template-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--p-content-border-color);
}

.template-text {
  display: grid;
}

.template-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.test-dialog {
  width: min(var(--dialog-width-sm), 100vw - 2 * var(--space-4));
}

.test-form {
  display: grid;
  gap: var(--space-3);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
