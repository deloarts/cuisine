/**
 * Unsaved editor state kept on the device, so leaving an editor (closing the
 * tab, following a link, losing the connection) does not lose the work.
 * Every draft belongs to one user and one editor scope, for example a recipe
 * or a variation, and is keyed by both, so people sharing a device and
 * different recipes never mix. A user's drafts are removed when they sign
 * out. Storage goes through safeStorage, so a browser without storage simply
 * keeps no drafts.
 */
import { safeStorage } from '@/core/utils/safeStorage'

const PREFIX = 'cuisineDraft:'

export interface StoredDraft<T> {
  // When the draft was last written, as an ISO timestamp.
  savedAt: string
  // The server's version of the edited record when the editor loaded it
  // (its `changed` timestamp), or null for a record that does not exist yet.
  base: string | null
  data: T
}

function keyOf(userId: string, scope: string): string {
  return `${PREFIX}${userId}:${scope}`
}

export const editorDrafts = {
  /** The stored draft, or null when there is none or it cannot be read. */
  read<T>(userId: string, scope: string): StoredDraft<T> | null {
    const raw = safeStorage.get(keyOf(userId, scope))
    if (raw === null) return null
    try {
      const parsed = JSON.parse(raw) as StoredDraft<T>
      return parsed && typeof parsed === 'object' && 'data' in parsed ? parsed : null
    } catch {
      return null
    }
  },

  /** Whether the draft was stored. */
  write<T>(userId: string, scope: string, base: string | null, data: T): boolean {
    const draft: StoredDraft<T> = { savedAt: new Date().toISOString(), base, data }
    return safeStorage.set(keyOf(userId, scope), JSON.stringify(draft))
  },

  remove(userId: string, scope: string): void {
    safeStorage.remove(keyOf(userId, scope))
  },

  /** Removes every draft of one user, on sign-out. */
  clearUser(userId: string): void {
    const prefix = `${PREFIX}${userId}:`
    for (const key of safeStorage.keys()) if (key.startsWith(prefix)) safeStorage.remove(key)
  },
}
