import type { AppLocale } from '@/core/i18n'

import { formatDateParts, formatTimeParts } from './displayFormats'

/** The BCP 47 tag of an app locale, for Intl and <html lang>. */
export function localeTag(locale: AppLocale): string {
  return locale === 'deAT' ? 'de-AT' : 'en-GB'
}

/**
 * A date and time in the instance's date and time format, or a dash for
 * none. The locale stays in the signature for the callers that pass it;
 * the format is the admin's choice, not the language's.
 */
export function formatDateTime(value: string | null | undefined, _locale?: AppLocale): string {
  if (!value) return '–'
  const date = new Date(value)
  return `${formatDateParts(date)} ${formatTimeParts(date)}`
}

/** A date in the instance's date format, or a dash for none. */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '–'
  return formatDateParts(typeof value === 'string' ? new Date(value) : value)
}
