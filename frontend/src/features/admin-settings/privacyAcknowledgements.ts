/**
 * The overview of who accepted which privacy statement version, as one list
 * for the shared table: everyone on the current version, and everyone still
 * asked with the version they accepted last (or none).
 */
import type { Schemas } from '@/core/api/generated'

export type AcknowledgementOverview = Schemas['PrivacyAcknowledgementOverviewResponse']
export type AcknowledgementEntry = Schemas['PrivacyAcknowledgementEntry']
export type AcknowledgementStatus = 'current' | 'outdated' | 'never'

export interface AcknowledgementRow {
  id: string
  name: string
  version: number | null
  acknowledgedAt: string | null
  status: AcknowledgementStatus
}

function row(entry: AcknowledgementEntry, status: AcknowledgementStatus): AcknowledgementRow {
  return {
    id: entry.user.id,
    name: entry.user.display_name,
    version: entry.version ?? null,
    acknowledgedAt: entry.acknowledged_at ?? null,
    status,
  }
}

/** The pending people first, since they are the ones an admin looks for, then by name. */
export function acknowledgementRows(overview: AcknowledgementOverview): AcknowledgementRow[] {
  const pending = overview.pending.map((e) => row(e, e.version == null ? 'never' : 'outdated'))
  const done = overview.acknowledged.map((e) => row(e, 'current'))
  const byName = (a: AcknowledgementRow, b: AcknowledgementRow) => a.name.localeCompare(b.name)
  return [...pending.sort(byName), ...done.sort(byName)]
}

export function acknowledgementCounts(overview: AcknowledgementOverview): { done: number; total: number } {
  return { done: overview.acknowledged.length, total: overview.acknowledged.length + overview.pending.length }
}
