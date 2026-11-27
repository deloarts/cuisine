import { describe, expect, it } from 'vitest'

import { CONTENT_LOCALES, contentLocaleOf } from '@/shared/cookbook/contentLocale'

describe('contentLocaleOf', () => {
  it('maps the UI language and defaults to English', () => {
    expect(contentLocaleOf('deAT')).toBe('de-AT')
    expect(contentLocaleOf('enGB')).toBe('en-GB')
    expect(contentLocaleOf('fr')).toBe('en-GB')
    expect(CONTENT_LOCALES[0]).toBe('en-GB')
  })
})
