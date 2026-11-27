import { passkeyRegistrationOptions, registerPasskey, type PasskeyResponse } from '@/features/auth/api/login'
import { updateRememberedAccount } from '@/features/auth/utils/rememberedAccounts'
import { createPasskey } from '@/features/auth/utils/webauthn'

/**
 * Registers a passkey for the signed-in user on this device: runs the
 * browser prompt, stores the passkey, and remembers on this device which
 * passkey the sign-in page offers from now on. A dismissed prompt throws
 * the browser's error, which `passkeyPromptDismissed` recognises.
 */
export async function setUpPasskeyOnThisDevice(
  userId: string,
  name: string,
): Promise<PasskeyResponse> {
  const options = await passkeyRegistrationOptions()
  const credential = await createPasskey(options.options)
  const created = await registerPasskey(options.challenge_token, credential, name)
  if (typeof credential.rawId === 'string') {
    updateRememberedAccount(userId, {
      credentialId: credential.rawId,
      passkeyPublicId: created.id,
      passkeyDeclined: false,
    })
  }
  return created
}
