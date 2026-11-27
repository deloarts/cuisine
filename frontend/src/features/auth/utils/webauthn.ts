/**
 * Browser side of the passkey ceremonies. The backend sends WebAuthn
 * options as JSON with base64url strings where the browser API wants
 * binary, and expects the created or signed credential back in the same
 * JSON form. The conversions are written out here instead of relying on
 * PublicKeyCredential.parseCreationOptionsFromJSON and toJSON(), which
 * not every supported browser ships yet.
 */

type Json = Record<string, unknown>

export function base64urlToBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

export function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** Whether this page may use WebAuthn at all: https or localhost, and a browser that has it. */
export function passkeysSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    typeof window.PublicKeyCredential !== 'undefined' &&
    typeof navigator.credentials !== 'undefined'
  )
}

/** Whether the device has a built-in authenticator (Windows Hello, Touch ID, a phone's screen lock). */
export async function platformAuthenticatorAvailable(): Promise<boolean> {
  if (!passkeysSupported()) return false
  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
  } catch {
    return false
  }
}

export type PlatformAuthenticator = 'windowsHello' | 'touchId' | 'generic'

/** Which name the device's built-in authenticator goes by, for the labels. */
export function platformAuthenticatorKind(): PlatformAuthenticator {
  const agent = navigator.userAgent
  if (/Windows/i.test(agent)) return 'windowsHello'
  if (/Macintosh|Mac OS X/i.test(agent)) return 'touchId'
  return 'generic'
}

/** The user dismissed the prompt, it timed out, or no matching passkey exists on this device. */
export function passkeyPromptDismissed(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === 'NotAllowedError' || error.name === 'AbortError')
  )
}

function isJson(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function field(value: unknown): Json {
  return isJson(value) ? value : {}
}

function text(value: unknown, name: string): string {
  if (typeof value !== 'string') throw new TypeError(`Passkey options lack the string field "${name}"`)
  return value
}

function optionalText(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

/** The value when it is one of the allowed strings, so an unknown enum value is left to the browser's default. */
function oneOf<T extends string>(value: unknown, allowed: readonly T[]): T | undefined {
  return allowed.find((option) => option === value)
}

const USER_VERIFICATION: readonly UserVerificationRequirement[] = ['required', 'preferred', 'discouraged']

function optionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined
}

function descriptors(list: unknown): PublicKeyCredentialDescriptor[] {
  if (!Array.isArray(list)) return []
  return list.filter(isJson).map((entry) => ({
    type: 'public-key',
    id: base64urlToBuffer(text(entry.id, 'id')),
    transports: Array.isArray(entry.transports)
      ? entry.transports.filter((t): t is AuthenticatorTransport => typeof t === 'string')
      : undefined,
  }))
}

function credentialParameters(list: unknown): PublicKeyCredentialParameters[] {
  if (!Array.isArray(list)) return []
  return list
    .filter(isJson)
    .flatMap((entry) => (typeof entry.alg === 'number' ? [{ type: 'public-key' as const, alg: entry.alg }] : []))
}

function authenticatorSelection(value: unknown): AuthenticatorSelectionCriteria | undefined {
  if (!isJson(value)) return undefined
  return {
    authenticatorAttachment: oneOf<AuthenticatorAttachment>(value.authenticatorAttachment, ['platform', 'cross-platform']),
    residentKey: oneOf<ResidentKeyRequirement>(value.residentKey, ['required', 'preferred', 'discouraged']),
    requireResidentKey: typeof value.requireResidentKey === 'boolean' ? value.requireResidentKey : undefined,
    userVerification: oneOf(value.userVerification, USER_VERIFICATION),
  }
}

/**
 * Converts the backend's registration options, typed only as a JSON object
 * in the generated schema, into the browser's creation options, decoding
 * the base64url fields and reading each known field by its type.
 */
export function toCreationOptions(options: Json): PublicKeyCredentialCreationOptions {
  const rp = field(options.rp)
  const user = field(options.user)
  return {
    rp: { id: optionalText(rp.id), name: text(rp.name, 'rp.name') },
    user: {
      id: base64urlToBuffer(text(user.id, 'user.id')),
      name: text(user.name, 'user.name'),
      displayName: text(user.displayName, 'user.displayName'),
    },
    challenge: base64urlToBuffer(text(options.challenge, 'challenge')),
    pubKeyCredParams: credentialParameters(options.pubKeyCredParams),
    timeout: optionalNumber(options.timeout),
    excludeCredentials: descriptors(options.excludeCredentials),
    authenticatorSelection: authenticatorSelection(options.authenticatorSelection),
    attestation: oneOf<AttestationConveyancePreference>(options.attestation, ['none', 'indirect', 'direct', 'enterprise']),
  }
}

/**
 * Converts the backend's authentication options into the browser's request
 * options. `credentialId` narrows the prompt to that one passkey.
 */
export function toRequestOptions(options: Json, credentialId?: string | null): PublicKeyCredentialRequestOptions {
  return {
    challenge: base64urlToBuffer(text(options.challenge, 'challenge')),
    timeout: optionalNumber(options.timeout),
    rpId: optionalText(options.rpId),
    userVerification: oneOf(options.userVerification, USER_VERIFICATION),
    allowCredentials: credentialId
      ? [{ type: 'public-key', id: base64urlToBuffer(credentialId) }]
      : descriptors(options.allowCredentials),
  }
}

function attachment(credential: PublicKeyCredential): string | null {
  return credential.authenticatorAttachment ?? null
}

/** Runs navigator.credentials.create() and returns the result in the backend's JSON form. */
export async function createPasskey(options: Json): Promise<Json> {
  const publicKey = toCreationOptions(options)

  const credential = (await navigator.credentials.create({ publicKey })) as PublicKeyCredential
  const response = credential.response as AuthenticatorAttestationResponse
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: attachment(credential),
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
      transports: response.getTransports?.() ?? [],
    },
  }
}

/**
 * Runs navigator.credentials.get() and returns the result in the backend's
 * JSON form. `credentialId` narrows the prompt to the passkey this device
 * registered for the remembered user; without it the browser offers every
 * passkey it holds for this site.
 */
export async function getPasskey(options: Json, credentialId?: string | null): Promise<Json> {
  const publicKey = toRequestOptions(options, credentialId)

  const credential = (await navigator.credentials.get({ publicKey })) as PublicKeyCredential
  const response = credential.response as AuthenticatorAssertionResponse
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: attachment(credential),
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    },
  }
}
