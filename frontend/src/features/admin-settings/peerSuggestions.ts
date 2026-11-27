/**
 * Suggestions from paired instances: catalogue values a peer sent with its
 * recipes that differ from the local entry its mapping points at. The
 * backend groups them by local entry, entries with allergen or diet marker
 * suggestions first; this module flattens the groups into table rows in
 * that order and says which rows the current user may accept.
 */
import type { Schemas } from '@/core/api/generated'
import { Permission } from '@/core/auth/permissions'

export type PeerSuggestionGroup = Schemas['PeerSuggestionGroupResponse']
export type PeerSuggestion = Schemas['PeerSuggestionResponse']
export type SuggestionKind = PeerSuggestionGroup['kind']

export const SUGGESTION_KINDS: SuggestionKind[] = ['ingredient', 'unit', 'tag', 'equipment']

/** One row of the table: a suggestion with the local entry it belongs to. */
export interface PeerSuggestionRow extends PeerSuggestion {
  id: string
  kind: SuggestionKind
  entryId: string
  name: string
}

/** Stable key of one suggestion, for the table and for removing a handled row. */
export function suggestionKey(row: Pick<PeerSuggestionRow, 'kind' | 'source_id' | 'field' | 'peer'>): string {
  return `${row.peer.id}:${row.kind}:${row.source_id}:${row.field}`
}

/** The groups as rows, keeping the backend's order. */
export function suggestionRows(groups: PeerSuggestionGroup[]): PeerSuggestionRow[] {
  return groups.flatMap((group) =>
    group.suggestions.map((s) => {
      const row = { ...s, kind: group.kind, entryId: group.id, name: group.name, id: '' }
      row.id = suggestionKey(row)
      return row
    }),
  )
}

/**
 * Whether the user may accept or dismiss suggestions of this kind: the
 * rights of the catalogue file, ingredients needing manage:ingredients and
 * write:ingredients, every other kind write:resources.
 */
export function mayDecide(kind: SuggestionKind, has: (permission: string) => boolean): boolean {
  if (kind === 'ingredient') return has(Permission.MANAGE_INGREDIENTS) && has(Permission.WRITE_INGREDIENTS)
  return has(Permission.WRITE_RESOURCES)
}
