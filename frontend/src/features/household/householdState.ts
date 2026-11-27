/**
 * What the household page shows, worked out from the user's household and the
 * invitations they received. Kept apart from the view so the rules (who can
 * still be invited, when an invitation can be accepted, what leaving means)
 * are tested without rendering anything.
 */
import type { Schemas } from '@/core/api/generated'

export type HouseholdResponse = Schemas['HouseholdResponse']
export type ReceivedInvitation = Schemas['ReceivedInvitationResponse']
export type DirectoryUser = Schemas['DirectoryUserResponse']

/**
 * `member`: the user lives in a household. `invited`: not in one, with at
 * least one invitation to answer. `alone`: neither, so the page offers to
 * start a household.
 */
export type HouseholdPhase = 'member' | 'invited' | 'alone'

export function householdPhase(household: HouseholdResponse | null, received: ReceivedInvitation[]): HouseholdPhase {
  if (household) return 'member'
  return received.length ? 'invited' : 'alone'
}

/** The people already in the household or with an open invitation to it. */
export function takenIds(household: HouseholdResponse): Set<string> {
  const ids = new Set(household.members.map((m) => m.id))
  for (const invitation of household.invitations) {
    if (invitation.invitee) ids.add(invitation.invitee.id)
  }
  return ids
}

/**
 * The people the user may still invite: active directory entries that are
 * neither a member nor already invited, and never the user themself. Whether
 * someone already lives in another household stays the backend's answer, as
 * the directory does not reveal it.
 */
export function invitableUsers(
  directory: DirectoryUser[],
  household: HouseholdResponse,
  selfId: string | null,
): DirectoryUser[] {
  const taken = takenIds(household)
  return directory
    .filter((u) => u.id !== selfId && !taken.has(u.id))
    .sort((a, b) => a.display_name.localeCompare(b.display_name))
}

/** Leaving as the last member dissolves the household with its plan and list. */
export function leavingDissolves(household: HouseholdResponse): boolean {
  return household.members.length <= 1
}

/** Received invitations, newest first, so a fresh one is at the top. */
export function sortedInvitations(received: ReceivedInvitation[]): ReceivedInvitation[] {
  return [...received].sort((a, b) => b.created.localeCompare(a.created))
}
