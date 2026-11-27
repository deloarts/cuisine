<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import RememberedAccounts from '@/features/auth/components/RememberedAccounts.vue'
import TotpQrCode from '@/features/auth/components/TotpQrCode.vue'
import UserAvatar from '@/shared/components/UserAvatar.vue'
import LegalLinks from '@/shared/components/legal/LegalLinks.vue'
import {
  confirmWithSetupToken,
  enrollWithSetupToken,
  passkeyLogin,
  passkeyLoginOptions,
  passwordLogin,
  totpLogin,
  type LoginResponse,
  type TotpEnrolmentResponse,
} from '@/features/auth/api/login'
import { setUpPasskeyOnThisDevice } from '@/features/auth/utils/passkeySetup'
import {
  forgetRememberedAccount,
  listRememberedAccounts,
  rememberSignedInAccount,
  updateRememberedAccount,
  type RememberedAccount,
} from '@/features/auth/utils/rememberedAccounts'
import {
  getPasskey,
  passkeyPromptDismissed,
  passkeysSupported,
  platformAuthenticatorAvailable,
  platformAuthenticatorKind,
} from '@/features/auth/utils/webauthn'
import type { CurrentUserResponse } from '@/core/types/user'
import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { usePublicInfoStore } from '@/core/stores/publicInfoStore'
import { errorMessage, errorStatus } from '@/core/utils/errors'

type Step = 'password' | 'totp' | 'setup' | 'passkey'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const currentUser = useCurrentUserStore()
const publicInfo = usePublicInfoStore()

const step = ref<Step>('password')
const loading = ref(false)
const error = ref<string | null>(null)

const email = ref('')
const password = ref('')
const code = ref('')
const trustDevice = ref(false)
const partialToken = ref('')
const trustedDeviceDays = ref(0)
const setupToken = ref('')
const enrolment = ref<TotpEnrolmentResponse | null>(null)

const instanceName = computed(() => publicInfo.info?.instance_name ?? 'Cuisine')
const canUsePasskey = passkeysSupported()
const notice = computed(() => (route.query.expired ? t('auth.sessionExpired') : null))

// Accounts that signed in on this device before. With one remembered, the
// page opens on it instead of the empty form.
const accounts = ref<RememberedAccount[]>(listRememberedAccounts())
const selected = ref<RememberedAccount | null>(accounts.value[0] ?? null)
// The remembered account's password field, shown when it has no passkey on
// this device or its passkey prompt was dismissed.
const askPassword = ref(false)
const chooserHint = ref<string | null>(null)
const others = computed(() => accounts.value.filter((a) => a.userId !== selected.value?.userId))
const selectedUsesPasskey = computed(() => canUsePasskey && !!selected.value?.credentialId)
// The passkey of the sign-in in progress, remembered once it succeeds.
let signedInCredential: string | null = null

function selectAccount(account: RememberedAccount) {
  selected.value = account
  askPassword.value = !selectedUsesPasskey.value
  chooserHint.value = null
  password.value = ''
  error.value = null
}

function otherAccount() {
  selected.value = null
  email.value = ''
  password.value = ''
  error.value = null
}

function backToAccounts() {
  const first = accounts.value[0]
  if (first) selectAccount(first)
}

function forgetSelected() {
  if (!selected.value) return
  forgetRememberedAccount(selected.value.userId)
  accounts.value = listRememberedAccounts()
  const first = accounts.value[0]
  if (first) selectAccount(first)
  else otherAccount()
}

if (selected.value) selectAccount(selected.value)

function describe(err: unknown): string {
  const status = errorStatus(err)
  if (status === 429) return t('auth.locked')
  if (status === 401) return errorMessage(err, t('auth.invalidCredentials'))
  return errorMessage(err, t('auth.genericError'))
}

// The offer, right after a password sign-in, to set up a passkey here.
const offeredTo = ref<CurrentUserResponse | null>(null)
const offerBusy = ref(false)
const offerError = ref<string | null>(null)
const authenticatorKind = platformAuthenticatorKind()

/**
 * Whether to offer a passkey after this sign-in: only after a password,
 * on a device with a built-in authenticator, and only to an account that
 * has none on this device yet and did not say "Not now" here. The system
 * account cannot use passkeys.
 */
async function shouldOfferPasskey(user: CurrentUserResponse): Promise<boolean> {
  if (signedInCredential || user.is_systemuser || !canUsePasskey) return false
  const known = listRememberedAccounts().find((a) => a.userId === user.id)
  if (known?.credentialId || known?.passkeyDeclined) return false
  return platformAuthenticatorAvailable()
}

async function acceptPasskey() {
  const user = offeredTo.value
  if (!user) return
  offerBusy.value = true
  offerError.value = null
  try {
    await setUpPasskeyOnThisDevice(user.id, t(`auth.passkeyOffer.deviceName.${authenticatorKind}`))
    await leave(user)
  } catch (err) {
    offerError.value = passkeyPromptDismissed(err) ? t('auth.passkeyOffer.dismissed') : t('auth.passkeyOffer.failed')
  } finally {
    offerBusy.value = false
  }
}

async function declinePasskey() {
  const user = offeredTo.value
  if (!user) return
  updateRememberedAccount(user.id, { passkeyDeclined: true })
  await leave(user)
}

async function finish() {
  const user = await currentUser.refresh()
  if (!user) return leave(null)
  await rememberSignedInAccount(user, signedInCredential)
  if (await shouldOfferPasskey(user)) {
    offeredTo.value = user
    step.value = 'passkey'
    return
  }
  await leave(user)
}

async function leave(user: CurrentUserResponse | null) {
  // The system account is for administration only, so it always lands in
  // the admin area, whatever the link asked for.
  if (user?.is_systemuser) {
    await router.replace({ name: 'admin' })
    return
  }
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  // Only paths inside the app, never an absolute URL someone put in the link.
  await router.replace(redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/')
}

async function handle(result: LoginResponse) {
  if (result.status === 'session') {
    await finish()
  } else if (result.status === 'totp_required') {
    partialToken.value = result.partial_token ?? ''
    trustedDeviceDays.value = result.trusted_device_days ?? 0
    code.value = ''
    step.value = 'totp'
  } else {
    setupToken.value = result.setup_token ?? ''
    enrolment.value = await enrollWithSetupToken(setupToken.value)
    code.value = ''
    step.value = 'setup'
  }
}

async function run(action: () => Promise<void>) {
  loading.value = true
  error.value = null
  try {
    await action()
  } catch (err) {
    error.value = describe(err)
  } finally {
    loading.value = false
  }
}

const submitPassword = () =>
  run(async () => {
    signedInCredential = null
    const login = selected.value ? selected.value.login : email.value.trim()
    await handle(await passwordLogin(login, password.value))
    password.value = ''
  })

const submitTotp = () =>
  run(async () => handle(await totpLogin(partialToken.value, code.value, trustDevice.value)))

const submitSetup = () =>
  run(async () => {
    if (await confirmWithSetupToken(setupToken.value, code.value)) await finish()
  })

/**
 * Signs in with a passkey: the one this device used for `account` when
 * given, otherwise any the browser holds for this site. Returns false when
 * the prompt was dismissed or no such passkey exists on this device.
 */
async function signInWithPasskey(account: RememberedAccount | null = null): Promise<boolean> {
  loading.value = true
  error.value = null
  try {
    const options = await passkeyLoginOptions()
    const credential = await getPasskey(options.options, account?.credentialId)
    signedInCredential = typeof credential.rawId === 'string' ? credential.rawId : null
    await handle(await passkeyLogin(options.challenge_token, credential))
    return true
  } catch (err) {
    if (passkeyPromptDismissed(err)) return false
    error.value = describe(err)
    return true
  } finally {
    loading.value = false
  }
}

// The remembered account's sign-in: the passkey this device knows, falling
// back to the password when the prompt is dismissed.
async function signInSelected() {
  if (!selected.value) return
  if (!(await signInWithPasskey(selected.value))) {
    chooserHint.value = t('auth.chooser.usePassword')
    askPassword.value = true
  }
}

function back() {
  step.value = 'password'
  error.value = null
  code.value = ''
}
</script>

<template>
  <div class="login-wrapper">
    <div class="login-card">
      <span class="brand-name">{{ instanceName }}</span>
      <hr class="brand-divider" />

      <Message v-if="notice && step === 'password'" severity="warn" :closable="false">
        {{ notice }}
      </Message>

      <div v-if="step === 'password' && selected" class="login-form" data-testid="login-chooser">
        <div class="chosen-account" data-testid="login-remembered-account">
          <UserAvatar class="chosen-avatar" :name="selected.displayName" :src="selected.avatar" />
          <span class="chosen-name">{{ selected.displayName }}</span>
          <span class="chosen-login">{{ selected.login }}</span>
        </div>

        <form v-if="askPassword" class="login-form" @submit.prevent="submitPassword">
          <p v-if="chooserHint" class="step-hint">{{ chooserHint }}</p>
          <div class="field">
            <label for="login-chooser-password">{{ t('auth.password') }}</label>
            <!-- The address the password belongs to, for password managers. -->
            <input :value="selected.login" type="hidden" autocomplete="username" />
            <Password
              v-model="password"
              input-id="login-chooser-password"
              :feedback="false"
              toggle-mask
              autocomplete="current-password"
              autofocus
            />
          </div>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button
            type="submit"
            :label="t('auth.signIn')"
            :loading="loading"
            :disabled="!password"
            class="login-submit"
          />
        </form>

        <template v-else>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button
            type="button"
            icon="mdi mdi-fingerprint"
            :label="t('auth.signIn')"
            :loading="loading"
            class="login-submit"
            data-testid="login-chooser-sign-in"
            @click="signInSelected"
          />
        </template>

        <div class="chooser-actions">
          <Button
            type="button"
            icon="mdi mdi-account-switch-outline"
            :label="t('auth.chooser.otherAccount')"
            text
            class="login-back"
            :disabled="loading"
            data-testid="login-other-account"
            @click="otherAccount"
          />
          <Button
            type="button"
            icon="mdi mdi-account-remove-outline"
            :label="t('auth.chooser.forget')"
            text
            class="login-back"
            :disabled="loading"
            data-testid="login-forget-account"
            @click="forgetSelected"
          />
        </div>

        <RememberedAccounts :accounts="others" :disabled="loading" @select="selectAccount" />
      </div>

      <form v-else-if="step === 'password'" class="login-form" @submit.prevent="submitPassword">
        <div class="field">
          <label for="login-email">{{ t('auth.email') }}</label>
          <!--
            Plain text rather than type="email", so the system user can sign in as "system".
            "username" is the autocomplete token password managers pair with the password.
          -->
          <InputText
            id="login-email"
            v-model="email"
            inputmode="email"
            autocomplete="username"
            autocapitalize="none"
            autofocus
          />
        </div>
        <div class="field">
          <label for="login-password">{{ t('auth.password') }}</label>
          <Password
            v-model="password"
            input-id="login-password"
            :feedback="false"
            toggle-mask
            autocomplete="current-password"
          />
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          :label="t('auth.signIn')"
          :loading="loading"
          :disabled="!email || !password"
          class="login-submit"
        />
        <Button
          v-if="canUsePasskey"
          type="button"
          icon="mdi mdi-fingerprint"
          :label="t('auth.signInPasskey')"
          :disabled="loading"
          class="login-secondary"
          outlined
          @click="signInWithPasskey()"
        />
        <Button
          v-if="accounts.length > 0"
          type="button"
          icon="mdi mdi-arrow-left"
          :label="t('auth.chooser.back')"
          text
          class="login-back"
          :disabled="loading"
          data-testid="login-back-to-accounts"
          @click="backToAccounts"
        />
      </form>

      <form v-else-if="step === 'totp'" class="login-form" @submit.prevent="submitTotp">
        <p class="step-hint">{{ t('auth.totpHint') }}</p>
        <div class="field otp-field">
          <label for="login-totp">{{ t('auth.totpCode') }}</label>
          <InputOtp id="login-totp" v-model="code" :length="6" integer-only />
        </div>
        <div v-if="trustedDeviceDays > 0" class="trust-field">
          <Checkbox v-model="trustDevice" input-id="login-trust" binary />
          <label for="login-trust">
            {{ t('auth.trustDevice', { days: trustedDeviceDays }) }}
          </label>
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          :label="t('auth.verify')"
          :loading="loading"
          :disabled="code.length !== 6"
          class="login-submit"
        />
        <Button type="button" :label="t('common.back')" text class="login-back" @click="back" />
      </form>

      <div v-else-if="step === 'passkey'" class="login-form" data-testid="login-passkey-offer">
        <span class="mdi mdi-fingerprint offer-icon" aria-hidden="true" />
        <p class="step-hint">{{ t('auth.passkeyOffer.description') }}</p>
        <Message v-if="offerError" severity="warn" :closable="false">{{ offerError }}</Message>
        <Button
          type="button"
          icon="mdi mdi-fingerprint"
          :label="t(`auth.passkeyOffer.accept.${authenticatorKind}`)"
          :loading="offerBusy"
          class="login-submit"
          data-testid="login-passkey-accept"
          @click="acceptPasskey"
        />
        <Button
          type="button"
          :label="t('auth.passkeyOffer.notNow')"
          text
          class="login-back"
          :disabled="offerBusy"
          data-testid="login-passkey-decline"
          @click="declinePasskey"
        />
      </div>

      <form v-else class="login-form" @submit.prevent="submitSetup">
        <p class="step-hint">{{ t('auth.setupHint') }}</p>
        <TotpQrCode
          v-if="enrolment"
          :uri="enrolment.provisioning_uri"
          :label="t('account.totp.qrLabel')"
        />
        <p v-if="enrolment" class="secret">{{ enrolment.secret }}</p>
        <div class="field otp-field">
          <label for="login-setup-code">{{ t('auth.totpCode') }}</label>
          <InputOtp id="login-setup-code" v-model="code" :length="6" integer-only />
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          :label="t('auth.setupConfirm')"
          :loading="loading"
          :disabled="code.length !== 6"
          class="login-submit"
        />
        <Button type="button" :label="t('common.back')" text class="login-back" @click="back" />
      </form>
    </div>
    <RouterLink
      v-if="publicInfo.info?.allow_public_recipes"
      :to="{ name: 'public-recipes' }"
      class="login-public"
      data-testid="login-public-recipes"
    >
      <span class="mdi mdi-earth" aria-hidden="true" />
      {{ t('auth.browsePublic') }}
    </RouterLink>
    <LegalLinks class="login-legal" />
  </div>
</template>

<style scoped lang="scss">
// This screen does not follow the app theme: it renders before a session
// exists, so there is no preference to read, and always shows the same dark
// card over the warm backdrop of AuthLayout.
.login-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-4);
  animation: appear 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.login-card {
  width: min(22rem, 100%);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  background: var(--auth-card);
  backdrop-filter: blur(32px) saturate(1.6);
  border-radius: 18px;
  box-shadow: var(--auth-card-shadow);
}

.brand-name {
  font-family: var(--font-brand);
  font-size: var(--font-size-4xl);
  letter-spacing: 0.03em;
  text-align: center;
  color: var(--auth-ink);
}

.brand-divider {
  border: none;
  height: 1px;
  margin: 0;
  background: linear-gradient(90deg, transparent, var(--auth-line), transparent);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);

  label {
    font-family: var(--font-head);
    font-size: var(--font-size-xs);
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--auth-text);
  }
}

.otp-field {
  align-items: center;
}

.trust-field {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--auth-text);
  font-size: var(--font-size-sm);

  // The checkbox takes the card's dark field look and accent, like the
  // inputs above, since the app theme does not reach this screen.
  --p-checkbox-background: var(--auth-field);
  --p-checkbox-border-color: var(--auth-line);
  --p-checkbox-hover-border-color: var(--auth-hover-border);
  --p-checkbox-focus-border-color: var(--auth-accent);
  --p-checkbox-checked-background: var(--auth-accent);
  --p-checkbox-checked-border-color: var(--auth-accent);
  --p-checkbox-checked-hover-background: var(--auth-accent-hover);
  --p-checkbox-checked-hover-border-color: var(--auth-accent-hover);
  --p-checkbox-checked-focus-border-color: var(--auth-accent);
  --p-checkbox-icon-checked-color: var(--on-accent);
  --p-checkbox-icon-checked-hover-color: var(--on-accent);

  label {
    cursor: pointer;
  }
}

.step-hint {
  margin: 0;
  color: var(--auth-text);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  text-align: center;
}

.secret {
  font-family: monospace;
  font-size: var(--font-size-sm);
  color: var(--auth-text-muted);
  text-align: center;
  word-break: break-all;
  user-select: all;
}

/* stylelint-disable selector-disallowed-list -- the sign-in screen draws its own input skin, with hover and focus states the input tokens cannot express */
.field :deep(.p-password),
.field :deep(.p-inputtext) {
  width: 100%;
}

.field :deep(.p-inputtext),
.field :deep(.p-inputotp-input) {
  background: var(--auth-field) !important;
  border: 1px solid var(--auth-line) !important;
  border-radius: 9px !important;
  color: var(--auth-text-strong) !important;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;

  &:hover {
    background: var(--auth-field-hover) !important;
    border-color: var(--auth-hover-border) !important;
  }

  &:focus {
    background: var(--auth-focus-fill) !important;
    border-color: var(--auth-focus-border) !important;
    box-shadow: var(--auth-focus-glow) !important;
  }
}

.field :deep(.p-inputotp-input) {
  width: 2.6rem;
}
/* stylelint-enable selector-disallowed-list */

.login-submit {
  border-radius: 9px;
  --p-button-primary-background: var(--auth-accent);
  --p-button-primary-border-color: var(--auth-accent);
  --p-button-primary-color: var(--on-accent);
  --p-button-primary-hover-background: var(--auth-accent-hover);
  --p-button-primary-hover-border-color: var(--auth-accent-hover);
  --p-button-primary-hover-color: var(--on-accent);
  --p-button-primary-active-background: var(--auth-accent-active);
  --p-button-primary-active-border-color: var(--auth-accent-active);
  --p-button-primary-active-color: var(--on-accent);
  font-family: var(--font-head);
  font-weight: 700;
  letter-spacing: 0.07em;
  box-shadow: var(--auth-submit-shadow);

  &:hover:not(:disabled) {
    box-shadow: var(--auth-submit-shadow-hover);
  }
}

.login-secondary {
  border-radius: 9px;
  --p-button-outlined-primary-color: var(--auth-accent-text);
  --p-button-outlined-primary-border-color: var(--auth-hover-border);
  --p-button-outlined-primary-hover-background: var(--auth-focus-fill);
}

.login-public {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  margin-top: var(--space-3);
  color: var(--auth-accent-text);
  font-weight: 700;
}

.login-legal {
  margin-top: var(--space-3);

  :deep(a) {
    color: var(--auth-text-muted);
  }
}

.login-back {
  --p-button-text-primary-color: var(--auth-text-muted);
}

// The fingerprint above the passkey offer.
.offer-icon {
  align-self: center;
  font-size: var(--font-size-4xl);
  color: var(--auth-accent-text);
}

// The remembered account the page opened on, as a small profile card.
.chosen-account {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.chosen-avatar {
  --avatar-size: 4.5rem;
  --avatar-background: var(--auth-field);
  --avatar-color: var(--auth-text-strong);

  margin-bottom: var(--space-2);
  box-shadow: 0 0 0 2px var(--auth-line);
}

.chosen-name {
  color: var(--auth-text-strong);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.chosen-login {
  color: var(--auth-text-muted);
  font-size: var(--font-size-sm);
  word-break: break-all;
}

.chooser-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-1);
}

@keyframes appear {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }

  to {
    opacity: 1;
    transform: none;
  }
}
</style>
