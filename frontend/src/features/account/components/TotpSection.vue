<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import TotpQrCode from '@/features/auth/components/TotpQrCode.vue'
import { confirmTotp, disableTotp, enrollTotp, type TotpEnrolment } from '@/features/account/api/security'
import { useAppToast } from '@/core/composables/useAppToast'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'

const { t } = useI18n()
const toast = useAppToast()
const currentUser = useCurrentUserStore()

const enrolment = ref<TotpEnrolment | null>(null)
const code = ref('')
const password = ref('')
// Enrolling from a signed-in session asks for the current password first.
const enrolPassword = ref('')
const askingPassword = ref(false)
const disabling = ref(false)
const busy = ref(false)

async function start() {
  busy.value = true
  try {
    enrolment.value = await enrollTotp(enrolPassword.value)
    enrolPassword.value = ''
    askingPassword.value = false
    code.value = ''
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function confirm() {
  busy.value = true
  try {
    await confirmTotp(code.value)
    enrolment.value = null
    await currentUser.refresh()
    toast.success(t('account.totp.enabledToast'))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}

async function disable() {
  busy.value = true
  try {
    await disableTotp(password.value)
    password.value = ''
    disabling.value = false
    await currentUser.refresh()
    toast.success(t('account.totp.disabledToast'))
  } catch (err) {
    toast.error(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="section">
    <h2 class="panel-title">
      {{ t('account.totp.title') }}
      <Tag
        :value="currentUser.user?.totp_enabled ? t('account.totp.on') : t('account.totp.off')"
        :severity="currentUser.user?.totp_enabled ? 'success' : 'secondary'"
      />
    </h2>
    <p class="hint">{{ t('account.totp.hint') }}</p>

    <template v-if="!currentUser.user?.totp_enabled">
      <div v-if="!enrolment && !askingPassword">
        <Button :label="t('account.totp.enable')" icon="mdi mdi-shield-key" @click="askingPassword = true" />
      </div>
      <form v-else-if="!enrolment" class="disable" @submit.prevent="start">
        <p>{{ t('account.totp.enrolPasswordHint') }}</p>
        <div class="field">
          <label for="totp-enrol-password">{{ t('account.totp.passwordPrompt') }}</label>
          <Password v-model="enrolPassword" input-id="totp-enrol-password" :feedback="false" toggle-mask />
        </div>
        <div class="actions">
          <Button type="button" :label="t('common.cancel')" text @click="askingPassword = false" />
          <Button type="submit" :label="t('account.totp.continue')" :loading="busy" :disabled="!enrolPassword" />
        </div>
      </form>
      <form v-else class="enrol" @submit.prevent="confirm">
        <p>{{ t('account.totp.scan') }}</p>
        <TotpQrCode :uri="enrolment.provisioning_uri" :label="t('account.totp.qrLabel')" />
        <p class="secret">{{ enrolment.secret }}</p>
        <div class="field otp">
          <label for="totp-confirm">{{ t('auth.totpCode') }}</label>
          <InputOtp id="totp-confirm" v-model="code" :length="6" integer-only />
        </div>
        <div class="actions">
          <Button type="button" :label="t('common.cancel')" text @click="enrolment = null" />
          <Button type="submit" :label="t('account.totp.confirm')" :loading="busy" :disabled="code.length !== 6" />
        </div>
      </form>
    </template>

    <Message v-else-if="currentUser.user?.is_systemuser" severity="info" :closable="false">
      {{ t('account.totp.systemUserMandatory') }}
    </Message>

    <Message v-else-if="currentUser.user?.totp_mandatory" severity="info" :closable="false">
      {{ t('account.totp.settingsMandatory') }}
    </Message>

    <template v-else>
      <div v-if="!disabling">
        <Button :label="t('account.totp.disable')" severity="danger" outlined @click="disabling = true" />
      </div>
      <form v-else class="disable" @submit.prevent="disable">
        <div class="field">
          <label for="totp-password">{{ t('account.totp.passwordPrompt') }}</label>
          <Password v-model="password" input-id="totp-password" :feedback="false" toggle-mask />
        </div>
        <div class="actions">
          <Button type="button" :label="t('common.cancel')" text @click="disabling = false" />
          <Button type="submit" :label="t('account.totp.disable')" severity="danger" :loading="busy" :disabled="!password" />
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped lang="scss">
.section,
.enrol,
.disable {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.enrol {
  align-items: center;
  max-width: 24rem;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.secret {
  font-family: monospace;
  word-break: break-all;
  user-select: all;
  color: var(--p-text-muted-color);
}

.otp {
  align-items: center;
}

.actions {
  display: flex;
  gap: var(--space-2);
}
</style>
