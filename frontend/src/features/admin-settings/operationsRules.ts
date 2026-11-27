/**
 * The rules of the Operations tab: what saving the maintenance form changes,
 * so turning the read-only mode on or off is confirmed first, and how a
 * retention period reads.
 */
import type { Schemas } from '@/core/api/generated'

export type Maintenance = Schemas['MaintenanceResponse']
export type MaintenanceForm = Pick<Maintenance, 'enabled' | 'messages'>
export type MaintenanceChange = 'on' | 'off' | 'message' | null

const MAINTENANCE_LOCALES = ['de-AT', 'en-GB'] as const

function sameMessages(a: Record<string, string>, b: Record<string, string>): boolean {
  return MAINTENANCE_LOCALES.every((l) => (a[l] ?? '').trim() === (b[l] ?? '').trim())
}

export function maintenanceChange(saved: MaintenanceForm, form: MaintenanceForm): MaintenanceChange {
  if (form.enabled !== saved.enabled) return form.enabled ? 'on' : 'off'
  return sameMessages(saved.messages, form.messages) ? null : 'message'
}

/** Turning maintenance on without any message leaves people with a bare banner. */
export function maintenanceMessageMissing(form: MaintenanceForm): boolean {
  return form.enabled && MAINTENANCE_LOCALES.every((l) => !(form.messages[l] ?? '').trim())
}

/** Only the locales with text, as the backend stores them. */
export function cleanMessages(messages: Record<string, string>): Record<string, string> {
  const clean: Record<string, string> = {}
  for (const l of MAINTENANCE_LOCALES) {
    const text = (messages[l] ?? '').trim()
    if (text) clean[l] = text
  }
  return clean
}

export const RETENTION_MAX_DAYS = 3650

/** A retention period of 0 days keeps the records forever. */
export function keepsForever(days: number | null | undefined): boolean {
  return !days
}
