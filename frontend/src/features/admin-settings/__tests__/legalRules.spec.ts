import { describe, expect, it } from 'vitest'

import {
  cleanTexts,
  currentVersion,
  hasChanges,
  localesWithoutMarker,
  missingLocales,
  type LegalVersion,
} from '@/features/admin-settings/legalRules'

function version(n: number, texts: Record<string, string>): LegalVersion {
  return {
    id: `v${n}`,
    kind: 'privacy',
    version: n,
    texts,
    published_at: '2026-11-21T10:00:00Z',
    privacy_mode: 'instance',
    default_visibility: 'instance',
  }
}

describe('currentVersion', () => {
  it('is the highest version number, whatever the order', () => {
    expect(currentVersion([version(1, {}), version(3, {}), version(2, {})])?.version).toBe(3)
    expect(currentVersion([])).toBeNull()
  })
})

describe('publishing', () => {
  it('sends only locales with text, trimmed', () => {
    expect(cleanTexts({ 'de-AT': '  Hallo \n', 'en-GB': '   ' })).toEqual({ 'de-AT': 'Hallo' })
    expect(missingLocales({ 'de-AT': 'Hallo', 'en-GB': '' })).toEqual(['en-GB'])
  })

  it('needs a text and a difference to the current version', () => {
    const current = version(2, { 'de-AT': 'Hallo', 'en-GB': 'Hello' })
    expect(hasChanges({ 'de-AT': '', 'en-GB': '' }, null)).toBe(false)
    expect(hasChanges({ 'de-AT': 'Hallo' }, null)).toBe(true)
    expect(hasChanges({ 'de-AT': 'Hallo ', 'en-GB': 'Hello' }, current)).toBe(false)
    expect(hasChanges({ 'de-AT': 'Hallo', 'en-GB': '' }, current)).toBe(true)
  })
})

describe('localesWithoutMarker', () => {
  it('names the filled locales that lost the mode marker', () => {
    expect(localesWithoutMarker({ 'de-AT': 'Text {{ privacy_mode }} mehr', 'en-GB': 'Text' })).toEqual(['en-GB'])
    expect(localesWithoutMarker({ 'de-AT': '', 'en-GB': '' })).toEqual([])
  })
})
