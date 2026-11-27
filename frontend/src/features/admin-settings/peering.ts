/**
 * The rules of the Peers tab: how versions read, what a peer cannot show of
 * this instance's recipes, the switch form of a peer, and how a channel
 * error reads.
 */
import type { Peer, PeerSwitches } from '@/features/admin-settings/api/peering'

// The short categories the backend records for a failed channel request.
const CHANNEL_ERRORS = ['unreachable', 'invalid_target', 'refused', 'invalid_answer', 'consumer_failed']

/** Format versions as one line, such as "cuisine-recipes 1 · cuisine-catalogue 1". */
export function formatVersions(versions: Record<string, number | number[]>): string {
  return Object.entries(versions)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, v]) => `${name} ${Array.isArray(v) ? v.join(', ') : v}`)
    .join(' · ')
}

/** What this instance can show that the peer did not announce, so it is lost over there. */
export function missingCapabilities(own: string[], peer: string[]): string[] {
  const theirs = new Set(peer)
  return own.filter((c) => !theirs.has(c)).sort()
}

/** The switch form of a peer, as the switches endpoint takes it. */
export function switchesOf(peer: Peer): PeerSwitches {
  return {
    users_may_share: peer.users_may_share,
    accept_incoming: peer.accept_incoming,
    mirror_visibility: peer.mirror_visibility,
    mirror_group: peer.mirror_group ?? null,
    sync_all: peer.sync_all,
  }
}

/** How recipes from the peer are taken in: refused, after review, or at once. */
export function incomingKey(peer: Pick<Peer, 'accept_incoming' | 'sync_all'>): string {
  if (!peer.accept_incoming) return 'adminArea.peers.acceptIncomingOff'
  return peer.sync_all ? 'adminArea.peers.syncAllOn' : 'adminArea.peers.acceptIncomingOn'
}

/** Whether a save just switched "sync all" on, so the waiting recipes may be accepted at once. */
export function syncAllSwitchedOn(before: Pick<Peer, 'sync_all'>, after: Pick<Peer, 'sync_all'>): boolean {
  return !before.sync_all && after.sync_all
}

/** A group visibility needs a group before it can be saved. */
export function switchesComplete(form: PeerSwitches): boolean {
  return form.mirror_visibility === 'instance' || Boolean(form.mirror_group)
}

/** The locale key of a channel error category; an unknown category reads as a general failure. */
export function channelErrorKey(category: string): string {
  return `adminArea.peers.channelErrors.${CHANNEL_ERRORS.includes(category) ? category : 'other'}`
}
