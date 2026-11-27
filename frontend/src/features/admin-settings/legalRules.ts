/**
 * The rules of the Legal tab: which version is current, what a publish sends,
 * and when publishing would change nothing. Publishing always adds a new
 * version (nothing is edited in place), so the tab refuses to publish an
 * unchanged text and drops empty locales instead of sending them.
 */
import type { Schemas } from '@/core/api/generated'

export type LegalKind = Schemas['LegalKind']
export type LegalVersion = Schemas['LegalVersionResponse']
export type LegalTexts = Record<string, string>

export const LEGAL_LOCALES = ['de-AT', 'en-GB'] as const

/** The marker the privacy statement's mode section replaces. */
export const PRIVACY_MODE_MARKER = '{{ privacy_mode }}'

export function currentVersion(versions: LegalVersion[]): LegalVersion | null {
  return versions.reduce<LegalVersion | null>((best, v) => (!best || v.version > best.version ? v : best), null)
}

/** The texts to publish: every locale with some text, trimmed at the ends. */
export function cleanTexts(form: LegalTexts): LegalTexts {
  const texts: LegalTexts = {}
  for (const locale of LEGAL_LOCALES) {
    const text = (form[locale] ?? '').trim()
    if (text) texts[locale] = text
  }
  return texts
}

/** Locales the form leaves empty; readers of those fall back to another language. */
export function missingLocales(form: LegalTexts): string[] {
  return LEGAL_LOCALES.filter((locale) => !(form[locale] ?? '').trim())
}

/** Whether publishing would add a version that differs from the current one. */
export function hasChanges(form: LegalTexts, current: LegalVersion | null): boolean {
  const next = cleanTexts(form)
  if (!Object.keys(next).length) return false
  if (!current) return true
  const before = cleanTexts(current.texts)
  return LEGAL_LOCALES.some((locale) => (next[locale] ?? '') !== (before[locale] ?? ''))
}

/**
 * Locales of a privacy statement without the mode marker. The backend then
 * appends the mode section at the end, which the tab points out.
 */
export function localesWithoutMarker(form: LegalTexts): string[] {
  return LEGAL_LOCALES.filter((locale) => {
    const text = (form[locale] ?? '').trim()
    return text !== '' && !text.includes(PRIVACY_MODE_MARKER)
  })
}
