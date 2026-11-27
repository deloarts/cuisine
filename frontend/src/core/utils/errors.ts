import axios from 'axios'

import { i18n } from '@/core/i18n'

/**
 * The message a failed request carries, in the user's language when possible.
 * The backend names its domain error in `code`; a translation under
 * `errors.<code>` wins. Without one the backend's `detail` is used, which is
 * written for the user but always in English, and `fallback` when there is
 * neither. FastAPI's validation errors arrive as a list and are joined.
 */
export function errorMessage(error: unknown, fallback: string): string {
  const translated = translatedCode(errorCode(error))
  if (translated) return translated
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (typeof detail === 'string' && detail) return detail
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item: unknown) =>
          item && typeof item === 'object' && 'msg' in item ? String(item.msg) : '',
        )
        .filter(Boolean)
      if (messages.length) return messages.join(' ')
    }
  }
  return fallback
}

/** The translated message for a domain error code, or null when there is none. */
function translatedCode(code: string | null): string | null {
  if (!code) return null
  const key = `errors.${code}`
  return i18n.global.te(key) ? i18n.global.t(key) : null
}

/** The HTTP status of a failed request, or null for anything else. */
export function errorStatus(error: unknown): number | null {
  return axios.isAxiosError(error) ? (error.response?.status ?? null) : null
}

/** The domain error name the backend sends as `code`, or null when there is none. */
export function errorCode(error: unknown): string | null {
  if (!axios.isAxiosError(error)) return null
  const code: unknown = error.response?.data?.code
  return typeof code === 'string' && code ? code : null
}
