/**
 * The catalogue review queue: draft ingredients (from an agent, inline
 * creation in the editor or a typed intolerance) waiting for someone who
 * manages ingredients to activate them or merge them into an existing one.
 */
import type { Schemas } from '@/core/api/generated'

export type DuplicateCandidate = Schemas['DuplicateCandidate']

/**
 * The merge suggestions for one draft: every near-duplicate except the draft
 * itself, exact matches first, then by name.
 */
export function mergeSuggestions(draftId: string, candidates: DuplicateCandidate[]): DuplicateCandidate[] {
  return candidates
    .filter((c) => c.id !== draftId)
    .sort((a, b) => Number(b.exact) - Number(a.exact) || a.name.localeCompare(b.name))
}
