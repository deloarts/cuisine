/**
 * The alert recipients list of the mail settings. The shape check is a light
 * one so typos are caught early; the backend validates for real.
 */
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export type AddRecipientResult = { recipients: string[]; error: null } | { recipients: string[]; error: 'invalid' }

/** Adds an address once, ignoring case for the duplicate check; empty input changes nothing. */
export function addRecipient(recipients: string[], input: string): AddRecipientResult {
  const email = input.trim()
  if (!email) return { recipients, error: null }
  if (!EMAIL_SHAPE.test(email)) return { recipients, error: 'invalid' }
  if (recipients.some((r) => r.toLowerCase() === email.toLowerCase())) return { recipients, error: null }
  return { recipients: [...recipients, email], error: null }
}
