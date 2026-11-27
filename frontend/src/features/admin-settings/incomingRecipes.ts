/**
 * The rules of the incoming recipes queue and the per-peer mapping: which
 * decisions each kind of catalogue entry takes, what a decision starts as,
 * when one is complete, the request the backend takes, and which entries a
 * refused accept names as still missing.
 */
import axios from 'axios'

import type {
  MappingDecision,
  NeededEntry,
  PeerMapping,
} from '@/features/admin-settings/api/peering'

export type EntryKind = NeededEntry['kind']
export type DecisionAction = MappingDecision['action']

/** The decisions each kind takes: units map or none; tags map, create or none; ingredients and equipment map, create or plain. */
export const ACTIONS: Record<EntryKind, DecisionAction[]> = {
  unit: ['map', 'none'],
  tag: ['map', 'create', 'none'],
  ingredient: ['map', 'create', 'plain'],
  equipment: ['map', 'create', 'plain'],
}

/** One decision as the dialog edits it; `target_name` is only shown. */
export interface DecisionState {
  action: DecisionAction
  target_id: string | null
  target_name: string | null
  category_id: string | null
}

/** The key the backend names an entry by in `missing`: `<kind>:<source id>`. */
export function entryKey(entry: { kind: string; source_id: string }): string {
  return `${entry.kind}:${entry.source_id}`
}

/**
 * The decision an entry starts with: the suggestion when there is one,
 * otherwise a new ingredient or equipment item, and a unit left out or a
 * tag dropped (a tag is created only when the administrator asks for it).
 */
export function initialDecision(entry: NeededEntry): DecisionState {
  if (entry.suggestion) {
    return {
      action: 'map',
      target_id: entry.suggestion.id,
      target_name: entry.suggestion.name,
      category_id: entry.category_suggestion?.id ?? null,
    }
  }
  return {
    action: entry.kind === 'ingredient' || entry.kind === 'equipment' ? 'create' : 'none',
    target_id: null,
    target_name: null,
    category_id: entry.category_suggestion?.id ?? null,
  }
}

/** The decision a mapping holds now, for correcting it. */
export function mappingDecision(mapping: PeerMapping): DecisionState {
  return {
    action: mapping.action ?? ACTIONS[mapping.kind][0]!,
    target_id: mapping.target_id,
    target_name: mapping.target_name,
    category_id: null,
  }
}

/** A decision is complete unless it maps without naming the local entry. */
export function decisionComplete(state: DecisionState | undefined): boolean {
  return !!state && (state.action !== 'map' || !!state.target_id)
}

/** The keys of the entries whose decision is not complete yet. */
export function incompleteKeys(entries: NeededEntry[], states: Record<string, DecisionState>): string[] {
  return entries.map(entryKey).filter((key) => !decisionComplete(states[key]))
}

/** The accept request: one decision per entry, sending only what the action needs. */
export function decisionRequests(
  entries: NeededEntry[],
  states: Record<string, DecisionState>,
): MappingDecision[] {
  return entries.flatMap((entry) => {
    const state = states[entryKey(entry)]
    if (!state) return []
    return [
      {
        kind: entry.kind,
        source_id: entry.source_id,
        action: state.action,
        target_id: state.action === 'map' ? state.target_id : null,
        category_id: state.action === 'create' && entry.kind === 'ingredient' ? state.category_id : null,
      },
    ]
  })
}

/** The entries a 422 `PeerMappingError` names as still lacking a decision. */
export function missingKeysOf(error: unknown): string[] {
  if (!axios.isAxiosError(error)) return []
  const missing: unknown = error.response?.data?.missing
  return Array.isArray(missing) ? missing.filter((m): m is string => typeof m === 'string') : []
}
