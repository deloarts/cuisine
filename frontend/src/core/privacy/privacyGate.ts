/**
 * The rules of the blocking privacy statement. Until the signed-in user has
 * acknowledged the current version, the backend refuses everything but a few
 * routes with a 403 `PrivacyAcknowledgementRequiredError`; the app then shows
 * the statement instead of the page, and accepting or declining it is the
 * only way on.
 */
import type { CurrentUserResponse } from '@/core/types/user'
import { errorCode, errorStatus } from '@/core/utils/errors'

export const PRIVACY_REQUIRED_CODE = 'PrivacyAcknowledgementRequiredError'
export const STALE_PRIVACY_CODE = 'StalePrivacyVersionError'

/** Whether the user still has to acknowledge the current privacy statement. */
export function privacyPending(user: CurrentUserResponse | null): boolean {
  return user?.privacy_acknowledgement_pending === true
}

/** A request the backend refused because the statement is not acknowledged yet. */
export function isPrivacyRequired(error: unknown): boolean {
  return errorStatus(error) === 403 && errorCode(error) === PRIVACY_REQUIRED_CODE
}

/**
 * An acknowledgement of a version that is no longer the current one: the
 * administrator published a new statement while the dialog was open.
 */
export function isStalePrivacyVersion(error: unknown): boolean {
  return errorStatus(error) === 409 && errorCode(error) === STALE_PRIVACY_CODE
}
