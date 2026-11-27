import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { webApi } from '@/core/api/webRequest'
import { TOTP_GUARDED_PERMISSIONS } from '@/core/auth/permissions'
import { i18n, type AppLocale } from '@/core/i18n'
import { useLayoutStore } from '@/core/stores/layoutStore'
import type { CurrentUserResponse } from '@/core/types/user'
import { editorDrafts } from '@/core/utils/editorDrafts'

// sessionStorage, so the system account's warning returns with every new
// sign-in or tab but not on a reload.
export const SYSTEM_USER_WARNING_SESSION_KEY = 'cuisineSystemUserWarningShown'

// Caches outside core that hold the signed-in user's data register here to be
// dropped on sign-out. Core cannot import them, and they already import this
// store, so the store calls them back instead.
const signOutHooks = new Set<() => void>()

/** Registers a callback that `clear()` runs when the user signs out. */
export function onSignOut(hook: () => void): void {
  signOutHooks.add(hook)
}

function systemUserWarningAlreadyShown(): boolean {
  try {
    return sessionStorage.getItem(SYSTEM_USER_WARNING_SESSION_KEY) !== null
  } catch {
    return false
  }
}

function markSystemUserWarningShown(): void {
  try {
    sessionStorage.setItem(SYSTEM_USER_WARNING_SESSION_KEY, '1')
  } catch {
    // Best effort; at worst the warning shows again on the next reload.
  }
}

function clearSystemUserWarningShown(): void {
  try {
    sessionStorage.removeItem(SYSTEM_USER_WARNING_SESSION_KEY)
  } catch {
    // Best effort, like markSystemUserWarningShown.
  }
}

/**
 * The signed-in user. `loaded` turns true after the first attempt to read
 * the session, so the router can tell "not signed in" from "not asked yet".
 * The session itself is an httponly cookie the app never sees.
 */
export const useCurrentUserStore = defineStore('currentUser', () => {
  const user = ref<CurrentUserResponse | null>(null)
  const loaded = ref(false)
  // Set when a request answered 401 mid-visit; the router sends the user
  // to the login page with a note.
  const expired = ref(false)
  // When the session ends at the latest, in this browser's clock. Only set
  // for the system account, whose sessions end 15 minutes after sign-in;
  // null hides the countdown rather than showing a wrong number.
  const sessionExpiresAt = ref<number | null>(null)
  // Shown once per sign-in as the system account; only acknowledging it or
  // the session ending clears it, so a reload does not.
  const systemUserWarningPending = ref(false)

  const isSignedIn = computed(() => user.value !== null)
  // The user holds a settings permission but has not set up two-factor
  // authentication yet, so the backend refuses the settings until they do.
  const settingsNeedTotp = computed(
    () =>
      !!user.value &&
      !user.value.is_systemuser &&
      !user.value.totp_enabled &&
      TOTP_GUARDED_PERMISSIONS.some((p) => user.value!.effective_permissions.includes(p)),
  )

  function apply(next: CurrentUserResponse) {
    user.value = next
    expired.value = false
    i18n.global.locale.value = next.language as AppLocale
    useLayoutStore().applyUserTheme(
      next.theme_preset,
      next.theme_primary,
      next.theme_surface,
      next.theme_dark_mode,
    )
  }

  /**
   * The session's hard end, corrected for clock skew with the server's own
   * time. Never throws, so a failed read cannot fail the sign-in.
   */
  async function fetchSessionExpiry() {
    try {
      const { expires_at, server_time } = await webApi.get('/users/me/sessions/current')
      if (expires_at === null) {
        sessionExpiresAt.value = null
        return
      }
      const skewMs = Date.parse(server_time) - Date.now()
      sessionExpiresAt.value = Date.parse(expires_at) - skewMs
    } catch {
      sessionExpiresAt.value = null
    }
  }

  /** Reads the session; a 401 simply means nobody is signed in. */
  async function refresh(): Promise<CurrentUserResponse | null> {
    try {
      apply(await webApi.get('/users/me'))
    } catch {
      user.value = null
    } finally {
      loaded.value = true
    }
    if (user.value?.is_systemuser) {
      await fetchSessionExpiry()
      if (!systemUserWarningAlreadyShown()) systemUserWarningPending.value = true
    } else {
      sessionExpiresAt.value = null
    }
    return user.value
  }

  /** Records the system account's warning as read for this tab and hides it. */
  function acknowledgeSystemUserWarning() {
    systemUserWarningPending.value = false
    markSystemUserWarningShown()
  }

  function forgetSession() {
    user.value = null
    sessionExpiresAt.value = null
    systemUserWarningPending.value = false
    clearSystemUserWarningShown()
  }

  function hasPermission(permission: string): boolean {
    if (!user.value) return false
    return user.value.is_systemuser || user.value.effective_permissions.includes(permission)
  }

  /**
   * Marks the current privacy statement as not acknowledged, after a request
   * the backend refused for it, so the app shows the statement again.
   */
  function requirePrivacyAcknowledgement() {
    if (user.value && !user.value.privacy_acknowledgement_pending) {
      user.value = { ...user.value, privacy_acknowledgement_pending: true }
    }
  }

  // Signing out (logging out, declining the privacy statement, deleting the
  // account) also drops the user's unsaved editor drafts from the device and
  // the caches registered with `onSignOut`. An expired session keeps the
  // drafts, so the work is still there after signing in again.
  function clear() {
    if (user.value) editorDrafts.clearUser(user.value.id)
    signOutHooks.forEach((hook) => hook())
    forgetSession()
  }

  function sessionExpired() {
    if (user.value) expired.value = true
    forgetSession()
  }

  return {
    user,
    loaded,
    expired,
    sessionExpiresAt,
    systemUserWarningPending,
    isSignedIn,
    settingsNeedTotp,
    apply,
    refresh,
    acknowledgeSystemUserWarning,
    hasPermission,
    requirePrivacyAcknowledgement,
    clear,
    sessionExpired,
  }
})
