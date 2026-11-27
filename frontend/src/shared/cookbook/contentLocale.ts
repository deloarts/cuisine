import type { AppLocale } from '@/core/i18n'

import type { ContentLocale } from './types'

/** The languages recipe and catalogue text can be written in. */
export const CONTENT_LOCALES: ContentLocale[] = ['en-GB', 'de-AT']

/** The content language that matches the UI language. */
export function contentLocaleOf(locale: AppLocale | string): ContentLocale {
  return locale === 'deAT' ? 'de-AT' : 'en-GB'
}
