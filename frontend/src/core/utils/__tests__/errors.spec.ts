import { AxiosError, AxiosHeaders } from 'axios'
import { afterEach, describe, expect, it } from 'vitest'

import { i18n } from '@/core/i18n'
import { errorCode, errorMessage, errorStatus } from '@/core/utils/errors'

function axiosError(status: number, data: unknown): AxiosError {
  const headers = new AxiosHeaders()
  return new AxiosError('failed', 'ERR', { headers }, null, {
    status,
    data,
    statusText: '',
    headers,
    config: { headers },
  })
}

describe('errorMessage', () => {
  afterEach(() => {
    i18n.global.locale.value = 'enGB'
  })

  it('prefers the translation of the error code over the detail', () => {
    i18n.global.locale.value = 'deAT'
    const err = axiosError(403, {
      detail: 'Only its author or someone with manage:recipes deletes it.',
      code: 'NotOwnerError',
    })
    expect(errorMessage(err, 'x')).toBe(i18n.global.t('errors.NotOwnerError'))
    expect(errorMessage(err, 'x')).not.toContain('manage:recipes')
  })

  it('falls back to the detail for a code without a translation', () => {
    const err = axiosError(409, { detail: 'Taken.', code: 'SomethingNewError' })
    expect(errorMessage(err, 'x')).toBe('Taken.')
    expect(errorCode(err)).toBe('SomethingNewError')
  })

  it('uses the backend detail when there is one', () => {
    expect(errorMessage(axiosError(409, { detail: 'Taken.' }), 'x')).toBe('Taken.')
  })

  it('joins validation errors', () => {
    const err = axiosError(422, { detail: [{ msg: 'too short' }, { msg: 'bad email' }] })
    expect(errorMessage(err, 'x')).toBe('too short bad email')
  })

  it('keeps joining validation errors in German', () => {
    i18n.global.locale.value = 'deAT'
    const err = axiosError(422, { detail: [{ msg: 'too short' }] })
    expect(errorMessage(err, 'x')).toBe('too short')
  })

  it('falls back for anything else', () => {
    expect(errorMessage(new Error('boom'), 'fallback')).toBe('fallback')
    expect(errorMessage(axiosError(500, {}), 'fallback')).toBe('fallback')
  })

  it('reads the status', () => {
    expect(errorStatus(axiosError(429, {}))).toBe(429)
    expect(errorStatus(new Error('x'))).toBeNull()
  })
})
