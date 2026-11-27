import { authApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type LoginResponse = Schemas['LoginResponse']
export type PasskeyOptionsResponse = Schemas['PasskeyOptionsResponse']
export type TotpEnrolmentResponse = Schemas['TotpEnrolmentResponse']

/** Step one of the sign-in: the e-mail address, or `system` for the system user, and the password. */
export async function passwordLogin(login: string, password: string): Promise<LoginResponse> {
  return (await authApi.post<LoginResponse>('/login', { login, password })).data
}

export async function totpLogin(
  partialToken: string,
  code: string,
  trustDevice: boolean,
): Promise<LoginResponse> {
  return (
    await authApi.post<LoginResponse>('/login/totp', {
      partial_token: partialToken,
      code,
      trust_device: trustDevice,
    })
  ).data
}

export async function passkeyLoginOptions(): Promise<PasskeyOptionsResponse> {
  return (await authApi.post<PasskeyOptionsResponse>('/login/passkey/options')).data
}

export async function passkeyLogin(
  challengeToken: string,
  credential: Record<string, unknown>,
): Promise<LoginResponse> {
  return (
    await authApi.post<LoginResponse>('/login/passkey', {
      challenge_token: challengeToken,
      credential,
    })
  ).data
}

/** Enrolment forced at login: the setup token stands in for a session. */
function bearer(setupToken: string) {
  return { config: { headers: { Authorization: `Bearer ${setupToken}` } } }
}

export function enrollWithSetupToken(setupToken: string): Promise<TotpEnrolmentResponse> {
  return webApi.post('/users/me/totp/enroll', { body: null, ...bearer(setupToken) })
}

export async function confirmWithSetupToken(setupToken: string, code: string): Promise<boolean> {
  const result = await webApi.post('/users/me/totp/confirm', {
    body: { code },
    ...bearer(setupToken),
  })
  return result.session_started
}

export type PasskeyResponse = Schemas['PasskeyResponse']

/** Registration options for a new passkey of the signed-in user. */
export function passkeyRegistrationOptions(): Promise<PasskeyOptionsResponse> {
  return webApi.post('/users/me/passkeys/options')
}

/** Stores the passkey the browser created for the registration options' challenge. */
export function registerPasskey(
  challengeToken: string,
  credential: Record<string, unknown>,
  name: string,
): Promise<PasskeyResponse> {
  return webApi.post('/users/me/passkeys', { body: { challenge_token: challengeToken, credential, name } })
}
