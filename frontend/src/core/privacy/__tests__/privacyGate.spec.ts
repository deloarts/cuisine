import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import { isPrivacyRequired, isStalePrivacyVersion, privacyPending } from '@/core/privacy/privacyGate'
import type { CurrentUserResponse } from '@/core/types/user'

function failure(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('failed', 'ERR', config, null, { status, statusText: '', headers: {}, config, data })
}

describe('privacyGate', () => {
  it('is pending only for a signed-in user who has not acknowledged the current version', () => {
    expect(privacyPending(null)).toBe(false)
    expect(privacyPending({ privacy_acknowledgement_pending: true } as CurrentUserResponse)).toBe(true)
    expect(privacyPending({ privacy_acknowledgement_pending: false } as CurrentUserResponse)).toBe(false)
  })

  it('recognises the refusal of a request until the statement is acknowledged', () => {
    expect(isPrivacyRequired(failure(403, { code: 'PrivacyAcknowledgementRequiredError' }))).toBe(true)
    expect(isPrivacyRequired(failure(403, { code: 'PermissionDeniedError' }))).toBe(false)
    expect(isPrivacyRequired(failure(409, { code: 'PrivacyAcknowledgementRequiredError' }))).toBe(false)
    expect(isPrivacyRequired(new Error('offline'))).toBe(false)
  })

  it('recognises an acknowledgement of a version that was replaced meanwhile', () => {
    expect(isStalePrivacyVersion(failure(409, { code: 'StalePrivacyVersionError' }))).toBe(true)
    expect(isStalePrivacyVersion(failure(409, { detail: 'conflict' }))).toBe(false)
  })
})
