import { describe, expect, it } from 'vitest'

import {
  householdPhase,
  invitableUsers,
  leavingDissolves,
  sortedInvitations,
  takenIds,
  type DirectoryUser,
  type HouseholdResponse,
  type ReceivedInvitation,
} from '@/features/household/householdState'

const anna = { id: 'anna', display_name: 'Anna' }
const ben = { id: 'ben', display_name: 'Ben' }
const me = { id: 'me', display_name: 'Me' }

function household(extra: Partial<HouseholdResponse> = {}): HouseholdResponse {
  return {
    id: 'h1',
    name: 'Familie Beispiel',
    members: [me],
    invitations: [],
    shopping_list_id: 'list-1',
    created: '2026-11-01T10:00:00Z',
    ...extra,
  }
}

function received(id: string, created: string): ReceivedInvitation {
  return { id, household: { id: `h-${id}`, name: `House ${id}` }, inviter: anna, created }
}

function user(person: { id: string; display_name: string }): DirectoryUser {
  return { ...person, avatar_id: null }
}

describe('householdPhase', () => {
  it('is member while in a household, whatever was received', () => {
    expect(householdPhase(household(), [received('a', '2026-11-02T00:00:00Z')])).toBe('member')
  })

  it('is invited without a household but with invitations, alone otherwise', () => {
    expect(householdPhase(null, [received('a', '2026-11-02T00:00:00Z')])).toBe('invited')
    expect(householdPhase(null, [])).toBe('alone')
  })
})

describe('invitableUsers', () => {
  const directory = [user(ben), user(me), user(anna), user({ id: 'cleo', display_name: 'Cleo' })]

  it('leaves out the user, the members and everyone already invited', () => {
    const h = household({
      members: [me, anna],
      invitations: [{ id: 'i1', invitee: ben, inviter: me, created: '2026-11-02T00:00:00Z' }],
    })
    expect(invitableUsers(directory, h, 'me').map((u) => u.id)).toEqual(['cleo'])
  })

  it('sorts by name and ignores invitations whose invitee is gone', () => {
    const h = household({ invitations: [{ id: 'i1', invitee: null, inviter: me, created: '2026-11-02T00:00:00Z' }] })
    expect(invitableUsers(directory, h, 'me').map((u) => u.display_name)).toEqual(['Anna', 'Ben', 'Cleo'])
    expect(takenIds(h)).toEqual(new Set(['me']))
  })
})

describe('leavingDissolves', () => {
  it('is true only for the last member', () => {
    expect(leavingDissolves(household())).toBe(true)
    expect(leavingDissolves(household({ members: [me, anna] }))).toBe(false)
  })
})

describe('sortedInvitations', () => {
  it('puts the newest first without changing the input', () => {
    const list = [received('old', '2026-11-01T00:00:00Z'), received('new', '2026-11-03T00:00:00Z')]
    expect(sortedInvitations(list).map((i) => i.id)).toEqual(['new', 'old'])
    expect(list[0]?.id).toBe('old')
  })
})
