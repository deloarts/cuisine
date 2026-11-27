/**
 * The accounts that signed in on this device, so the sign-in page can offer
 * them again with name and avatar instead of an empty form. Kept in this
 * browser's localStorage only and never sent anywhere. Nothing secret is
 * stored: the passkey's credential id only tells the browser which of its
 * passkeys to offer, and the private key stays in the authenticator.
 *
 * Storage goes through safeStorage, so a browser without storage simply
 * shows the plain form.
 */
import type { CurrentUserResponse } from '@/core/types/user'
import { safeStorage } from '@/core/utils/safeStorage'
import { imageUrl } from '@/shared/components/recipes/recipeImage'

const STORAGE_KEY = 'cuisine.rememberedAccounts'
const MAX_REMEMBERED = 5

export interface RememberedAccount {
  /** The account's public id, which stays when the e-mail address changes. */
  userId: string
  /** What the sign-in form takes: the e-mail address, or `system`. */
  login: string
  displayName: string
  /** A small data URL, so the avatar shows before anyone is signed in. */
  avatar: string | null
  /** base64url credential id of the passkey this device signed in with or registered, if any. */
  credentialId: string | null
  /** Public id of that passkey, to forget the credential id when the passkey is removed. */
  passkeyPublicId: string | null
  /** The user said "Not now" to a passkey on this device, so the sign-in no longer offers one. */
  passkeyDeclined?: boolean
  lastSignedInAt: string
}

function isRememberedAccount(value: unknown): value is RememberedAccount {
  const entry = value as Partial<RememberedAccount> | null
  return (
    typeof entry?.userId === 'string' &&
    entry.userId !== '' &&
    typeof entry.login === 'string' &&
    entry.login !== '' &&
    typeof entry.displayName === 'string' &&
    typeof entry.lastSignedInAt === 'string'
  )
}

function read(): RememberedAccount[] {
  try {
    const raw = safeStorage.get(STORAGE_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    // Hand-edited or outdated entries are dropped rather than trusted.
    return Array.isArray(parsed) ? parsed.filter(isRememberedAccount) : []
  } catch {
    return []
  }
}

function write(accounts: RememberedAccount[]): void {
  safeStorage.set(STORAGE_KEY, JSON.stringify(accounts.slice(0, MAX_REMEMBERED)))
}

/** Most recent sign-in first. */
export function listRememberedAccounts(): RememberedAccount[] {
  return read().sort((a, b) => b.lastSignedInAt.localeCompare(a.lastSignedInAt))
}

/** Records a sign-in, keeping what this device already knew about the account. */
export function rememberAccount(
  update: Pick<RememberedAccount, 'userId' | 'login' | 'displayName'> & Partial<RememberedAccount>,
): RememberedAccount {
  const accounts = read()
  const existing = accounts.find((a) => a.userId === update.userId)
  const merged: RememberedAccount = {
    avatar: null,
    credentialId: null,
    passkeyPublicId: null,
    ...existing,
    ...update,
    lastSignedInAt: new Date().toISOString(),
  }
  write([merged, ...accounts.filter((a) => a.userId !== update.userId)])
  return merged
}

export function updateRememberedAccount(userId: string, patch: Partial<RememberedAccount>): void {
  write(read().map((a) => (a.userId === userId ? { ...a, ...patch } : a)))
}

export function forgetRememberedAccount(userId: string): void {
  write(read().filter((a) => a.userId !== userId))
}

/** Drops the credential id wherever it belongs to a passkey that no longer exists. */
export function forgetPasskey(passkeyPublicId: string): void {
  write(
    read().map((a) =>
      a.passkeyPublicId === passkeyPublicId ? { ...a, credentialId: null, passkeyPublicId: null } : a,
    ),
  )
}

/** Shrinks an avatar to a small JPEG data URL, so it fits comfortably in localStorage. */
export async function avatarToDataUrl(blob: Blob, size = 96): Promise<string | null> {
  try {
    const bitmap = await createImageBitmap(blob)
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    if (!context) return null
    const side = Math.min(bitmap.width, bitmap.height)
    context.drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, size, size)
    return canvas.toDataURL('image/jpeg', 0.85)
  } catch {
    return null
  }
}

/**
 * Remembers the account that just signed in, with its avatar shrunk to a
 * data URL while the session can still fetch it. `credentialId` is the
 * passkey it signed in with, if any; a password sign-in keeps what this
 * device already knew.
 */
export async function rememberSignedInAccount(
  user: CurrentUserResponse,
  credentialId: string | null = null,
): Promise<void> {
  let avatar: string | null = null
  if (user.avatar_id) {
    try {
      // A plain fetch of the image URL, because webApi types JSON routes and this one returns image bytes.
      const response = await fetch(imageUrl(user.avatar_id), { credentials: 'include' })
      if (response.ok) avatar = await avatarToDataUrl(await response.blob())
    } catch {
      // Without the image the sign-in page shows the initials.
    }
  }
  const known = read().find((a) => a.userId === user.id)
  rememberAccount({
    userId: user.id,
    // The system user signs in as "system", everyone else with the address.
    login: user.is_systemuser ? 'system' : user.email,
    displayName: user.display_name,
    avatar,
    // Another passkey than the one this device registered: its public id
    // is unknown here, so removing the old one must not forget this one.
    ...(credentialId && credentialId !== known?.credentialId ? { credentialId, passkeyPublicId: null } : {}),
  })
}
