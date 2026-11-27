import { describe, expect, it } from 'vitest'

import type { Peer } from '@/features/admin-settings/api/peering'
import {
  channelErrorKey,
  formatVersions,
  incomingKey,
  missingCapabilities,
  switchesComplete,
  switchesOf,
  syncAllSwitchedOn,
} from '@/features/admin-settings/peering'

const peer: Peer = {
  id: 'p1',
  instance_id: 'i1',
  name: 'Friends',
  base_url: 'https://friends.example',
  app_version: '1.2.0',
  status: 'active',
  revoked_by: null,
  protocol_version: 1,
  format_versions: { 'cuisine-recipes': 1, 'cuisine-catalogue': 1 },
  capabilities: ['seasons'],
  users_may_share: true,
  accept_incoming: true,
  mirror_visibility: 'instance',
  mirror_group: null,
  sync_all: false,
  created: '2026-11-22T10:00:00Z',
  paired_at: '2026-11-22T10:00:00Z',
  revoked_at: null,
  last_contact_at: null,
}

describe('formatVersions', () => {
  it('lists formats by name with one or several versions', () => {
    expect(formatVersions(peer.format_versions)).toBe('cuisine-catalogue 1 · cuisine-recipes 1')
    expect(formatVersions({ 'cuisine-recipes': [1, 2] })).toBe('cuisine-recipes 1, 2')
    expect(formatVersions({})).toBe('')
  })
})

describe('missingCapabilities', () => {
  it('names what the peer cannot show', () => {
    expect(missingCapabilities(['variations', 'equipment', 'seasons'], peer.capabilities)).toEqual([
      'equipment',
      'variations',
    ])
    expect(missingCapabilities(['seasons'], ['seasons', 'other'])).toEqual([])
  })
})

describe('switches', () => {
  it('copies the switches of a peer', () => {
    expect(switchesOf(peer)).toEqual({
      users_may_share: true,
      accept_incoming: true,
      mirror_visibility: 'instance',
      mirror_group: null,
      sync_all: false,
    })
  })

  it('says how recipes from the peer are taken in', () => {
    expect(incomingKey(peer)).toBe('adminArea.peers.acceptIncomingOn')
    expect(incomingKey({ ...peer, sync_all: true })).toBe('adminArea.peers.syncAllOn')
    expect(incomingKey({ ...peer, accept_incoming: false, sync_all: true })).toBe(
      'adminArea.peers.acceptIncomingOff',
    )
  })

  it('notices when sync all was just switched on', () => {
    expect(syncAllSwitchedOn(peer, { ...peer, sync_all: true })).toBe(true)
    expect(syncAllSwitchedOn({ ...peer, sync_all: true }, { ...peer, sync_all: true })).toBe(false)
    expect(syncAllSwitchedOn(peer, peer)).toBe(false)
  })

  it('needs a group for the group visibility', () => {
    const form = switchesOf(peer)
    expect(switchesComplete(form)).toBe(true)
    expect(switchesComplete({ ...form, mirror_visibility: 'group' })).toBe(false)
    expect(switchesComplete({ ...form, mirror_visibility: 'group', mirror_group: 'g1' })).toBe(true)
  })
})

describe('channelErrorKey', () => {
  it('names a known category and reads anything else as a general failure', () => {
    expect(channelErrorKey('unreachable')).toBe('adminArea.peers.channelErrors.unreachable')
    expect(channelErrorKey('consumer_failed')).toBe('adminArea.peers.channelErrors.consumer_failed')
    expect(channelErrorKey('something_new')).toBe('adminArea.peers.channelErrors.other')
  })
})
