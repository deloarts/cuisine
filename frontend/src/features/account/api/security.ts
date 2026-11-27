/**
 * The sign-in security of the own account: password, TOTP, passkeys, the
 * open sessions and the devices trusted to skip the second factor.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type Passkey = Schemas['PasskeyResponse']
export type Session = Schemas['SessionResponse']
export type TrustedDevice = Schemas['TrustedDeviceResponse']
export type TotpEnrolment = Schemas['TotpEnrolmentResponse']

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await webApi.post('/users/me/password', {
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

/** Starts a TOTP enrolment; a signed-in session confirms it with the current password. */
/** Starts enrolling from a signed-in session, which the backend confirms with the current password. */
export function enrollTotp(password: string): Promise<TotpEnrolment> {
  return webApi.post('/users/me/totp/enroll', { body: { password } })
}

export async function confirmTotp(code: string): Promise<void> {
  await webApi.post('/users/me/totp/confirm', { body: { code } })
}

export async function disableTotp(password: string): Promise<void> {
  await webApi.post('/users/me/totp/disable', { body: { password } })
}

export function listPasskeys(): Promise<Passkey[]> {
  return webApi.get('/users/me/passkeys')
}

export async function removePasskey(id: string): Promise<void> {
  await webApi.delete('/users/me/passkeys/{passkey_id}', { path: { passkey_id: id } })
}

export function listSessions(): Promise<Session[]> {
  return webApi.get('/users/me/sessions')
}

export async function endSession(id: string): Promise<void> {
  await webApi.delete('/users/me/sessions/{session_id}', { path: { session_id: id } })
}

/** Ends every other session of the user. */
export async function endOtherSessions(): Promise<void> {
  await webApi.delete('/users/me/sessions')
}

export function listTrustedDevices(): Promise<TrustedDevice[]> {
  return webApi.get('/users/me/trusted-devices')
}

/** Forgets one trusted device, or every one when no id is given. */
export async function forgetTrustedDevice(id?: string): Promise<void> {
  if (id) await webApi.delete('/users/me/trusted-devices/{device_id}', { path: { device_id: id } })
  else await webApi.delete('/users/me/trusted-devices')
}
